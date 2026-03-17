from flask import Flask, request, jsonify
import requests
import os
import datetime

app = Flask(__name__)

APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL")


# ---------------- HOME ----------------
@app.route("/")
def home():
    return "Atlas is running"


# ---------------- MAIN ROUTE ----------------
@app.route("/atlas/command", methods=["POST"])
def atlas_command():
    try:
        data = request.get_json(force=True)

        # ----------- MODE 1: NATURAL LANGUAGE (input) -----------
        raw_input = data.get("input", "").lower()

        if raw_input:
            if "log decision" in raw_input:
                return jsonify(log_decision_from_text(raw_input))

            return jsonify({
                "status": "error",
                "message": f"Could not understand input: {raw_input}"
            })

        # ----------- MODE 2: STRUCTURED (command + payload) -----------
        command = data.get("command", "").strip().lower().replace(" ", "_")

        payload = data.get("payload")

        # fallback if GPT sends flat fields
        if not payload:
            payload = {
                "Decision": data.get("Decision"),
                "Reason": data.get("Reason"),
                "System_Affected": data.get("System_Affected"),
                "Decision_Owner": data.get("Decision_Owner")
            }

        if not command:
            return jsonify({"status": "error", "message": "No command provided"})

        if "log_decision" in command:
            return jsonify(log_decision(payload))

        return jsonify({
            "status": "error",
            "message": f"Unknown command received: {command}"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })


# ---------------- LOG DECISION ----------------
def log_decision(payload):

    if not payload.get("Decision") or not payload.get("Reason") or not payload.get("System_Affected"):
        return {
            "status": "rejected",
            "message": "Missing required fields"
        }

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

    # 🔥 SAFE CALL TO APPS SCRIPT
    try:
        response = requests.post(
            APPS_SCRIPT_URL,
            json={
                "action": "append_decision",
                "data": record
            },
            timeout=5
        )

        return {
            "status": "logged",
            "decision_id": decision_id,
            "sheet_response": response.json()
        }

    except Exception as e:
        return {
            "status": "partial_success",
            "decision_id": decision_id,
            "error": str(e),
            "note": "Saved in system but not in sheet"
        }


# ---------------- NLP PARSER ----------------
def log_decision_from_text(text):

    return log_decision({
        "Decision": text,
        "Reason": "Auto-parsed from input",
        "System_Affected": "General",
        "Decision_Owner": "Naushad"
    })


# ---------------- START SERVER ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
