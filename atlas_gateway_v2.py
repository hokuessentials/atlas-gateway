from flask import Flask, request, jsonify
import requests
import json
import time
import os
import state_engine
from step_decision_engine import decide_step_action
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
        requests.post(
            APPS_SCRIPT_URL,
            json={
                "action": "update_active_state",
                "payload": active_state
            },
            headers={"Content-Type": "application/json"},
            timeout=3
        )
    except Exception as e:
        print("❌ STATE SAVE ERROR:", e)

def log_execution_to_sheet(data):
    try:
        requests.post(
            APPS_SCRIPT_URL,
            json={
                "action": "log_execution",
                "data": data
            },
            headers={"Content-Type": "application/json"},
            timeout=3
        )
    except Exception as e:
        print("❌ LOG ERROR:", e)

def update_tracker(data):
    try:
        requests.post(
            APPS_SCRIPT_URL,
            json={
                "action": "update_tracker",
                "data": data
            },
            headers={"Content-Type": "application/json"},
            timeout=3
        )
    except Exception as e:
        print("❌ TRACKER ERROR:", e)

def save_decision_to_sheet(decision_data):
    try:
        requests.post(
            APPS_SCRIPT_URL,
            json={
                "action": "log_decision",
                "data": decision_data
            },
            headers={"Content-Type": "application/json"},
            timeout=3
        )
    except Exception as e:
        print("❌ DECISION SAVE ERROR:", e)       

