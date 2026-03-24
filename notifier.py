import requests
from google import genai
import os

# Load secrets from environment variables
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

client = genai.Client(api_key=GEMINI_API_KEY)

def analyze_and_alert(error_log):
    print("Sending error to Gemini for analysis...")
    prompt = f"You are a DevOps assistant. Read this error log and explain exactly why it crashed in ONE simple sentence. Do not use markdown. Error: {error_log}"
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        ai_summary = response.text.strip()
    except Exception as e:
        ai_summary = f"Could not reach Gemini API: {str(e)}"

    slack_message = {
        "text": f"🚨 *Self-Healing Triggered!*\n\n*What happened:* The container crashed and was auto-restarted.\n*AI Root Cause Analysis:* {ai_summary}"
    }
    print("Sending alert to Slack...")
    requests.post(SLACK_WEBHOOK_URL, json=slack_message)
    print("Alert sent!")

if __name__ == "__main__":
    fake_error = "Traceback (most recent call last): File 'app.py', line 45, in <module> KeyError: 'DATABASE_URL'"
    analyze_and_alert(fake_error)