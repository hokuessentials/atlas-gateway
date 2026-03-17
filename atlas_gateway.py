from flask import Flask, request, jsonify
import requests
import os
import datetime

app = Flask(__name__)

APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL")

@app.route("/")
def home():
    return "Atlas is running"

@app.route("/atlas/command", methods=["POST"])
def atlas_command():
    data = request.json
    command = data.get("command", "").strip().lower().replace(" ", "_")
    payload = data.get("payload", {})

    if not command:
        return jsonify({"status": "error", "message": "No command provided"})

    if command == "log_decision":
    return jsonify(log_decision(payload))

return jsonify({
    "status": "error",
    "message": f"Unknown command received: {command}"
})


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

    requests.post(
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


# 🔥 IMPORTANT FOR RAILWAY
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
