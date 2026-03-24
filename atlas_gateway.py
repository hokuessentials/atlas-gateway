# ================================
# 1. IMPORTS
# ================================
from flask import Flask, request, jsonify
import requests
import os
import datetime


# ================================
# 2. APP INITIALIZATION
# ================================
app = Flask(__name__)
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzE0aSjAWHgONC-GT4hFlMmq830hkMWsKR96Hla2yxOgzLhcPtNH-Ua3Llqjz9GAh5Xkg/exec"
load_session_from_sheet()

# ================================
# 3. GLOBAL STATE
# ================================
CURRENT_STATE = {
    "last_decision": None,
    "active_module": None,
    "total_decisions": 0,
    "last_updated": None
}
SESSION_DATA = {
    "session_id": None,
    "decisions": [],
    "module_count": {}
}

# ================================
# 4. UTILITY FUNCTIONS
# ================================
def generate_session_id():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return f"S-{today}"


# ================================
# 5. CORE ENGINES
# ================================
def calculate_scores(payload):
    module = (payload.get("module") or "General").lower()
    reversible = payload.get("reversible_flag", True)
    description = payload.get("description", "")
    tags = payload.get("tags", "")
    decision_type = payload.get("decision_type", "general")

    base_risk = {
        "finance": 0.6,
        "supplier": 0.5,
        "product": 0.4,
        "marketing": 0.5,
        "general": 0.3
    }.get(module, 0.3)

    base_risk += 0.2 if not reversible else -0.2
    risk_score = max(0, min(1, base_risk))

    confidence = 0.5
    if len(description) > 50:
        confidence += 0.2
    if tags:
        confidence += 0.1
    if decision_type == "strategic":
        confidence += 0.1
    confidence = min(1, confidence)

    roi_map = {
        "product": 25,
        "finance": 20,
        "supplier": 15,
        "marketing": 30,
        "general": 10
    }

    expected_roi = roi_map.get(module, 10)

    return risk_score, confidence, expected_roi


def update_current_state(record):
    CURRENT_STATE["last_decision"] = record.get("Title")
    CURRENT_STATE["active_module"] = record.get("Module")
    CURRENT_STATE["total_decisions"] += 1
    CURRENT_STATE["last_updated"] = record.get("Timestamp")

def update_session_data(record):
    session_id = record.get("Session_ID")
    module = record.get("Module")

    SESSION_DATA["session_id"] = session_id
    SESSION_DATA["decisions"].append(record.get("Title"))

    if module not in SESSION_DATA["module_count"]:
        SESSION_DATA["module_count"][module] = 0

    SESSION_DATA["module_count"][module] += 1

def load_session_from_sheet():
    try:
        import json

        response = requests.get(APPS_SCRIPT_URL + "?action=get_last_session", timeout=10)

        data = json.loads(response.text)

        print("LOADED DATA:", data)

        if not data or "records" not in data:
            return

        records = data["records"]

        for r in records:
            SESSION_DATA["session_id"] = r.get("Session_ID")
            SESSION_DATA["decisions"].append(r.get("Title"))

            module = r.get("Module")
            if module not in SESSION_DATA["module_count"]:
                SESSION_DATA["module_count"][module] = 0
            SESSION_DATA["module_count"][module] += 1

            CURRENT_STATE["last_decision"] = r.get("Title")
            CURRENT_STATE["active_module"] = module
            CURRENT_STATE["total_decisions"] += 1
            CURRENT_STATE["last_updated"] = r.get("Timestamp")

    except Exception as e:
        print("Load session failed:", e)
        
# ================================
# 6. BUSINESS LOGIC
# ================================
def log_decision(payload):

    if not payload:
        return {"status": "rejected", "message": "Payload missing"}

    if not payload.get("title") or not payload.get("description") or not payload.get("module"):
        return {"status": "rejected", "message": "Missing required fields"}

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
    update_session_data(record)

    try:
        response = requests.post(
            APPS_SCRIPT_URL,
            json={"action": "append_decision", "data": record},
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
            "error": str(e)
        }


def log_decision_from_text(text):
    return log_decision({
        "title": text[:50],
        "description": text,
        "module": "General",
        "reversible_flag": True,
        "decision_owner": "Naushad",
        "tags": "auto",
        "decision_type": "general"
    })


# ================================
# 7. API ROUTES
# ================================
@app.route("/")
def home():
    return "Atlas is running"


@app.route("/atlas/command", methods=["POST"])
def atlas_command():
    try:
        data = request.get_json(force=True)

        raw_input = data.get("input", "").lower()
        if raw_input:
            if "log decision" in raw_input:
                return jsonify(log_decision_from_text(raw_input))
            return jsonify({"status": "error", "message": "Could not understand input"})

        command = data.get("command", "").strip().lower()
        payload = data.get("payload")

        if "log_decision" in command:
            return jsonify(log_decision(payload))

        return jsonify({"status": "error", "message": "Unknown command"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/atlas/state", methods=["GET"])
def get_state():
    return jsonify({
        "status": "success",
        "current_state": CURRENT_STATE
    })
@app.route("/atlas/session", methods=["GET"])
def get_session():
    return jsonify({
        "status": "success",
        "session_data": SESSION_DATA
    })
load_session_from_sheet()
# ================================
# 8. SERVER START
# ================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
