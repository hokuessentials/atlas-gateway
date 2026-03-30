from flask import Flask, request, jsonify
import requests
import json
import time
from intelligence_engine import generate_intelligent_action, is_step_allowed, get_candidate_steps, filter_allowed_candidates, select_better_step
import state_engine
from session_engine import evaluate_session_health

def read_active_state_from_sheet():

    SHEET_URL = "https://script.google.com/macros/s/AKfycbzE0aSjAWHgONC-GT4hFlMmq830hkMWsKR96Hla2yxOgzLhcPtNH-Ua3Llqjz9GAh5Xkg/exec"

    try:
        response = requests.get(f"{SHEET_URL}?action=read_active_state")

        if response.status_code != 200:
            return None

        data = response.json()

        return data.get("active_state")

    except Exception as e:
        print("❌ ACTIVE_STATE READ ERROR:", e)
        return None

update_state = state_engine.update_state
add_blocker = state_engine.add_blocker
clear_blockers = state_engine.clear_blockers
complete_current_task = state_engine.complete_current_task
ACTIVE_STATE = state_engine.ACTIVE_STATE

app = Flask(__name__)

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzE0aSjAWHgONC-GT4hFlMmq830hkMWsKR96Hla2yxOgzLhcPtNH-Ua3Llqjz9GAh5Xkg/exec"

# =========================
# 🔵 MEMORY LAYER
# =========================

def save_state_to_sheet(active_state):
    try:
        payload = {
            "action": "save_state",
            "data": active_state
        }

        print("🔥 SAVING STATE:", payload)

        headers = {
            "Content-Type": "application/json"
        }

        for attempt in range(2):
            try:
                resp = requests.post(
                    APPS_SCRIPT_URL,
                    data=json.dumps(payload),   # ✅ FIXED (NO json=payload)
                    headers=headers,
                    timeout=10,
                    allow_redirects=True
                )

                print("🔥 SAVE STATUS:", resp.status_code)
                print("🔥 SAVE RESPONSE:", resp.text)

                if resp and resp.status_code == 200:
                    return
                else:
                    print("⚠️ SAVE FAILED")

            except Exception as retry_error:
                print(f"⚠️ RETRY {attempt + 1} FAILED:", retry_error)

        print("❌ STATE SAVE FAILED AFTER RETRIES")

    except Exception as e:
        print("❌ STATE SAVE ERROR:", e)

def save_decision_to_sheet(decision_data):
    try:
        payload = {
            "action": "log_decision",
            "data": decision_data
        }

        headers = {
            "Content-Type": "application/json"
        }

        resp = requests.post(
            APPS_SCRIPT_URL,
            data=json.dumps(payload),
            headers=headers,
            timeout=10,
            allow_redirects=True
        )

        print("🔥 DECISION SAVE:", resp.text)

    except Exception as e:
        print("❌ DECISION SAVE ERROR:", e)       

def load_state_from_sheet():
    try:
        url = APPS_SCRIPT_URL + "?action=get_state"
        resp = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=10,
            allow_redirects=True
        )

        print("🔥 LOAD RESPONSE RAW:", resp.text)

        if not resp or resp.status_code != 200:
            return {}

        text = resp.text

        if text.startswith(")]}'"):
            text = text[4:]

        data = json.loads(text)

        state = data.get("active_state", {})

        if isinstance(state, str):
            try:
                state = json.loads(state)
            except:
                state = {}

        return state

    except Exception as e:
        print("STATE LOAD ERROR:", e)
        return {}

def read_full_system_memory():
    try:
        print("🔥 USING URL:", APPS_SCRIPT_URL)

        url = APPS_SCRIPT_URL + "?action=read_full_memory"

        resp = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=10
        )
        
        if not resp or resp.status_code != 200:
            return {}

        data = resp.json()

        return {
            "active_state": data.get("active_state", {}),
            "roadmap": data.get("roadmap_memory", []),
            "problems": data.get("problem_intelligence", []),
            "decisions": data.get("decision_log", [])
        }

    except Exception as e:
        print("❌ FULL MEMORY READ ERROR:", e)
        return {}

# =========================
# SESSION LOAD
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
        resp = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=10,
            allow_redirects=True
        )

        if not resp or resp.status_code != 200:
            return session_data

        text = resp.text

        if text.startswith(")]}'"):
            text = text[4:]

        data = json.loads(text)
        records = data.get("records", [])

        # 🔥 LIMIT MEMORY (ONLY LAST 10 RECORDS)
        records = records[-10:]

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

            # 🔥 FAILURE COUNT SIGNAL
            session_data["failure_count"] = session_data.get("failure_count", 0)

            if str(val).strip().lower() == "failed":
                session_data["failure_count"] += 1

        session_data["decisions"].reverse()
        session_data["roi_list"].reverse()
        session_data["risk_list"].reverse()
        session_data["confidence_list"].reverse()
        session_data["outcome_list"].reverse()

    except Exception as e:
        print("SESSION ERROR:", e)

    return session_data

import threading

def save_session_to_sheet_async(session_data):

    def task():
        try:
            payload = {
                "action": "save_session",
                "data": session_data
            }

            requests.post(APPS_SCRIPT_URL, json=payload, timeout=5)

        except Exception as e:
            print("❌ SESSION SAVE ERROR:", e)

    threading.Thread(target=task).start()

def update_decision_outcome(decision_id, outcome, lesson):

    payload = {
        "action": "update_decision",
        "data": {
            "Decision_ID": decision_id,
            "Outcome_Status": outcome,
            "Lesson_Learned": lesson
        }
    }

    try:
        requests.post(APPS_SCRIPT_URL, json=payload, timeout=10)
    except Exception as e:
        print("❌ Update decision error:", e)

