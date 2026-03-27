from flask import Flask, request, jsonify
import requests
import datetime
import json
from intelligence_engine import generate_intelligent_action
import state_engine

update_state = state_engine.update_state
add_blocker = state_engine.add_blocker
clear_blockers = state_engine.clear_blockers
complete_current_task = state_engine.complete_current_task
ACTIVE_STATE = state_engine.ACTIVE_STATE

app = Flask(__name__)

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzE0aSjAWHgONC-GT4hFlMmq830hkMWsKR96Hla2yxOgzLhcPtNH-Ua3Llqjz9GAh5Xkg/exec"

# =========================
# 🔵 MEMORY LAYER (PHASE 1)
# =========================

def save_state_to_sheet(active_state):
    try:
        payload = {
            "action": "save_state",
            "data": active_state
        }
        resp = requests.post(APPS_SCRIPT_URL, json=payload, timeout=3)
        print("🔥 SAVE RESPONSE:", resp.text)
    except Exception as e:
        print("STATE SAVE ERROR:", e)


def load_state_from_sheet():
    try:
        url = APPS_SCRIPT_URL + "?action=get_state"
        resp = requests.get(url, timeout=3)

        print("🔥 LOAD RESPONSE RAW:", resp.text)

        if not resp or resp.status_code != 200:
            return {}

        text = resp.text

        if text.startswith(")]}'"):
            text = text[4:]

        data = json.loads(text)
        return data.get("active_state", {})

    except Exception as e:
        print("STATE LOAD ERROR:", e)
        return {}

# =========================
# SESSION LOAD (EXISTING)
# =========================

def load_session_from_sheet():

    session_data = {
        "session_id": None,
        "decisions": [],
        "module_count": {},
        "roi_list": [],
        "risk_list": [],
        "confidence_list": [],
        "outcome_list": []
    }

    try:
        url = APPS_SCRIPT_URL + "?action=get_last_session"
        resp = requests.get(url, timeout=20)

        if not resp or resp.status_code != 200:
            return session_data

        text = resp.text

        if text.startswith(")]}'"):
            text = text[4:]

        data = json.loads(text)
        records = data.get("records", [])

        for r in records:
            title = r.get("Title")
            module = r.get("Module")

            if not title or not module:
                continue

            session_data["session_id"] = r.get("Session_ID")
            session_data["decisions"].append(title)

            session_data["module_count"][module] = \
                session_data["module_count"].get(module, 0) + 1

            session_data["roi_list"].append(float(r.get("Expected_ROI") or 0))
            session_data["risk_list"].append(float(r.get("Risk_Score") or 0))
            session_data["confidence_list"].append(float(r.get("Confidence_Level") or 0))
            val = r.get("Outcome_Status") or ""
            session_data["outcome_list"].append(str(val).strip().lower())

        # reverse once after loop (fix)
        session_data["decisions"].reverse()
        session_data["roi_list"].reverse()
        session_data["risk_list"].reverse()
        session_data["confidence_list"].reverse()
        session_data["outcome_list"].reverse()

    except Exception as e:
        print("SESSION ERROR:", e)

    return session_data

# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return "Atlas is running"

@app.route("/atlas/state/full")
def full_state():
    try:
        session = load_session_from_sheet()

        if not session["decisions"]:
            return jsonify({
                "active_state": ACTIVE_STATE,
                "status": "no_data"
            })

        update_state(session, {})

        return jsonify({
            "active_state": ACTIVE_STATE,
            "decision_count": len(session["decisions"]),
            "status": "success"
        })

    except Exception as e:
        print("🔥 ERROR IN /atlas/state/full:", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route("/atlas/command", methods=["GET", "POST"])
def atlas_command():
    data = request.get_json(force=True)

    if data.get("command") == "log_decision":
        return jsonify({"status": "logged"})

    return jsonify({"status": "invalid"})

@app.route("/atlas/state/block", methods=["GET", "POST"])
def block():
    add_blocker(request.get_json().get("description"))
    return jsonify({"status": "blocked"})

@app.route("/atlas/state/unblock", methods=["GET", "POST"])
def unblock():
    clear_blockers()
    return jsonify({"status": "unblocked"})

@app.route("/atlas/task/complete", methods=["GET", "POST"])
def complete_task():
    complete_current_task()
    return jsonify({"status": "task_completed"})

# =========================
# MAIN INTELLIGENCE ROUTE
# =========================

@app.route("/atlas/action", methods=["GET", "POST"])
def atlas_action():
    
    if request.method == "GET":
        return jsonify({"message": "Use POST with JSON body"})

    try:
        input_data = request.get_json(force=True)

        # 🔵 LOAD MEMORY STATE FIRST
        try:
            saved_state = load_state_from_sheet()
        except Exception as e:
            print("STATE LOAD FAIL:", e)
            saved_state = {}

        # 🔥 FORCE MEMORY PRIORITY
        if saved_state and isinstance(saved_state, dict):
            active_state = saved_state
        else:
            active_state = input_data.get("active_state", {})
        
        print("🔥 RAW SAVED STATE:", saved_state)
        print("🔥 FINAL ACTIVE STATE:", active_state)

        # Load session
        session = load_session_from_sheet()

        session["active_state"] = active_state

        # Run intelligence
        result = generate_intelligent_action(session)

        # 🔵 SAVE UPDATED STATE
        if result.get("execution_state"):
            try:
                save_state_to_sheet({
                    "current_step": result.get("execution_state", {}).get("current_step"),
                    "completed_steps": result.get("execution_state", {}).get("completed_steps", []),
                    "step_updates": result.get("execution_state", {}).get("step_updates", []),
                    "execution_plan": result.get("execution_plan", [])
                })
                print("🔥 SAVING STATE:", state)
            except Exception as e:
                print("STATE SAVE FAIL:", e)

        return jsonify({
            "status": "success",
            "result": result
        })

    except Exception as e:
        print("🔥 ACTION ERROR:", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        })

# =========================
# RUN SERVER
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)