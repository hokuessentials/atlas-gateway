from flask import Flask, request, jsonify
import requests
import os
import datetime

app = Flask(__name__)

# Environment variable (set in Railway)
APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL")


# ---------- HEALTH CHECK ----------
@app.route("/")
def home():
    return "Atlas is running"


# ---------- MAIN COMMAND ROUTER ----------
@app.route("/atlas/command", methods=["POST"])
def atlas_command():
    data = request.json
    command = data.get("command")
    payload = data.get("payload", {})

    if not command:
        return jsonify({
            "status": "error",
            "message": "No command provided"
        })

    try:

        # 🔥 DECISION ENGINE (NOW ON RAILWAY)
        if command == "log_decision":
            return jsonify(log_decision(payload))

        return jsonify({
            "status": "error",
            "message": f"Unknown command: {command}"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })


# ---------- DECISION FUNCTION ----------
def log_decision(payload):

    # 🚨 STRICT VALIDATION
    if not payload.get("Decision") or not payload.get("Reason") or not payload.get("System_Affected"):
        return {
            "status": "rejected",
            "message": "Missing required fields: Decision, Reason, System_Affected"
        }

    # Generate unique ID
    decision_id = f"D-{int(datetime.datetime.now().timestamp() * 1000)}"

    # Date format (matches schema)
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # Schema-aligned record
    record = {
        "Decision_ID": decision_id,
        "Date": today,
        "Decision": payload["Decision"],
        "Reason": payload["Reason"],
        "System_Affected": payload["System_Affected"],
        "Decision_Owner": payload.get("Decision_Owner", "Naushad")
    }

    # 🔥 ONLY STORAGE CALL (Apps Script is now dumb storage)
    response = requests.post(
        APPS_SCRIPT_URL,
        json={
            "action": "append_decision",
            "data": record
        }
    )

    # Optional: check response
    try:
        res_json = response.json()
    except:
        res_json = {"status": "unknown"}

    return {
        "status": "logged",
        "decision_id": decision_id,
        "storage_response": res_json
    }
