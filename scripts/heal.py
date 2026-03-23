import os
import subprocess
import time
import requests

HEALTH_URL = "http://localhost:5000/health"
CONTAINER_NAME = "myapp"
IMAGE_NAME = "vivekbommalla1251/self-healing-app:latest"
MAX_RETRIES = 3
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "")

def send_slack(message):
    try:
        requests.post(SLACK_WEBHOOK, json={"text": message})
    except Exception as e:
        print(f"Slack failed: {e}")

def check_health():
    try:
        return requests.get(HEALTH_URL, timeout=5).status_code == 200
    except:
        return False

def restart_container():
    print("Restarting...")
    send_slack("App is DOWN! Auto-restarting...")
    subprocess.run(["docker", "stop", CONTAINER_NAME], capture_output=True)
    subprocess.run(["docker", "rm", CONTAINER_NAME], capture_output=True)
    result = subprocess.run(["docker", "run", "-d", "--name", CONTAINER_NAME, "-p", "5000:5000", IMAGE_NAME], capture_output=True)
    if result.returncode == 0:
        send_slack("App AUTO-RESTARTED and healthy!")
    else:
        send_slack("Auto-restart FAILED!")

def monitor():
    print("Monitoring started...")
    failures = 0
    while True:
        if check_health():
            print("Healthy")
            failures = 0
        else:
            failures += 1
            print(f"Failure {failures}/{MAX_RETRIES}")
            if failures >= MAX_RETRIES:
                restart_container()
                failures = 0
        time.sleep(10)

if __name__ == "__main__":
    monitor()