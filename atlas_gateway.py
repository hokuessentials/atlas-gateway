from flask import Flask, request, jsonify
import requests
import os
import datetime

app = Flask(__name__)
CURRENT_STATE = {
    "last_decision": None,
    "active_module": None,
    "total_decisions": 0,
    "last_updated": None
}

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

        @app.route("/atlas/state", methods=["GET"])
def get_state():
    try:
        return jsonify({
            "status": "success",
            "current_state": CURRENT_STATE
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })
        # ----------- MODE 2: STRUCTURED (command + payload) -----------
        command = data.get("command", "").strip().lower().replace(" ", "_")
        payload = data.get("payload")

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
def calculate_scores(payload):
    module = (payload.get("module") or "General").lower()
    reversible = payload.get("reversible_flag", True)
    description = payload.get("description", "")
    tags = payload.get("tags", "")
    decision_type = payload.get("decision_type", "general")

    # --- Risk ---
    base_risk = {
        "finance": 0.6,
        "supplier": 0.5,
        "product": 0.4,
        "marketing": 0.5,
        "general": 0.3
    }.get(module, 0.3)

    if reversible:
        base_risk -= 0.2
    else:
        base_risk += 0.2

    risk_score = max(0, min(1, base_risk))

    # --- Confidence ---
    confidence = 0.5

    if len(description) > 50:
        confidence += 0.2

    if tags:
        confidence += 0.1

    if decision_type == "strategic":
        confidence += 0.1

    confidence = min(1, confidence)

    # --- ROI ---
    roi_map = {
        "product": 25,
        "finance": 20,
        "supplier": 15,
        "marketing": 30,
        "general": 10
    }

    expected_roi = roi_map.get(module, 10)

    return risk_score, confidence, expected_roi

def generate_session_id():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return f"S-{today}"

CURRENT_STATE = {
    "last_decision": None,
    "active_module": None,
    "total_decisions": 0,
    "last_updated": None
}

def update_current_state(record):
    CURRENT_STATE["last_decision"] = record.get("Title")
    CURRENT_STATE["active_module"] = record.get("Module")
    CURRENT_STATE["total_decisions"] += 1
    CURRENT_STATE["last_updated"] = record.get("Timestamp")

# ---------------- LOG DECISION ----------------
def log_decision(payload):

    if not payload:
        return {
            "status": "rejected",
            "message": "Payload missing"
        }

    # ✅ NEW VALIDATION (UPDATED)
    if not payload.get("title") or not payload.get("description") or not payload.get("module"):
        return {
            "status": "rejected",
            "message": "Missing required fields (title, description, module)"
        }

    decision_id = f"D-{int(datetime.datetime.now().timestamp()*1000)}"
    risk_score, confidence_level, expected_roi = calculate_scores(payload)

    record = {
        "Decision_ID": decision_id,
        "Session_ID": generate_session_id(),
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Title": payload.get("title"),
        "Description": payload.get("description"),
        "Module": payload.get("module"),
        "Expected_ROI": expected_roi,
        "Risk_Score": risk_score,
        "Confidence_Level": confidence_level,
        "Reversible_Flag": payload.get("reversible_flag", True),
        "Decision_Owner": payload.get("decision_owner", "Naushad"),
        "Tags": payload.get("tags", ""),
        "Decision_Type": payload.get("decision_type", "general"),
        "Outcome_Status": "pending",
        "Lesson_Learned": ""
    }
    update_current_state(record)

    # 🔥 SEND TO GOOGLE SHEET
    try:
        response = requests.post(
            APPS_SCRIPT_URL,
            json={
                "action": "append_decision",
                "data": record
            },
            timeout=15
        )

        return {
            "status": "logged",
            "decision_id": decision_id,
            "sheet_response": response.text
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
        "title": text[:50],
        "description": text,
        "module": "General",
        "expected_roi": 0,
        "risk_score": 0.5,
        "confidence_level": 0.5,
        "reversible_flag": True,
        "decision_owner": "Naushad",
        "tags": "auto",
        "decision_type": "general"
    })


# ---------------- START SERVER ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
