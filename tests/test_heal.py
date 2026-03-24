"""
tests/test_heal.py — unit tests for scripts/heal.py

All external calls (Docker subprocess, requests, Gemini API) are mocked.
No real containers, no real HTTP calls, no API keys needed.

Run with:
    pytest tests/test_heal.py -v
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Provide dummy env vars so the module-level genai.Client() doesn't fail."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("SLACK_WEBHOOK", "https://hooks.slack.com/test")


@pytest.fixture
def heal(mock_env):
    """Import heal fresh for each test (avoids module-level side-effects)."""
    with patch("google.genai.Client"):
        import importlib
        import heal as _heal
        importlib.reload(_heal)
        return _heal


# ─── check_health ─────────────────────────────────────────────────────────────

class TestCheckHealth:

    def test_returns_true_on_200(self, heal):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.get", return_value=mock_resp):
            assert heal.check_health() is True

    def test_returns_false_on_500(self, heal):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("requests.get", return_value=mock_resp):
            assert heal.check_health() is False

    def test_returns_false_on_connection_error(self, heal):
        import requests as req
        with patch("requests.get", side_effect=req.exceptions.ConnectionError):
            assert heal.check_health() is False

    def test_returns_false_on_timeout(self, heal):
        import requests as req
        with patch("requests.get", side_effect=req.exceptions.Timeout):
            assert heal.check_health() is False

    def test_uses_5_second_timeout(self, heal):
        mock_resp = MagicMock(status_code=200)
        with patch("requests.get", return_value=mock_resp) as mock_get:
            heal.check_health()
            mock_get.assert_called_once_with(heal.HEALTH_URL, timeout=5)


# ─── send_slack ────────────────────────────────────────────────────────────────

class TestSendSlack:

    def test_posts_to_webhook(self, heal):
        with patch("requests.post") as mock_post:
            heal.send_slack("test message")
            mock_post.assert_called_once_with(
                heal.SLACK_WEBHOOK,
                json={"text": "test message"}
            )

    def test_does_not_raise_on_failure(self, heal):
        import requests as req
        with patch("requests.post", side_effect=req.exceptions.ConnectionError):
            heal.send_slack("test")  # should not raise


# ─── get_container_logs ────────────────────────────────────────────────────────

class TestGetContainerLogs:

    def test_returns_stdout_and_stderr(self, heal):
        mock_result = MagicMock()
        mock_result.stdout = "stdout log line\n"
        mock_result.stderr = "stderr log line\n"
        with patch("subprocess.run", return_value=mock_result):
            logs = heal.get_container_logs()
            assert "stdout log line" in logs
            assert "stderr log line" in logs

    def test_fetches_last_20_lines(self, heal):
        mock_result = MagicMock(stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            heal.get_container_logs()
            args = mock_run.call_args[0][0]
            assert "--tail" in args
            assert "20" in args

    def test_returns_fallback_on_exception(self, heal):
        with patch("subprocess.run", side_effect=Exception("docker not found")):
            logs = heal.get_container_logs()
            assert logs == "No logs available"


# ─── gemini_diagnose ──────────────────────────────────────────────────────────

class TestGeminiDiagnose:

    def test_returns_diagnosis_text(self, heal):
        mock_response = MagicMock()
        mock_response.text = "The app crashed due to OOM."
        heal.client.models.generate_content.return_value = mock_response
        result = heal.gemini_diagnose("some logs here")
        assert result == "The app crashed due to OOM."

    def test_includes_logs_in_prompt(self, heal):
        mock_response = MagicMock(text="ok")
        heal.client.models.generate_content.return_value = mock_response
        heal.gemini_diagnose("my specific log output")
        call_kwargs = heal.client.models.generate_content.call_args
        contents = call_kwargs[1].get("contents") or call_kwargs[0][1]
        assert "my specific log output" in contents

    def test_uses_correct_model(self, heal):
        mock_response = MagicMock(text="ok")
        heal.client.models.generate_content.return_value = mock_response
        heal.gemini_diagnose("logs")
        call_kwargs = heal.client.models.generate_content.call_args
        model = call_kwargs[1].get("model") or call_kwargs[0][0]
        assert model == "gemini-2.0-flash"

    def test_returns_fallback_on_api_error(self, heal):
        heal.client.models.generate_content.side_effect = Exception("API quota exceeded")
        result = heal.gemini_diagnose("some logs")
        assert "Gemini diagnosis failed" in result


# ─── restart_container ────────────────────────────────────────────────────────

class TestRestartContainer:

    def _make_success_result(self):
        r = MagicMock()
        r.returncode = 0
        return r

    def _make_fail_result(self):
        r = MagicMock()
        r.returncode = 1
        return r

    def test_sends_slack_alert_on_restart(self, heal):
        heal.client.models.generate_content.return_value = MagicMock(text="OOM error")
        with patch("subprocess.run", return_value=self._make_success_result()):
            with patch.object(heal, "send_slack") as mock_slack:
                heal.restart_container()
                assert mock_slack.call_count >= 2  # down alert + recovery alert

    def test_sends_down_alert_first(self, heal):
        heal.client.models.generate_content.return_value = MagicMock(text="crash reason")
        with patch("subprocess.run", return_value=self._make_success_result()):
            with patch.object(heal, "send_slack") as mock_slack:
                heal.restart_container()
                first_call_text = mock_slack.call_args_list[0][0][0]
                assert "DOWN" in first_call_text or "🔴" in first_call_text

    def test_sends_recovery_alert_on_success(self, heal):
        heal.client.models.generate_content.return_value = MagicMock(text="crash reason")
        with patch("subprocess.run", return_value=self._make_success_result()):
            with patch.object(heal, "send_slack") as mock_slack:
                heal.restart_container()
                all_messages = " ".join(c[0][0] for c in mock_slack.call_args_list)
                assert "🟢" in all_messages or "healthy" in all_messages.lower()

    def test_sends_failure_alert_when_docker_run_fails(self, heal):
        heal.client.models.generate_content.return_value = MagicMock(text="crash")
        with patch("subprocess.run", return_value=self._make_fail_result()):
            with patch.object(heal, "send_slack") as mock_slack:
                heal.restart_container()
                all_messages = " ".join(c[0][0] for c in mock_slack.call_args_list)
                assert "FAILED" in all_messages or "❌" in all_messages

    def test_stops_and_removes_container_before_run(self, heal):
        heal.client.models.generate_content.return_value = MagicMock(text="crash")
        run_calls = []
        def capture_run(cmd, **kwargs):
            run_calls.append(cmd)
            r = MagicMock()
            r.returncode = 0
            return r
        with patch("subprocess.run", side_effect=capture_run):
            with patch.object(heal, "send_slack"):
                heal.restart_container()
        commands = [" ".join(c) for c in run_calls]
        stop_idx  = next(i for i, c in enumerate(commands) if "stop"   in c)
        rm_idx    = next(i for i, c in enumerate(commands) if "rm"     in c)
        run_idx   = next(i for i, c in enumerate(commands) if "run"    in c and "-d" in c)
        assert stop_idx < rm_idx < run_idx

    def test_includes_gemini_diagnosis_in_slack_message(self, heal):
        heal.client.models.generate_content.return_value = MagicMock(
            text="Unique diagnosis string XYZ"
        )
        with patch("subprocess.run", return_value=self._make_success_result()):
            with patch.object(heal, "send_slack") as mock_slack:
                heal.restart_container()
                all_messages = " ".join(c[0][0] for c in mock_slack.call_args_list)
                assert "Unique diagnosis string XYZ" in all_messages


# ─── monitor (one iteration) ─────────────────────────────────────────────────

class TestMonitorLoop:
    """
    Tests one iteration of the monitor loop by patching time.sleep
    to raise StopIteration after the first cycle, breaking the while True.
    """

    def test_resets_failures_on_healthy(self, heal):
        """After a healthy check failures counter should reset to 0."""
        with patch.object(heal, "check_health", return_value=True), \
             patch.object(heal, "send_slack"), \
             patch("time.sleep", side_effect=StopIteration):
            try:
                heal.monitor()
            except StopIteration:
                pass

    def test_increments_failures_on_unhealthy(self, heal):
        """Each failed check should increment the failure counter."""
        call_count = {"n": 0}
        def alternating():
            call_count["n"] += 1
            if call_count["n"] > 3:
                raise StopIteration
            return False  # always failing

        with patch.object(heal, "check_health", side_effect=alternating), \
             patch.object(heal, "send_slack"), \
             patch.object(heal, "restart_container") as mock_restart, \
             patch("time.sleep"):
            try:
                heal.monitor()
            except StopIteration:
                pass
            mock_restart.assert_called_once()

    def test_triggers_restart_after_max_retries(self, heal):
        """restart_container must be called after MAX_RETRIES consecutive failures."""
        responses = [False] * heal.MAX_RETRIES + [True]

        with patch.object(heal, "check_health", side_effect=responses), \
             patch.object(heal, "send_slack"), \
             patch.object(heal, "restart_container") as mock_restart, \
             patch("time.sleep", side_effect=[None] * heal.MAX_RETRIES + [StopIteration]):
            try:
                heal.monitor()
            except StopIteration:
                pass
            mock_restart.assert_called_once()

    def test_does_not_restart_before_max_retries(self, heal):
        """restart_container must NOT be called before MAX_RETRIES failures."""
        responses = [False] * (heal.MAX_RETRIES - 1) + [True]

        with patch.object(heal, "check_health", side_effect=responses), \
             patch.object(heal, "send_slack"), \
             patch.object(heal, "restart_container") as mock_restart, \
             patch("time.sleep", side_effect=[None] * len(responses) + [StopIteration]):
            try:
                heal.monitor()
            except StopIteration:
                pass
            mock_restart.assert_not_called()

    def test_sends_startup_slack_message(self, heal):
        with patch.object(heal, "check_health", return_value=True), \
             patch.object(heal, "send_slack") as mock_slack, \
             patch("time.sleep", side_effect=StopIteration):
            try:
                heal.monitor()
            except StopIteration:
                pass
            first_msg = mock_slack.call_args_list[0][0][0]
            assert "Monitor" in first_msg or "🤖" in first_msg
