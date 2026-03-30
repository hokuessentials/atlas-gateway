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
        # =========================
        # 🔹 SAFE INPUT PARSE
        # =========================
        try:
            input_data = request.get_json(force=True) or {}
        except Exception as e:
            print("❌ REQUEST PARSE ERROR:", e)
            return jsonify({"status": "error", "message": str(e)})

        # =========================
        # 🔹 LOAD SYSTEM MEMORY (FIXED)
        # =========================
        system_memory = read_full_system_memory()
        active_raw = system_memory.get("active_state", [])

        print("🔥 ACTIVE RAW:", active_raw)

        # 🔥 FIX: HANDLE BOTH LIST + DICT SAFELY
        active_state = {}

        if isinstance(active_raw, dict):
            active_state = active_raw

        elif isinstance(active_raw, list) and len(active_raw) >= 2:
            try:
                headers = active_raw[0]

                # 🔥 FIND LAST NON-EMPTY ROW
                values = None

                for row in reversed(active_raw[1:]):
                    if any(str(cell).strip() != "" for cell in row):
                        values = row
                        break

                if not values:
                    values = []

                if isinstance(headers, list) and isinstance(values, list):
                    for i in range(min(len(headers), len(values))):
                        active_state[headers[i]] = values[i]
            except Exception as e:
                print("❌ ACTIVE_STATE PARSE ERROR:", e)
                active_state = {}

        else:
            active_state = {}

        print("🔥 PARSED STATE:", active_state)

        # =========================
        # 🔥 FINAL PARSE (CORRECT)
        # =========================

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
            try:
                headers = active_raw[0]

                values = None
                for row in reversed(active_raw[1:]):
                    if any(str(cell).strip() != "" for cell in row):
                        values = row
                        break

                if values:
                    for i in range(min(len(headers), len(values))):
                        parsed_state[headers[i]] = values[i]
            except Exception as e:
                print("❌ PARSE ERROR:", e)

    # 🔥 APPLY JSON PARSE
    completed_steps = safe_json_parse(parsed_state.get("completed_steps", []))
    execution_plan = safe_json_parse(parsed_state.get("execution_plan", []))
    current_step = parsed_state.get("current_step")
    step_updates = safe_json_parse(parsed_state.get("step_updates", []))

    pending_steps = [
        step for step in execution_plan
        if step not in completed_steps
    ]

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
# 🚀 EXECUTION MODE (PHASE 2)
# =========================
if input_data.get("execute"):

    if not execution_plan:
        # =========================
        # 🚨 FAILURE + DUPLICATE PROTECTION
        # =========================

        # ❌ FAILURE COUNT
        failure_count = sum(
            1 for s in step_updates
            if isinstance(s, dict) and s.get("status") == "failed"
        )

        if failure_count >= 2:
            return jsonify({
                "status": "warning",
                "mode": "execution",
                "decision": "blocked",
                "reason": "Too many failures"
            })

        # ❌ DUPLICATE EXECUTION BLOCK
        if current_step and current_step in completed_steps:

            # =========================
            # 🧠 TRY ENGINE BEFORE SKIP
            # =========================
            try:
                session = load_session_from_sheet() or {}

                session["active_state"] = {
                    "session_id": parsed_state.get("session_id"),
                    "current_step": current_step,
                    "completed_steps": completed_steps,
                    "step_updates": safe_json_parse(parsed_state.get("step_updates", [])),
                    "execution_plan": execution_plan
                }

                session.setdefault("decisions", [])
                session.setdefault("roi_list", [])
                session.setdefault("risk_list", [])
                session.setdefault("confidence_list", [])
                session.setdefault("outcome_list", [])

                start_time = time.time()

                result = None

                try:
                    result = generate_intelligent_action(session)
                except Exception as e:
                    print("❌ ENGINE ERROR:", e)

                    # ⏱️ TIME GUARD (CRITICAL)
                    if time.time() - start_time > 5:
                        print("⚠️ ENGINE TIMEOUT — SKIPPING")
                        result = None

                return jsonify({
                    "status": "success",
                    "mode": "execution_complete",
                    "decision": "engine_triggered",
                    "next_plan": result.get("execution_plan", []) if result else [],
                    "message": "Step already done, engine generated next plan"
                })

            except Exception as e:
                print("❌ ENGINE ERROR:", e)
                return jsonify({
                    "status": "error",
                    "message": str(e)
                })

    # =========================
    # 🧠 TRIGGER INTELLIGENCE ENGINE or SMART STEP SELECTION
    # =========================
    if not pending_steps:
        session = load_session_from_sheet() or {}

        # =========================
        # 🧠 PREPARE ENGINE INPUT
        # =========================
        session["active_state"] = {
            "session_id": parsed_state.get("session_id"),
            "current_step": current_step,
            "completed_steps": completed_steps,
            "step_updates": step_updates,
            "execution_plan": execution_plan
        }

        # Ensure required fields exist
        session.setdefault("decisions", [])
        session.setdefault("roi_list", [])
        session.setdefault("risk_list", [])
        session.setdefault("confidence_list", [])
        session.setdefault("outcome_list", [])

            # =========================
            # 🚀 CALL ENGINE
            # =========================
            result = generate_intelligent_action(session)
    
        else:
            # =========================
            # 🧠 SMART STEP SELECTION
            # =========================
            session = load_session_from_sheet() or {}
            session.setdefault("decisions", [])
            session.setdefault("roi_list", [])
            session.setdefault("risk_list", [])
            session.setdefault("confidence_list", [])
            session.setdefault("outcome_list", [])

            next_step = pending_steps[0]

            for step in pending_steps:
                failed = any(
                    isinstance(u, dict) and
                    u.get("step") == step and
                    u.get("status") == "failed"
                    for u in step_updates
                )
                if not failed:
                    next_step = step
                    break

            # =========================
            # 🔥 UPDATE STATE
            # =========================
            updated_completed = list(completed_steps)
            if next_step not in updated_completed:
                updated_completed.append(next_step)

            updated_current = next_step

            # next pending after update
            updated_pending = [
                step for step in execution_plan
                if step not in updated_completed
            ]

            # =========================
            # 🔥 SEND UPDATE TO SHEET
            # =========================
            try:
                requests.post(
                    APPS_SCRIPT_URL,
                    json={
                        "action": "update_active_state",
                        "payload": {
                            "session_id": parsed_state.get("session_id"),
                            "current_step": updated_current,
                            "completed_steps": updated_completed,
                            "execution_plan": execution_plan,
                            "step_updates": []
                        }
                    },
                    timeout=10
                )
            except Exception as e:
                print("⚠️ Update failed:", e)

            # =========================
            # 🔥 RESPONSE
            # =========================
            return jsonify({
                "status": "success",
                "mode": "execution",
                "decision": "proceed",
                "executed_step": next_step,
                "next_step": updated_pending[0] if updated_pending else None,
                "completed_steps": updated_completed
            })

    # =========================
    # 🔥 GLOBAL SAFE VARIABLES (CRITICAL FIX)
    # =========================
    action = result.get("action", "")
    execution_plan = result.get("execution_plan", [])

    print("✅ INTELLIGENCE RESULT:", result.get("action"))

    # =========================
    # 🔥 SAFETY DEFAULTS
    # =========================
    result.setdefault("execution_state", {})
    result.setdefault("step_decision", {})

    execution_state = result["execution_state"]

    # =========================
    # ⚡ STEP OVERRIDE (SAFE MODE)
    # =========================
    force_mode = execution_state.get("force_mode", False)

    if not force_mode:
        if action.startswith("Switch to higher value"):
            execution_plan = result.get("execution_plan", [])
            if execution_plan:
                new_step = execution_plan[-1]
                execution_state["current_step"] = new_step
                print("⚡ STEP OVERRIDE:", new_step)

    # =========================
    # 🧠 STEP VALIDATION (SAFE MODE)
    # =========================
    force_mode = execution_state.get("force_mode", False)

    if not force_mode:
        current_step = execution_state.get("current_step")
        completed_steps = execution_state.get("completed_steps", [])
        execution_plan = result.get("execution_plan", [])

        if current_step in execution_plan:
            idx = execution_plan.index(current_step)
            missing = [s for s in execution_plan[:idx] if s not in completed_steps]

            if missing:
                corrected = missing[0]
                execution_state["current_step"] = corrected
                print("🛑 STEP BLOCKED →", corrected)

    # =========================
    # 🔁 ACTION REALIGN
    # =========================
    final_step = execution_state.get("current_step")

    if final_step and action.startswith("Switch"):
        result["action"] = f"Continue: {final_step}"
        print("🔁 ACTION REALIGNED:", result["action"])

    # =========================
    # 🧠 PHASE 2: CONTROLLED NON-LINEAR EXECUTION (SAFE FINAL)
    # =========================
    execution_plan = result.get("execution_plan", [])
    execution_state = result.get("execution_state", {})

    current_step = execution_state.get("current_step")
    completed_steps = execution_state.get("completed_steps", [])
    step_updates = execution_state.get("step_updates", [])

    # 1. Get candidates (exclude current step)
    candidates = [
        step for step in get_candidate_steps(execution_plan, completed_steps)
        if step != current_step
    ]
    # FINAL SAFETY — NEVER ALLOW COMPLETED STEPS
    candidates = [
        step for step in candidates
        if step not in completed_steps
    ]

    # 2. Filter allowed (dependency-safe)
    allowed_candidates = filter_allowed_candidates(
        candidates,
        step_updates,
        completed_steps
    )
    selected_step = None

    # 3. Safety check
    if allowed_candidates:
        selected_step = select_better_step(
            current_step,
            allowed_candidates,
            step_updates,
            completed_steps,
            session
        )

    # 4. Apply ONLY if changed (SAFE)
    if selected_step and selected_step != current_step:
        # ❌ NEVER ALLOW COMPLETED STEP
        if selected_step in completed_steps:
            print("🚫 BLOCKED: Selected step already completed →", selected_step)
        else:
            print("⚡ CONTROLLED SWITCH:", current_step, "→", selected_step)

            execution_state["current_step"] = selected_step

            # ✅ SYNC pending steps
            execution_state["pending_steps"] = [
                s for s in execution_plan
                if s not in execution_state.get("completed_steps", [])
                and s != selected_step
            ]

            # ✅ SYNC action
            result["action"] = f"Continue: {selected_step}"

    # =========================
    # 🧠 DEPENDENCY CHECK (PHASE 1)
    # =========================
    execution_state = result["execution_state"]
    current_step = execution_state.get("current_step")
    step_updates = execution_state.get("step_updates", [])

    allowed, blocking_step = is_step_allowed(
        current_step,
        step_updates,
        execution_state.get("completed_steps", [])
    )

    if not allowed:
        print("🛑 BLOCKED BY DEPENDENCY:", blocking_step)

        result["action"] = f"Complete prerequisite: {blocking_step}"

        result.setdefault("step_decision", {})
        result["step_decision"]["execution_action"] = "blocked"
        result["step_decision"]["reason"] = f"{current_step} depends on {blocking_step}"

        return jsonify({
            "status": "success",
            "session_id": session.get("session_id"),
            "result": result
        })

    # =========================
    # 📝 STEP LOGGING (FIXED)
    # =========================
    step_updates = execution_state.get("step_updates", [])

    status = "success" if result.get("step_decision", {}).get("execution_action") == "execute" else "started"

    step_updates.append({
        "step": final_step,
        "status": status,
        "timestamp": time.time()
    })

    execution_state["step_updates"] = step_updates

    # =========================
    # 📊 PENDING STEPS (FIXED)
    # =========================
    pending_steps = [
        s for s in execution_plan
        if s not in completed_steps and s != final_step
    ]

    execution_state["pending_steps"] = pending_steps

    # =========================
    # ✅ STEP PROGRESSION
    # =========================
    if result.get("step_decision", {}).get("execution_action") == "execute":

        if final_step and final_step not in completed_steps:
            completed_steps.append(final_step)
            print("✅ STEP COMPLETED:", final_step)

            if final_step in execution_plan:
                idx = execution_plan.index(final_step)

                # FIND NEXT VALID STEP (NOT COMPLETED)
                next_step = None

                for s in execution_plan:
                    if s not in completed_steps:
                        next_step = s
                        break

                if next_step:
                    execution_state["current_step"] = next_step
                    execution_state["completed_steps"] = completed_steps

                    result["action"] = f"Continue: {next_step}"
                    print("➡️ NEXT STEP:", next_step)

    # =========================
    # 🔥 SAVE DECISION (FIXED MODULE)
    # =========================
    if result.get("action") and result["action"] != "Start by logging a decision":

        decision_payload = {
            "Decision_ID": f"D-{int(time.time())}",
            "Session_ID": session.get("session_id"),
            "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "Title": result.get("action"),
            "Description": result.get("reason"),
            "Module": active_state.get("focus_module", "general"),
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

        update_decision_outcome(
            decision_id=decision_payload["Decision_ID"],
            outcome="success",
            lesson="Initial execution completed"
        )

    # =========================
    # 💾 SAVE STATE
    # =========================
    state = {
        "session_id": session.get("session_id"),
        "current_step": execution_state.get("current_step"),
        "completed_steps": execution_state.get("completed_steps", []),
        "step_updates": execution_state.get("step_updates", []),
        "execution_plan": result.get("execution_plan", [])
    }

    save_state_to_sheet(state)

    # =========================
    # 💾 SAVE SESSION
    # =========================
    save_session_to_sheet(session)

    # =========================
    # ✅ RESPONSE
    # =========================
    return jsonify({
        "status": "success",
        "session_id": session.get("session_id"),
        "result": result
    })
    
    except Exception as e:
        print("❌ INTELLIGENCE ERROR:", e)
        print("❌ FATAL ERROR:", e)
        return jsonify({
            "status": "error",
            "message": str(e)
        })

# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)