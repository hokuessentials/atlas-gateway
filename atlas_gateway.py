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
            print("OUTCOME:", val)
            session_data["decisions"].reverse()
            session_data["roi_list"].reverse()
            session_data["risk_list"].reverse()
            session_data["confidence_list"].reverse()
            session_data["outcome_list"].reverse()

    except Exception as e:
        print("SESSION ERROR:", e)

    return session_data

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

@app.route("/atlas/action", methods=["GET", "POST"])
def atlas_action():
    if request.method == "GET":
        return jsonify({"message": "Use POST with JSON body"})
    try:
        input_data = request.get_json(force=True)

        session = load_session_from_sheet()

        # attach active_state from input
        session["active_state"] = input_data.get("active_state", {})

        result = generate_intelligent_action(session)

        return jsonify({
            "status": "success",
            "result": result
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)        