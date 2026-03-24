# ================================
# 1. IMPORTS
# ================================
from flask import Flask, request, jsonify
import requests
import datetime
import json


# ================================
# 2. APP INITIALIZATION
# ================================
app = Flask(__name__)

APPS_SCRIPT_URL = "https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec"


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
    module = record.get("Module")

    SESSION_DATA["session_id"] = record.get("Session_ID")
    SESSION_DATA["decisions"].append(record.get("Title"))

    if module not in SESSION_DATA["module_count"]:
        SESSION_DATA["module_count"][module] = 0

    SESSION_DATA["module_count"][module] += 1


def load_session_from_sheet():
    try:
        # Reset before loading (prevents duplicates)
        SESSION_DATA["decisions"] = []
        SESSION_DATA["module_count"] = {}

        response = requests.get(APPS_SCRIPT_URL + "?action=get_last_session", timeout=10)
        data = json.loads(response.text)

        if not data or "records" not in data:
            return

        for r in data["records"]:
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


def calculate_progress():
    total = len(SESSION_DATA["decisions"])
    modules = SESSION_DATA["module_count"]

    if total == 0:
        return {}

    productivity = min(1, total / 10)

    max_module = max(modules, key=modules.get)
    focus_score = modules[max_module] / total

    if total >= 5:
        momentum = "High"
    elif total >= 3:
        momentum = "Medium"
    else:
        momentum = "Low"

    return {
        "total_decisions": total,
        "productivity_score": round(productivity, 2),
        "focus_area": max_module,
        "focus_score": round(focus_score, 2),
        "momentum": momentum
    }


def generate_triggers():
    total = len(SESSION_DATA["decisions"])
    modules = SESSION_DATA["module_count"]

    alerts = []
    recommendation = None

    if total < 5:
        alerts.append("Increase decision velocity")

    if modules:
        max_module = max(modules, key=modules.get)
        if modules[max_module] / total > 0.7:
            alerts.append(f"Over-focus on {max_module}")

    all_modules = ["Product", "Supplier", "Finance", "Marketing"]
    missing = [m for m in all_modules if m not in modules]

    if missing:
        recommendation = f"Take next decision in {missing[0]}"

    return {
        "alerts": alerts,
        "recommendation": recommendation
    }


# ================================
# 6. BUSINESS LOGIC
# ================================
def log_decision(payload):

    if not payload:
        return {"status": "rejected", "message": "Payload missing"}

    if not payload.get("title") or not payload.get("description") or not payload.get("module"):
        return {"status": "rejected", "message": "Missing required fields"}

    decision_id = f"D-{int(datetime.datetime.now().timestamp()*1000)}"

    risk, confidence, roi = calculate_scores(payload)

    record = {
        "Decision_ID": decision_id,
        "Session_ID": generate_session_id(),
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Title": payload.get("title"),
        "Description": payload.get("description"),
        "Module": payload.get("module"),
        "Expected_ROI": roi,
        "Risk_Score": risk,
        "Confidence_Level": confidence,
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
        requests.post(APPS_SCRIPT_URL, json={"action": "append_decision", "data": record}, timeout=10)
        return {"status": "logged", "decision_id": decision_id}

    except Exception as e:
        return {"status": "partial_success", "error": str(e)}


def log_decision_from_text(text):
    return log_decision({
        "title": text[:50],
        "description": text,
        "module": "General"
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

        if data.get("input"):
            return jsonify(log_decision_from_text(data["input"]))

        if data.get("command") == "log_decision":
            return jsonify(log_decision(data.get("payload")))

        return jsonify({"status": "error"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/atlas/state")
def get_state():
    return jsonify({"current_state": CURRENT_STATE})


@app.route("/atlas/session")
def get_session():
    if not SESSION_DATA["decisions"]:
        load_session_from_sheet()
    return jsonify({"session_data": SESSION_DATA})


@app.route("/atlas/progress")
def get_progress():
    if not SESSION_DATA["decisions"]:
        load_session_from_sheet()
    return jsonify({"progress": calculate_progress()})


@app.route("/atlas/trigger")
def get_trigger():
    if not SESSION_DATA["decisions"]:
        load_session_from_sheet()
    return jsonify({"triggers": generate_triggers()})


# ================================
# 8. SERVER START
# ================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