# =========================
# ROUTES (UNCHANGED)
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
# 🔥 MAIN ENGINE (UPDATED)
# =========================
def save_session_to_sheet(session):
    try:
        payload = {
            "action": "save_session",
            "data": session
        }

        headers = {
            "Content-Type": "application/json"
        }

        resp = requests.post(
            APPS_SCRIPT_URL,
            json=payload,
            headers=headers,
            timeout=10,
            allow_redirects=True
        )

        print("🔥 SESSION SAVE:", resp.text)

    except Exception as e:
        print("❌ SESSION SAVE ERROR:", e)
        
@app.route("/atlas/action", methods=["POST"])
def atlas_action():
    print("🚀 REQUEST STARTED")

    try:
        input_data = request.get_json(force=True) or {}

        # =========================
        # 🔹 LOAD MEMORY
        # =========================
        system_memory = read_full_system_memory()
        active_raw = system_memory.get("active_state", [])

        def safe_json_parse(value):
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except:
                    return []
            return []

        parsed_state = {}

        if isinstance(active_raw, list) and len(active_raw) >= 2:
            headers = active_raw[0]
            values = None

            for row in reversed(active_raw[1:]):
                if any(str(cell).strip() != "" for cell in row):
                    values = row
                    break

            if values:
                for i in range(min(len(headers), len(values))):
                    parsed_state[headers[i]] = values[i]

        completed_steps = safe_json_parse(parsed_state.get("completed_steps", []))
        execution_plan = safe_json_parse(parsed_state.get("execution_plan", []))
        current_step = parsed_state.get("current_step")
        step_updates = safe_json_parse(parsed_state.get("step_updates", []))

        pending_steps = [s for s in execution_plan if s not in completed_steps]

        # =========================
        # 🧠 QUESTION MODE
        # =========================
        if input_data.get("question"):
            return jsonify({
                "status": "success",
                "mode": "question",
                "answer": {
                    "current_step": current_step,
                    "completed_steps": completed_steps,
                    "pending_steps": pending_steps,
                    "execution_plan": execution_plan
                }
            })

        # =========================
        # 🚀 EXECUTION MODE
        # =========================
        if input_data.get("execute"):

            loop_count = 0
            max_loops = 5   # safety limit

            final_response = None

            while loop_count < max_loops:
                loop_count += 1

                # =========================
                # FAILURE GUARD
                # =========================
                failure_count = sum(
                    1 for s in step_updates
                    if isinstance(s, dict) and s.get("status") == "failed"
                )

                if failure_count >= 2:
                    return jsonify({
                        "status": "warning",
                        "decision": "blocked"
                    })

                # =========================
                # COMPLETE → ENGINE
                # =========================
                if not pending_steps:
                    try:
                        session = load_session_from_sheet() or {}

                        session["active_state"] = {
                            "session_id": parsed_state.get("session_id"),
                            "current_step": current_step,
                            "completed_steps": completed_steps,
                            "step_updates": step_updates,
                            "execution_plan": execution_plan
                        }

                        result = generate_intelligent_action(session)

                        step_decision = result.get("step_decision", {})
                        execution_action = step_decision.get("execution_action")

                        # SAVE ENGINE DECISION
                        try:
                            save_decision_to_sheet({
                                "session_id": parsed_state.get("session_id"),
                                "decision": step_decision.get("decision"),
                                "decision_quality": step_decision.get("decision_quality"),
                                "score": step_decision.get("decision_score"),
                                "timestamp": time.time()
                            })
                        except:
                            pass

                        # 🧠 CONTROL FLOW
                        if execution_action == "execute":
                            execution_plan = result.get("execution_plan", [])
                            pending_steps = execution_plan
                            continue   # 🔁 LOOP CONTINUES

                        elif execution_action in ["hold", "continue"]:
                            return jsonify({
                                "status": "success",
                                "decision": execution_action,
                                "step_decision": step_decision
                            })

                        else:
                            return jsonify({
                                "status": "success",
                                "decision": "complete"
                            })

                    except Exception as e:
                        return jsonify({
                            "status": "success",
                            "decision": "complete"
                       })

                # =========================
                # STEP EXECUTION
                # =========================
                next_step = pending_steps[0]

                updated_completed = list(completed_steps)

                if next_step not in updated_completed:
                    updated_completed.append(next_step)

                updated_pending = [
                    s for s in execution_plan if s not in updated_completed
                ]

                # SAVE STATE
                try:
                    requests.post(
                        APPS_SCRIPT_URL,
                        json={
                                "action": "update_active_state",
                                "payload": {
                                "session_id": parsed_state.get("session_id"),
                                "current_step": next_step,
                                "completed_steps": updated_completed,
                                "execution_plan": execution_plan,
                                "step_updates": []
                            }
                        },
                            timeout=10
                    )
                except:
                    pass

                # SAVE EXECUTION
                try:
                    save_decision_to_sheet({
                        "session_id": parsed_state.get("session_id"),
                        "decision": next_step,
                        "type": "execution",
                        "timestamp": time.time()
                    })
                except:
                    pass

                # 🔁 UPDATE STATE FOR NEXT LOOP
                completed_steps = updated_completed
                pending_steps = updated_pending
                current_step = next_step

                if not pending_steps:
                     continue   # go to engine

                final_response = {
                    "status": "success",
                    "decision": "proceed",
                    "executed_step": next_step,
                    "next_step": pending_steps[0] if pending_steps else None
                }

            return jsonify(final_response or {
                "status": "success",
                "decision": "loop_finished"
            })

        return jsonify({"status": "invalid_request"})

    except Exception as e:
        print("❌ FATAL ERROR:", e)
        return jsonify({
            "status": "error",
            "message": str(e)
        })

# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)