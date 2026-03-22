from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "App is running", "version": "1.0"})

@app.route("/health")
def health():
    if os.environ.get("FORCE_FAIL") == "true":
        return jsonify({"status": "unhealthy"}), 500
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)