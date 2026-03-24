import os
import subprocess
import time
import requests
from google import genai

HEALTH_URL = "http://localhost:5000/health"
CONTAINER_NAME = "myapp"
IMAGE_NAME = "vivekbommalla1251/self-healing-app:latest"
MAX_RETRIES = 3
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

client = genai.Client(api_key=GEMINI_API_KEY)

def send_slack(message):
    try:
        requests.post(SLACK_WEBHOOK, json={"text": message})
    except Exception as e:
        print(f"Slack failed: {e}")

def get_container_logs():
    try:
        result = subprocess.run(["docker", "logs", "--tail", "20", CONTAINER_NAME], capture_output=True, text=True)
        return result.stdout + result.stderr
    except:
        return "No logs available"

def gemini_diagnose(logs):
    try:
        prompt = f"You are a DevOps AI. Analyze these Docker logs and explain in 2-3 sentences what went wrong:\n\n{logs}"
        response = client.models.generate_content(model="model="model="gemini-2.0-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"Gemini diagnosis failed: {e}"

def check_health():
    try:
        return requests.get(HEALTH_URL, timeout=5).status_code == 200
    except:
        return False

def restart_container():
    print("Restarting...")
    logs = get_container_logs()
    diagnosis = gemini_diagnose(logs)
    send_slack(f"🔴 *App is DOWN!*\n\n🤖 *Gemini AI Diagnosis:*\n{diagnosis}\n\n⚙️ Auto-restarting now...")
    subprocess.run(["docker", "stop", CONTAINER_NAME], capture_output=True)
    subprocess.run(["docker", "rm", CONTAINER_NAME], capture_output=True)
    result = subprocess.run(["docker", "run", "-d", "--name", CONTAINER_NAME, "-p", "5000:5000", IMAGE_NAME], capture_output=True)
    if result.returncode == 0:
        send_slack("🟢 *App AUTO-RESTARTED and healthy!*")
    else:
        send_slack("❌ *Auto-restart FAILED!*")

def monitor():
    print("👀 AI Monitor started...")
    send_slack("🤖 *Gemini AI Monitor Started*\nWatching http://44.211.185.25:5000/health")
    failures = 0
    while True:
        if check_health():
            print("✅ Healthy")
            failures = 0
        else:
            failures += 1
            print(f"⚠️  Failure {failures}/{MAX_RETRIES}")
            if failures >= MAX_RETRIES:
                restart_container()
                failures = 0
        time.sleep(10)

if __name__ == "__main__":
    monitor()