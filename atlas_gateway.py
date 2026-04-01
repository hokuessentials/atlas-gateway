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
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=3
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

def log_execution_to_sheet(data):
    try:
        payload = {
            "action": "log_execution",
            "data": data
        }

        requests.post(
            APPS_SCRIPT_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=3
        )

    except Exception as e:
        print("❌ LOG ERROR:", e)

def update_tracker(data):
    try:
        payload = {
            "action": "update_tracker",
            "data": data
        }

        requests.post(
            APPS_SCRIPT_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=3
        )

    except Exception as e:
        print("❌ TRACKER ERROR:", e)

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
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=3
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
            timeout=3
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

    try:
        requests.post(
            APPS_SCRIPT_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=3
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
            timeout=3,
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
        session_id = parsed_state.get("session_id") or input_data.get("session_id")

        if not session_id:
            session_id = "S-" + str(int(time.time()))
            parsed_state["session_id"] = session_id
            try:
               requests.post(
                   APPS_SCRIPT_URL,
                   json={
                       "action": "update_active_state",
                       "payload": {
                           "session_id": session_id
                        }
                    },
                    timeout=3
                )
            except:
               pass

        if not parsed_state.get("session_started"):

            try:
                save_session_to_sheet({
                    "Session_ID": session_id,
                    "Start_Time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Session_Type": "execution",
                    "Active_Module": "Execution Engine",
                    "Active_Phase": "Phase 3.5",
                    "Status": "ACTIVE"
                })

                parsed_state["session_started"] = True

            except:
                pass

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
            max_loops = 4  # safety limit

            start_time = time.time() 
            MAX_RUNTIME = 15 # seconds
            final_response = None

            while loop_count < max_loops:
                loop_count += 1

                # =========================
                # 🔥 FORCE EXECUTION OF CURRENT STEP
                # =========================

                if current_step and current_step not in completed_steps:

                    print("⚡ EXECUTING STEP:", current_step)

                    step_updates.append({
                        "step": current_step,
                        "status": "success",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })

                    completed_steps.append(current_step)
                    
                    score = 0.7 if len(completed_steps) > 1 else 0.5
                    confidence = round(score, 2)
                    expected_roi = round(score * 10, 2)
                    risk_score = round(1 - score, 2)
                    decision_quality = "execution"

                    # SAVE STATE IMMEDIATELY
                    try:
                        if True:
                            save_decision_to_sheet({
                                "Decision_ID": "D-" + str(int(time.time() * 1000)),
                                "Session_ID": session_id,
                                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "Title": current_step,
                                "Description": "Step executed",
                                "Module": "Execution Engine",
                                "Expected_ROI": expected_roi,
                                "Risk_Score": risk_score,
                                "Confidence_Level": confidence,
                                "Decision_Quality": decision_quality,
                                "Reversible_Flag": True,
                                "Decision_Owner": "Atlas",
                                "Tags": "execution",
                                "Decision_Type": "execution",
                                "Outcome_Status": "success",
                                "Lesson_Learned": "Initial execution completed"
                            })
                    except:
                        pass

                if time.time() - start_time > MAX_RUNTIME:
                
                    return jsonify({
                        "status": "timeout_safe_exit",
                        "decision": "partial",
                        "debug": {
                            "current_step": current_step,
                            "completed_steps": completed_steps,
                            "pending_steps": pending_steps
                        }
                    })
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

                    if time.time() - start_time > 20:
                        return jsonify({
                            "status": "timeout_safe_exit",
                            "decision": "partial",
                            "debug": {
                                "current_step": current_step,
                                "completed_steps": completed_steps,
                                "pending_steps": pending_steps
                            }
                        })

                    # ✅ FINAL STEP — ONLY INSIDE THIS BLOCK
                    score = 1
                    confidence = 1
                    expected_roi = 10
                    risk_score = 0
                    decision_quality = "final_step"

                    try:
                       save_decision_to_sheet({
                           "Decision_ID": "D-" + str(int(time.time() * 1000)),
                           "Session_ID": session_id,
                           "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                           "Title": "Execution Complete",
                           "Description": "All steps completed",
                           "Module": "Execution Engine",
                           "Expected_ROI": expected_roi,
                           "Risk_Score": risk_score,
                           "Confidence_Level": confidence,
                           "Decision_Quality": decision_quality,
                           "Reversible_Flag": True,
                           "Decision_Owner": "Atlas",
                           "Tags": "final",
                           "Decision_Type": "execution",
                           "Outcome_Status": "success",
                           "Lesson_Learned": "Execution completed"
                       })
                    except:
                        pass

                    try:
                       save_session_to_sheet({
                           "Session_ID": session_id,
                           "End_Time": time.strftime("%Y-%m-%d %H:%M:%S"),
                           "Status": "CLOSED",
                           "Tasks_Worked": len(completed_steps),
                           "Notes": "Auto closed"
                       })
                    except:
                        pass

                    return jsonify({
                        "status": "success",
                        "decision": "complete",
                        "Decision_Quality": decision_quality,
                        "Score": score,
                        "debug": {
                            "current_step": current_step,
                            "completed_steps": completed_steps,
                            "pending_steps": [],
                            "failed_steps": [],
                            "recent_updates": step_updates[-5:]
                        }
                    })
                # FINAL STEP — NO INTELLIGENCE

                score = 1
                confidence = 1
                expected_roi = 10
                risk_score = 0
                decision_quality = "final_step"

                # 🔥 SAVE FINAL DECISION
                try:
                    save_decision_to_sheet({
                        "Decision_ID": "D-" + str(int(time.time() * 1000)),
                        "Session_ID": session_id,
                        "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "Title": "Execution Complete",
                        "Description": "All steps completed",
                        "Module": "Execution Engine",
                        "Expected_ROI": expected_roi,
                        "Risk_Score": risk_score,
                        "Confidence_Level": confidence,
                        "Decision_Quality": decision_quality,
                        "Reversible_Flag": True,
                        "Decision_Owner": "Atlas",
                        "Tags": "final",
                        "Decision_Type": "execution",
                        "Outcome_Status": "success",
                        "Lesson_Learned": "Execution completed"
                    })
                except:
                    pass

                return jsonify({
                    "status": "success",
                    "decision": "complete",
                    "Decision_Quality": decision_quality,
                    "Score": score,
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
                    try:
                        requests.post(
                            APPS_SCRIPT_URL,
                            json={
                                "action": "update_active_state",
                                "payload": {
                                    "session_id": session_id,
                                    "current_step": current_step,
                                    "completed_steps": completed_steps,
                                    "execution_plan": execution_plan,
                                    "step_updates": step_updates
                                }
                            },
                            timeout=3
                        )
                    except:
                        pass

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
                    
                # =========================
                # 🧠 INTELLIGENT STEP SELECTION
                # =========================

                raw_candidates = available_steps if available_steps else pending_steps
                # ❌ REMOVE CURRENT STEP FROM SELECTION
                raw_candidates = [s for s in raw_candidates if s != current_step]

                # 🧠 APPLY DEPENDENCY FILTER
                candidates = [
                    step for step in raw_candidates
                    if is_step_allowed(step, step_updates, completed_steps)[0]
                ]

                # fallback if everything blocked
                if not candidates:
                    candidates = raw_candidates

                # fallback safety
                if not candidates:
                    next_step = current_step   # ✅ SAFE FALLBACK
                else:
                    try:
                        # 🧠 get better step using intelligence layer
                        better_step = select_better_step(
                            current_step=current_step,
                            candidates=candidates,
                            completed_steps=completed_steps,
                            step_updates=step_updates
                        )

                        next_step = better_step if (better_step and str(better_step).strip() != "") else candidates[0]

                    except Exception as e:
                        print("⚠️ STEP SELECTION ERROR:", e)
                        next_step = candidates[0]


                # ❌ DO NOT mark completed here
                updated_completed = list(completed_steps)

                updated_pending = [
                    s for s in execution_plan if s not in updated_completed
                ]

                # 🔁 UPDATE STATE FOR NEXT LOOP
                pending_steps = updated_pending
                previous_step = current_step

                if next_step:
                    current_step = next_step

                # 🔥 RECOMPUTE pending AFTER updating current_step
                pending_steps = [
                    s for s in execution_plan
                    if s not in completed_steps and s != current_step
                ]

                if not pending_steps:
                    score = score if score else 1
                    confidence = round(score, 2)
                    expected_roi = round(score * 10, 2)
                    risk_score = round(1 - score, 2)
                    decision_quality = "final_step"

                    # 🔥 LOG FINAL DECISION (ADD THIS FIRST)
                    try:
                        if True:
                            save_decision_to_sheet({
                                "Decision_ID": "D-" + str(int(time.time() * 1000)),
                                "Session_ID": session_id,
                                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "Title": "Execution Step",
                                "Description": "Auto decision by Atlas",
                                "Module": "Execution Engine",
                                "Expected_ROI": expected_roi,
                                "Risk_Score": risk_score,
                                "Confidence_Level": confidence,
                                "Decision_Quality": decision_quality,
                                "Reversible_Flag": True,
                                "Decision_Owner": "Atlas",
                                "Tags": "auto",
                                "Decision_Type": "execution",
                                "Outcome_Status": "success",
                                "Lesson_Learned": "Initial execution completed"
                            })
                    except:
                        pass

                    try:
                        save_session_to_sheet({
                            "Session_ID": session_id,
                            "Start_Time": "",
                            "End_Time": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "Session_Type": "execution",
                            "Active_Module": "Execution Engine",
                            "Active_Phase": "Phase 3.5",
                            "Tasks_Worked": len(completed_steps),
                            "Issues_Found": 0,
                            "Status": "CLOSED",
                            "Snapshot_ID": "",
                            "Notes": "Auto closed"
                        })
                    
                    except:
                        pass

                    return jsonify({
                        "status": "success",
                        "decision": "complete",
                        "Decision_Quality": decision_quality,
                        "Score": score,

                        "debug": {
                            "current_step": current_step,
                            "completed_steps": completed_steps,
                            "pending_steps": pending_steps,
                            "failed_steps": [],
                            "recent_updates": step_updates[-5:]
                        }
                    })
                    pending_steps = [
                        s for s in execution_plan
                        if s not in completed_steps and s != current_step
                    ]

                final_response = {
                    "status": "success",
                    "decision": "proceed",
                    "executed_step": previous_step,
                    "next_step": current_step if next_step else (pending_steps[0] if pending_steps else None),

                    # 🔥 DEBUG BLOCK (ADD HERE)
                    "debug": {
                        "current_step": current_step,
                        "selected_step": next_step,
                        "completed_steps": completed_steps,
                        "pending_steps": pending_steps,
                        "failed_steps": failed_steps,
                        "recent_updates": step_updates[-5:]
                    }
                }
            
                # ✅ ENSURE FINAL RESPONSE ALWAYS EXISTS
                if not final_response:
                    final_response = {
                        "status": "success",
                        "decision": "proceed",
                        "executed_step": previous_step,
                        "next_step": current_step if next_step else (pending_steps[0] if pending_steps else None),
                        "debug": {
                            "current_step": current_step,
                            "completed_steps": completed_steps,
                            "pending_steps": pending_steps,
                            "failed_steps": [],
                            "recent_updates": step_updates[-5:]
                        }
                    }

                # 🔥 UPDATE MASTER TRACKER (CORRECT)
                try:
                   update_tracker({
                       "module": "Execution Engine",
                       "phase": "Phase 3.5",
                       "task": "Control Layer Build",
                       "status": "complete" if final_response["decision"] == "complete" else "active",
                       "current_step": current_step,
                       "next_step": final_response.get("next_step"),
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