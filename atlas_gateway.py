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
        
import datetime

def log_decision(payload):
    if not payload.get("Decision") or not payload.get("Reason") or not payload.get("System_Affected"):
        return {"status": "rejected", "message": "Missing required fields"}

    decision_id = f"D-{int(datetime.datetime.now().timestamp()*1000)}"
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    record = {
        "Decision_ID": decision_id,
        "Date": today,
        "Decision": payload["Decision"],
        "Reason": payload["Reason"],
        "System_Affected": payload["System_Affected"],
        "Decision_Owner": payload.get("Decision_Owner", "Naushad")
    }

    response = requests.post(
        APPS_SCRIPT_URL,
        json={
            "action": "append_decision",
            "data": record
        }
    )

    return {
        "status": "logged",
        "decision_id": decision_id
    }
    # send to Apps Script (only for storage)
    response = requests.post(
        APPS_SCRIPT_URL,
        json={
            "action": "append_decision",
            "data": record
        }
    )

    return {
        "status": "logged",
        "decision_id": decision_id
    }