def load_state_from_sheet():
    try:
        url = APPS_SCRIPT_URL + "?action=read_active_state"
        resp = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=3,
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

        # 🔥 FIX: convert sheet array → dict
        if isinstance(state, list):
            try:
                headers = state[0]
                values = state[-1]
                state = dict(zip(headers, values))
            except:
                state = {}

        # 🔥 safety
        if not isinstance(state, dict):
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
            timeout=3,
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
            timeout=3,
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
def update_decision_outcome(decision_id, outcome, lesson):

    payload = {
        "action": "update_decision",
        "data": {
            "Decision_ID": decision_id,
            "Outcome_Status": outcome,
            "Lesson_Learned": lesson
        }
    }
    # requests.post(...)
    try:
        requests.post(
                APPS_SCRIPT_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=3,
                allow_redirects=True
            )
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
        requests.post(
            APPS_SCRIPT_URL,
            json={
                "action": "save_session",
                "data": session
            },
            headers={"Content-Type": "application/json"},
            timeout=3
        )
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
        system_memory = read_full_system_memory() or {}
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

        parsed_state = load_state_from_sheet() or {}

        if isinstance(parsed_state, list):
            parsed_state = {}

        session_id = parsed_state.get("session_id") or input_data.get("session_id")

        if not session_id:
            session_id = "S-" + str(int(time.time()))
            parsed_state["session_id"] = session_id

            # requests.post(...)
            save_state_to_sheet({
                "session_id": session_id
            })
            

        completed_steps = safe_json_parse(parsed_state.get("completed_steps", []))
        completed_steps = list(dict.fromkeys([
            s.strip() for s in completed_steps if s and str(s).strip()
        ]))
        
        # 🔥 CLEAN BAD DATA FROM SHEET
        completed_steps = [
            s for s in completed_steps
            if s and str(s).strip() != ""
        ]

        execution_plan = safe_json_parse(parsed_state.get("execution_plan", []))
        # 🔥 AUTO-INITIALIZE IF EMPTY
        if not execution_plan and not completed_steps:
            execution_plan = [
                "Evaluate sample quality against standards.",
                "Check supplier pricing",
                "Negotiate price",
                "Check sample quality",
                "Finalize supplier"
            ]

        # ✅ REMOVE EMPTY STEPS (FIX 4)
        execution_plan = [
            s for s in execution_plan
            if s and str(s).strip() != ""
        ]

        # ✅ ALWAYS DEFINE FIRST
        current_step = (parsed_state.get("current_step") or "").strip()

        # ✅ THEN FIX IF EMPTY
        if not current_step:
            if completed_steps:
                remaining = [s for s in execution_plan if s not in completed_steps]
                current_step = remaining[0] if remaining else execution_plan[0]
            elif execution_plan:
                current_step = execution_plan[0]

        step_updates = safe_json_parse(parsed_state.get("step_updates", []))

        pending_steps = [
            s for s in execution_plan
            if s not in completed_steps and s != current_step
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
        # 🚀 EXECUTION MODE
        # =========================
        if input_data.get("execute"):

            loop_count = 0
            max_loops = 1  # safety limit

            start_time = time.time() 
            MAX_RUNTIME = 15 # seconds
            final_response = None

            while loop_count < max_loops:
                loop_count += 1

                # 🔥 AUTO SESSION UPDATE (CRITICAL FIX)
                try:
                    save_session_to_sheet({
                        "Session_ID": session_id,
                        "Start_Time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "Session_Type": "execution",
                        "Active_Module": "Execution Engine",
                        "Active_Phase": "Phase 3.5",
                        "Tasks_Worked": len(completed_steps),
                        "Issues_Found": 0,
                        "Status": "ACTIVE",
                        "Notes": "Auto session update"
                    })
                except:
                    pass

                # =========================
                # 🔥 NOW DECIDE NEXT STEP
                # =========================

                pending_steps = [
                    s for s in execution_plan
                    if s not in completed_steps and s != current_step
                ]   
                
                # 2. FIND NEXT STEP (ONLY NORMALIZED VERSION)
                # 🔥 NORMALIZE STEPS (CRITICAL FIX)
                normalized_completed = [s.strip().lower() for s in completed_steps]

                # =========================
                # 🧠 PHASE 4 — INTELLIGENT STEP SELECTION
                # =========================

                normalized_completed = [
                    s.strip().lower() for s in completed_steps
                ]

                normalized_plan = [
                    s.strip() for s in execution_plan if s and str(s).strip()
                ]

                # =========================
                # 🧠 FILTER CANDIDATES
                # =========================

                candidates = [
                    s for s in normalized_plan
                    if s.strip().lower() not in normalized_completed
                ]

                # 🚫 REMOVE CURRENT STEP
                candidates = [
                    s for s in candidates
                    if s.strip().lower() != current_step.strip().lower()
                ]

                # 🚫 REMOVE LAST EXECUTED STEP (CRITICAL FIX)
                if step_updates:
                    last_step = step_updates[-1].get("step", "").strip().lower()

                    candidates = [
                        s for s in candidates
                        if s.strip().lower() != last_step
                    ]

                # =========================
                # 🧠 SELECT BEST STEP
                # =========================

                if candidates:

                    selected_step = select_better_step(
                        current_step,
                        candidates,
                        step_updates,
                        completed_steps
                    )
                    previous_step = current_step
                    next_step_candidate = selected_step

                    memory = build_step_memory(step_updates)

                    print("🧠 MEMORY:", memory)
                    print("🧠 SCORES:")

                    for c in candidates:
                        print(c, "→", score_step(c, completed_steps, step_updates))

                    print("✅ SELECTED:", selected_step)
                    print("🧠 FINAL SELECTED STEP:", selected_step)

                # =========================
                # 🧠 DECISION BEFORE EXECUTION
                # =========================

                session_data = load_session_from_sheet()

                session_data["active_state"] = {
                    "current_step": current_step,
                    "completed_steps": completed_steps,
                    "step_updates": step_updates,
                    "execution_plan": execution_plan
                }

                result = generate_intelligent_action(session_data)

                step_decision = result.get("step_decision", {})
                decision = step_decision.get("decision")
                execution_action = step_decision.get("execution_action")
                decision_score = step_decision.get("decision_score", 0)
                decision_quality = step_decision.get("decision_quality", "execution")

                if execution_action == "hold":
                    return jsonify({
                        "status": "hold",
                        "decision": decision,
                        "Decision_Quality": decision_quality,
                        "Score": decision_score,
                        "reason": step_decision.get("reason"),
                        "metrics": step_decision.get("metrics"),
                        "debug": {
                            "current_step": current_step,
                            "completed_steps": completed_steps,
                            "pending_steps": pending_steps,
                            "recent_updates": step_updates[-5:]
                        }
                    })
                
                # =========================
                # ⚡ EXECUTE AFTER DECISION
                # =========================

                if current_step and current_step not in completed_steps:

                    print("⚡ EXECUTING STEP:", current_step)

                    step_updates.append({
                        "step": previous_step,
                        "status": "success",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })

                    completed_steps.append(previous_step.strip())

                    save_state_to_sheet({
                        "session_id": session_id,
                        "current_step": current_step,
                        "completed_steps": json.dumps(completed_steps),
                        "execution_plan": json.dumps(execution_plan),
                        "step_updates": json.dumps(step_updates)
                    })
                    current_step = next_step_candidate
                    pending_steps = [
                        s for s in execution_plan
                        if s not in completed_steps and s != current_step
                    ]

                    # 4. NOW BUILD RESPONSE
                    final_response = {
                        "executed_step": previous_step,
                        "next_step": current_step,
                        "decision": decision,
                        "Decision_Quality": decision_quality,
                        "Score": decision_score,
                        "reason": step_decision.get("reason"),
                        "metrics": step_decision.get("metrics")
                    }    
                
                if time.time() - start_time > MAX_RUNTIME:
                
                # =========================
                # FAILURE GUARD
                # =========================
                    failure_count = sum(
                        1 for s in step_updates
                        if isinstance(s, dict) and s.get("status") == "failed"
                    )

                if failure_count >= 5:
                    return jsonify({
                        "status": "warning",
                        "decision": "blocked"
                    })
                
                pending_steps = [
                    s for s in execution_plan
                    if s not in completed_steps and s != current_step
                ]
                # =========================
                # COMPLETE → ENGINE
                # =========================
                if not pending_steps:
                    
                    current_step = None
                    # FINAL COMPLETION  
                    step_decision = decide_step_action("finalize", step_updates)
                    decision_score = step_decision.get("decision_score", 1)

                    if time.time() - start_time > 20:
                        return jsonify({
                            "status": "timeout_safe_exit",
                            "decision": "partial",
                            "debug": {
                                "current_step": None,
                                "completed_steps": completed_steps,
                                "pending_steps": pending_steps
                            }
                        })

                # ✅ FINAL STEP — ONLY INSIDE THIS BLOCK
                decision_quality = "final_step"

                try:
                    save_session_to_sheet({
                        "Session_ID": session_id,
                        "End_Time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "Status": "CLOSED",
                        "Notes": "Auto closed"
                    })
                except:
                    pass

                return jsonify({
                    "status": "success",
                    "decision": "complete",
                    "Decision_Quality": decision_quality,
                    "Score": decision_score,  # 🔥 use dynamic score
                    "reason": step_decision.get("reason"),
                    "metrics": step_decision.get("metrics"),
                    "debug": {
                        "current_step": current_step,
                        "completed_steps": completed_steps,
                        "pending_steps": [],
                        "failed_steps": [],
                        "recent_updates": step_updates[-5:]
                    }
                })

            # =========================
            # 🔁 RETRY + SWITCH LOGIC
            # =========================

            failure_count_map = {}

            for update in step_updates:
                if isinstance(update, dict):
                    step = update.get("step")
                    status = update.get("status")

                    if status == "failed":
                        failure_count_map[step] = failure_count_map.get(step, 0) + 1

            MAX_RETRY = 2

            failed_steps = [
                step for step, count in failure_count_map.items()
                if count >= MAX_RETRY
            ]

            pending_steps = [
                s for s in execution_plan
                if s not in completed_steps and s != current_step
            ]

            available_steps = [
                s for s in pending_steps
                if s not in failed_steps
            ]

            # 🚨 fallback (avoid dead loop)

            if not available_steps:

                # check if reset already happened
                reset_done = any(
                    isinstance(u, dict) and u.get("status") == "reset"
                    for u in step_updates
                )

                if not reset_done:
                    step_updates.append({
                        "step": "system",
                        "status": "reset",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })

                    # 🔥 SAVE STATE BEFORE RETURN
                    return jsonify({
                        "status": "retrying",
                        "reason": "All steps failed once, retrying",
                        "action": "retry_all_steps",
                            
                        "debug": {
                            "current_step": current_step,
                            "completed_steps": completed_steps,
                            "pending_steps": pending_steps,
                            "failed_steps": failed_steps,
                            "recent_updates": step_updates[-5:]
                        }
                    })
                else:
                    return jsonify({
                        "status": "hold",
                        "reason": "All steps failed after retry",
                        "action": "manual_review_required",
                        "debug": {
                            "current_step": current_step,
                            "completed_steps": completed_steps,
                            "pending_steps": pending_steps,
                            "failed_steps": failed_steps,
                            "recent_updates": step_updates[-5:]
                        }
                    })

            # 🔥 ALWAYS LOG DECISION (CRITICAL FIX)
            try:
                save_decision_to_sheet({
                    "Decision_ID": "D-" + str(int(time.time() * 1000)),
                    "Session_ID": session_id,
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Title": previous_step,
                    "Description": "Step executed",
                    "Module": "Execution Engine",
                    "Expected_ROI": 5,
                    "Risk_Score": 0.5,
                    "Confidence_Level": 0.5,
                    "Decision_Quality": "execution",
                    "Reversible_Flag": True,
                    "Decision_Owner": "Atlas",
                    "Tags": "execution",
                    "Decision_Type": "execution",
                    "Outcome_Status": "success",
                    "Lesson_Learned": "Step executed"
                })
            except:
                pass

            # 🔥 UPDATE MASTER TRACKER (CORRECT)
            try:
                update_tracker({
                    "module": "Execution Engine",
                    "phase": "Phase 3.5",
                    "task": "Control Layer Build",
                    "status": "complete" if not pending_steps else "active",
                    "current_step": previous_step,
                    "next_step": current_step,
                    "owner": "Atlas",
                    "notes": "Live execution update"
                })
            except:
                pass

            # 🔥 AUTO LOG EXECUTION
            try:
                log_execution_to_sheet({
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "executed_step": previous_step,
                    "next_step": current_step,
                    "current_step": current_step,
                    "completed_steps": ";".join(completed_steps),
                    "pending_steps": ";".join(pending_steps),
                    "status": final_response.get("status", "success"),
                    "decision": final_response.get("decision", "proceed")
                })
            except:
                pass 

            save_state_to_sheet({
                "session_id": session_id,
                "current_step": current_step,
                "completed_steps": json.dumps(completed_steps),
                "execution_plan": json.dumps(execution_plan),
                "step_updates": json.dumps(step_updates)
            })

            return jsonify({
                "status": "success",
                "decision": decision,
                "Decision_Quality": decision_quality,
                "Score": decision_score,
                "reason": step_decision.get("reason"),
                "metrics": step_decision.get("metrics"),
                "executed_step": previous_step,
                "next_step": current_step,
                "debug": {
                    "current_step": current_step,
                    "completed_steps": completed_steps,
                    "pending_steps": pending_steps,
                    "recent_updates": step_updates[-5:]
                }
            })

        return jsonify({"status": "invalid_request"})

    except Exception as e:
        print("❌ FATAL ERROR:", e)
        return jsonify({
            "status": "error",
            "message": str(e)
        })
def suggest_next_step(execution_plan, completed_steps):

    remaining = [s for s in execution_plan if s not in completed_steps]

    if not remaining:
        return None

    # 🔥 FOR NOW — SAME AS ORDER (SAFE)
    return remaining[0]

# =========================
# 🧠 PHASE 4.2 — STEP MEMORY ENGINE
# =========================

def build_step_memory(step_updates):

    memory = {}

    for u in step_updates:
        if not isinstance(u, dict):
            continue

        step = u.get("step", "").strip()
        status = u.get("status", "").strip().lower()

        if not step:
            continue

        if step not in memory:
            memory[step] = {
                "success": 0,
                "fail": 0,
                "total": 0
            }

        memory[step]["total"] += 1

        if status == "success":
            memory[step]["success"] += 1
        elif status == "failed":
            memory[step]["fail"] += 1

    # calculate rates
    for step in memory:
        total = memory[step]["total"]

        if total > 0:
            memory[step]["success_rate"] = memory[step]["success"] / total
            memory[step]["failure_rate"] = memory[step]["fail"] / total
        else:
            memory[step]["success_rate"] = 0
            memory[step]["failure_rate"] = 0

    return memory

def score_step(step, completed_steps, step_updates):

    step_lower = step.strip().lower()
    score = 0

    # =========================
    # 🧠 MEMORY (PHASE 4.2)
    # =========================

    memory = build_step_memory(step_updates)
    step_mem = memory.get(step, {})

    success_rate = step_mem.get("success_rate", 0)
    failure_rate = step_mem.get("failure_rate", 0)

    # =========================
    # 💰 ROI ENGINE (NEW)
    # =========================

    if "finalize" in step_lower:
        roi = 10
    elif "negotiate" in step_lower:
        roi = 8
    elif "check sample" in step_lower:
        roi = 7
    elif "check supplier" in step_lower:
        roi = 6
    elif "evaluate" in step_lower:
        roi = 5
    else:
        roi = 4

    # =========================
    # ⚠️ RISK ENGINE (NEW)
    # =========================

    if "negotiate" in step_lower:
        risk = 0.6
    elif "finalize" in step_lower:
        risk = 0.4
    else:
        risk = 0.2

    # =========================
    # 🎯 CONFIDENCE ENGINE (NEW)
    # =========================

    confidence = success_rate if success_rate > 0 else 0.5

    # =========================
    # 🔥 SCORE FORMULA (CORE BRAIN)
    # =========================

    score += (roi * 1.2)
    score += (confidence * 5)
    score -= (risk * 6)
    score += (success_rate * 5)
    score -= (failure_rate * 7)

    # =========================
    # 🔁 RETRY PENALTY
    # =========================

    retry_count = sum(
        1 for u in step_updates
        if isinstance(u, dict)
        and u.get("step", "").strip().lower() == step_lower
    )

    score -= retry_count * 3
    
        # =========================
    # 🧠 PHASE 4.3 — ADAPTIVE LEARNING
    # =========================

    # 🔴 STRONG FAILURE PENALTY
    if failure_rate > 0.5:
        score -= 10

    # 🔴 REPEATED FAILURE BLOCK
    if retry_count >= 2:
        score -= 15

    # 🟢 SUCCESS BOOST
    if success_rate > 0.7:
        score += 8

    # 🟢 CONSISTENCY BOOST
    if success_rate > 0 and failure_rate == 0:
        score += 5
        
    # =========================
    # 🚫 COMPLETION SAFETY
    # =========================

    if step_lower in [s.strip().lower() for s in completed_steps]:
        score -= 100

    # =========================
    # 🚫 RECENT STEP BLOCK
    # =========================

    if step_updates:
        last_step = step_updates[-1].get("step", "").strip().lower()
        if step_lower == last_step:
            score -= 5

    return score

# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)