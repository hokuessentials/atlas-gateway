from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL")

@app.route("/")
def home():
    return "Atlas is running"

@app.route("/atlas/command", methods=["POST"])
def atlas_command():
    data = request.json
    command = data.get("command")
    payload = data.get("payload", {})

    if not command:
        return jsonify({"error": "No command provided"})

    try:
        response = requests.post(
            APPS_SCRIPT_URL,
            json={
                "command": command,
                "payload": payload
            }
        )
        return jsonify(response.json())

    except Exception as e:
        return jsonify({"error": str(e)})
