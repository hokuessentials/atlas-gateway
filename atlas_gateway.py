from flask import Flask, request, jsonify
import requests
import json
import time
from intelligence_engine import generate_intelligent_action
import state_engine
from session_engine import evaluate_session_health

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
        input_data = request.get_json(force=True)

        # =========================
        # 🔵 LOAD STATE (SOURCE OF TRUTH)
        # =========================
        saved_state = load_state_from_sheet()

        force_input = input_data.get("force_input", False)

        if force_input:
            active_state = input_data.get("active_state", {})
        elif saved_state and isinstance(saved_state, dict):
            active_state = saved_state
        else:
            active_state = input_data.get("active_state", {})

        print("✅ STATE LOADED")

        # =========================
        # 🔵 LOAD SESSION (ONLY ONCE)
        # =========================
        session = load_session_from_sheet() or {}
        print("✅ SESSION LOADED:", session.get("session_id"))

        # =========================
        # 🔥 SESSION SOURCE = STATE ONLY
        # =========================
        memory_session_id = active_state.get("session_id")

        if memory_session_id:
            final_session_id = memory_session_id
        else:
            final_session_id = f"S-{int(time.time())}"

        # FORCE SYNC
        session["session_id"] = final_session_id
        active_state["session_id"] = final_session_id
        session["active_state"] = active_state

        # =========================
        # 🔥 SESSION HEALTH CHECK
        # =========================
        try:
            session_check = evaluate_session_health(session, active_state)
        except Exception as e:
            print("❌ SESSION HEALTH ERROR:", e)
            session_check = {"session_decision": "continue"}

        if session_check.get("session_decision") == "reset_session":
            new_session_id = f"S-{int(time.time())}"
            session["session_id"] = new_session_id
            active_state = {"session_id": new_session_id}
            session["active_state"] = active_state

        # =========================
        # 🧠 INTELLIGENCE ENGINE
        # =========================
        try:
            result = generate_intelligent_action(session)
            print("✅ INTELLIGENCE RESULT:", result.get("action"))
        except Exception as e:
            print("❌ INTELLIGENCE ERROR:", e)
            return jsonify({
                "status": "error",
                "message": str(e)
            })

        # =========================
        # 🔥 FORCE STEP ALIGNMENT (CRITICAL)
        # =========================

        action = result.get("action", "")

        if action.startswith("Switch to higher value"):
            execution_plan = result.get("execution_plan", [])

            if execution_plan:
                new_step = execution_plan[-1]  # highest value step
                result.setdefault("execution_state", {})
                result["execution_state"]["current_step"] = new_step

                print("⚡ STEP OVERRIDE:", new_step)


        # =========================
        # 🧠 EXECUTION FEASIBILITY GUARD (ADD HERE)
        # =========================

        execution_state = result.get("execution_state", {})
        current_step = execution_state.get("current_step")
        completed_steps = execution_state.get("completed_steps", [])

        execution_plan = result.get("execution_plan", [])

        if current_step in execution_plan:
            step_index = execution_plan.index(current_step)

            if step_index > 0:
                required_previous_steps = execution_plan[:step_index]

                missing_steps = [s for s in required_previous_steps if s not in completed_steps]

                if missing_steps:
                    corrected_step = missing_steps[0]

                    result["execution_state"]["current_step"] = corrected_step

                    print("🛑 STEP BLOCKED → reverting to:", corrected_step)

        # =========================
        # 🧠 DECISION REALIGNMENT
        # =========================

        final_step = result.get("execution_state", {}).get("current_step")

        if final_step and result.get("action", "").startswith("Switch"):
            result["action"] = f"Continue: {final_step}"
            print("🔁 ACTION REALIGNED →", result["action"]) 

        # =========================
        # 🚀 AUTO STEP PROGRESSION
        # =========================

        execution_state = result.get("execution_state", {})
        current_step = execution_state.get("current_step")
        completed_steps = execution_state.get("completed_steps", [])
        execution_plan = result.get("execution_plan", [])
        
        # =========================
        # 📝 STEP UPDATE LOGGING
        # =========================

        step_updates = execution_state.get("step_updates", [])

        step_updates.append({
            "step": current_step,
            "status": "started",
            "timestamp": time.time()
        })

        result["execution_state"]["step_updates"] = step_updates

        # mark current step as completed if execution is happening
        if result.get("step_decision", {}).get("execution_action") == "execute":

            if current_step and current_step not in completed_steps:
                completed_steps.append(current_step)

                print("✅ STEP COMPLETED:", current_step)

                # move to next step
                if current_step in execution_plan:
                    idx = execution_plan.index(current_step)

                    if idx + 1 < len(execution_plan):
                        next_step = execution_plan[idx + 1]

                        result["execution_state"]["current_step"] = next_step
                        result["execution_state"]["completed_steps"] = completed_steps

                        result["action"] = f"Continue: {next_step}"

                        print("➡️ MOVING TO NEXT STEP:", next_step) 

        # =========================
        # 🧠 FAILURE & LOOP CONTROL
        # =========================

        execution_state = result.get("execution_state", {})
        current_step = execution_state.get("current_step")
        step_updates = execution_state.get("step_updates", [])

        # count failures for current step
        failure_count = sum(
            1 for update in step_updates
            if update.get("step") == current_step and update.get("status") == "failed"
        )

        # count repeats
        repeat_count = sum(
            1 for step in execution_state.get("completed_steps", [])
            if step == current_step
        )

        # 🚨 FAILURE LOGIC
        if failure_count >= 2:
            result["action"] = f"⚠️ Escalate: {current_step} is failing repeatedly"
            result.setdefault("step_decision", {})
            result["step_decision"]["decision"] = "escalate"
            result["step_decision"]["execution_action"] = "hold"

            print("🚨 FAILURE ESCALATION TRIGGERED")

        # 🔁 LOOP LOGIC
        elif repeat_count >= 2:
            result["action"] = f"🔁 Loop detected at: {current_step}, forcing change"
            result["step_decision"]["decision"] = "adjust"
            result["step_decision"]["execution_action"] = "hold"

            print("🔁 LOOP DETECTED")                         

        # =========================
        # 🔥 SAVE DECISION
        # =========================
        if result.get("action") and result["action"] != "Start by logging a decision":

            decision_payload = {
                "Decision_ID": f"D-{int(time.time())}",
                "Session_ID": session.get("session_id"),
                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "Title": result.get("action"),
                "Description": result.get("reason"),
                "Module": session.get("focus_module", "general"),
                "Expected_ROI": result.get("expected_roi", 10),
                "Risk_Score": result.get("risk_score", 0.3),
                "Confidence_Level": result.get("confidence_level", 0.6),
                "Reversible_Flag": True,
                "Decision_Owner": "Atlas",
                "Tags": "auto",
                "Decision_Type": "execution",
                "Outcome_Status": "pending",
                "Lesson_Learned": ""
            }

            save_decision_to_sheet(decision_payload)

            # ✅ OPTIONAL: immediate outcome update (your current system)
            update_decision_outcome(
                decision_id=decision_payload["Decision_ID"],
                outcome="success",
                lesson="Initial execution completed"
            )

        # =========================
        # 🔥 SAVE STATE (SYNC BACK)
        # =========================
        if result.get("execution_state"):
            state = {
                "session_id": session.get("session_id"),
                "current_step": result.get("execution_state", {}).get("current_step"),
                "completed_steps": result.get("execution_state", {}).get("completed_steps", []),
                "step_updates": result.get("execution_state", {}).get("step_updates", []),
                "execution_plan": result.get("execution_plan", [])
            }

            save_state_to_sheet(state)

        # =========================
        # 🔥 SAVE SESSION
        # =========================
        save_session_to_sheet(session)

        # =========================
        # ✅ FINAL RESPONSE
        # =========================
        return jsonify({
            "status": "success",
            "session_id": session.get("session_id"),
            "result": result
        })

    except Exception as e:
        print("❌ FATAL ERROR:", e)
        return jsonify({
            "status": "error",
            "message": str(e)
        })  

# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)