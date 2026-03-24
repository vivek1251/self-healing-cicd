from flask import Flask, jsonify, request
import os
import time
import datetime

app = Flask(__name__)
START_TIME = time.time()

deployments = [
    {"id": 1, "status": "success", "branch": "main", "triggered_by": "push", "timestamp": "2026-03-22T08:00:00Z"},
    {"id": 2, "status": "failed",  "branch": "feature/auth", "triggered_by": "push", "timestamp": "2026-03-23T14:00:00Z"},
    {"id": 3, "status": "success", "branch": "main", "triggered_by": "auto-heal", "timestamp": "2026-03-24T09:00:00Z"},
]

alerts = [
    {"id": 1, "type": "health_fail",   "message": "App returned 500 — triggering auto-heal", "resolved": True,  "timestamp": "2026-03-23T14:05:00Z"},
    {"id": 2, "type": "auto_restarted","message": "Container restarted successfully",          "resolved": True,  "timestamp": "2026-03-23T14:06:00Z"},
    {"id": 3, "type": "health_fail",   "message": "App unreachable — retrying (1/3)",          "resolved": False, "timestamp": "2026-03-24T10:00:00Z"},
]

@app.route("/")
def home():
    return jsonify({"message": "Self-Healing CI/CD App", "version": "1.0", "docs": "/status"})

@app.route("/health")
def health():
    if os.environ.get("FORCE_FAIL") == "true":
        return jsonify({"status": "unhealthy"}), 500
    return jsonify({"status": "healthy"}), 200

@app.route("/status")
def status():
    uptime = int(time.time() - START_TIME)
    return jsonify({
        "status": "running",
        "uptime_seconds": uptime,
        "version": "1.0",
        "environment": os.environ.get("APP_ENV", "production"),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

@app.route("/metrics")
def metrics():
    total = len(deployments)
    successful = sum(1 for d in deployments if d["status"] == "success")
    heals = sum(1 for d in deployments if d["triggered_by"] == "auto-heal")
    return jsonify({
        "deployments": {
            "total": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate_percent": round((successful / total) * 100, 1) if total else 0
        },
        "auto_healing": {
            "total_heals": heals,
            "max_retries": 3,
            "check_interval_seconds": 10
        },
        "alerts": {
            "total": len(alerts),
            "unresolved": sum(1 for a in alerts if not a["resolved"])
        }
    })

@app.route("/deployments", methods=["GET"])
def get_deployments():
    return jsonify({"deployments": deployments, "total": len(deployments)})

@app.route("/deployments/<int:deploy_id>", methods=["GET"])
def get_deployment(deploy_id):
    deployment = next((d for d in deployments if d["id"] == deploy_id), None)
    if not deployment:
        return jsonify({"error": "Deployment not found"}), 404
    return jsonify(deployment)

@app.route("/deployments", methods=["POST"])
def create_deployment():
    body = request.get_json() or {}
    branch = body.get("branch", "main")
    new = {
        "id": len(deployments) + 1,
        "status": "success",
        "branch": branch,
        "triggered_by": body.get("triggered_by", "api"),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    deployments.append(new)
    return jsonify(new), 201

@app.route("/alerts", methods=["GET"])
def get_alerts():
    unresolved_only = request.args.get("unresolved") == "true"
    filtered = [a for a in alerts if not a["resolved"]] if unresolved_only else alerts
    return jsonify({"alerts": filtered, "total": len(filtered)})
@app.route("/version")
def version():
    return jsonify({
        "version": "1.0.0",
        "build": "stable",
        "author": "vivek1251"
    })
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
