from flask import Flask, request, jsonify
import requests
import json
import time
import os
import state_engine
from step_decision_engine import decide_step_action
from intelligence_engine import select_better_step
from intelligence_engine import generate_intelligent_action
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

def save_state_to_sheet(data):
    print("🧪 STATE SAVE (BYPASSED)")

def log_execution_to_sheet(data):
    print("🧪 EXECUTION LOG (BYPASSED)")

def update_tracker(data):
    print("🧪 TRACKER (BYPASSED)")

def save_decision_to_sheet(data):
    print("🧪 DECISION LOG (BYPASSED)")
def load_state_from_sheet():
    print("🧪 STATE LOAD (BYPASSED)")
    return {}

def read_full_system_memory():
    print("🧪 FULL MEMORY (BYPASSED)")
    return {}
def read_product_master():
    print("🧪 PRODUCT LOAD (BYPASSED)")
    return []
def save_product_to_sheet(product_data):
    try:
        requests.post(
            APPS_SCRIPT_URL,
            data=json.dumps({
                    "action": "save_product",
                    "data": product_data
            }),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
    except Exception as e:
        print("❌ PRODUCT SAVE ERROR:", e)    
# =========================
# SESSION LOAD
# =========================

def load_session_from_sheet():
    print("🧪 SESSION LOAD (BYPASSED)")
    return {
        "session_id": None,
        "decisions": [],
        "module_count": {},
        "roi_list": [],
        "risk_list": [],
        "confidence_list": [],
        "outcome_list": []
    }
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
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
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
        res = requests.post(
            APPS_SCRIPT_URL,
            data=json.dumps({
                "action": "save_session",
                "data": session
            }),
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print("🔥 SESSION SAVE STATUS:", res.status_code)
        print("🔥 SESSION SAVE RESPONSE:", res.text)

    except Exception as e:
        print("❌ SESSION SAVE ERROR:", e)

@app.route("/test", methods=["GET"])
def test():
    print("✅ TEST ROUTE HIT")
    return "OK"
@app.before_request
def log_all_requests():
    print("🌍 INCOMING:", request.method, request.path)

@app.route("/atlas/action", methods=["POST"])
def atlas_action():
    print("🚀 REQUEST STARTED")
  
    import requests
    from datetime import datetime

    try:
        input_data = request.get_json(force=True) or {}

        # =========================
        # 🔹 LOAD MEMORY
        # =========================
        # 🔥 TEMP BYPASS (CRITICAL FIX)
        system_memory = {}
        product_data = []
        active_raw = []

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

        # ✅ SESSION INIT
        session_id = parsed_state.get("session_id")

        if not session_id:
            session_id = f"S-{int(time.time())}"
            parsed_state["session_id"] = session_id

        # 🔥 ALWAYS RUN (OUTSIDE IF)
        session_payload = {
            "session_id": session_id,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": "",
            "session_type": "execution",
            "active_module": "Execution Engine",
            "active_phase": "Phase 3.5",
            "tasks_worked": 0,
            "issues_found": 0,
            "status": "ACTIVE",
            "snapshot_id": "",
            "notes": "Auto session sync"
        }

        print("🚀 SESSION SYNC:", session_payload)

        print("✅ BEFORE SESSION POST")

        print("🧪 SESSION SYNC (BYPASSED)", session_payload)

        print("📤 RAW SENT:", json.dumps({
            "action": "save_session",
            "data": session_payload
        }))
        print("✅ AFTER SESSION POST")

        if isinstance(parsed_state, list):
            parsed_state = {}
            

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

        # ✅ SAFETY LOCK (DO NOT REMOVE)
        if not isinstance(step_updates, list):
            step_updates = []

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
            failure_count = 0  # ✅ SAFE INIT
            MAX_RUNTIME = 15 # seconds
            final_response = None

            while loop_count < max_loops:
                loop_count += 1

                # 🔥 AUTO SESSION UPDATE (CRITICAL FIX)
                def save_session_to_sheet(data):
                    print("🧪 SESSION SAVE (BYPASSED)")
                
              

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
                    selected_step = candidates[0]   # 🔥 HARD BYPASS
                    previous_step = current_step
                    next_step_candidate = selected_step

                    previous_step = current_step
                    next_step_candidate = selected_step

                    # ✅ FAIL-SAFE (SAFE CONTINUE)
                    if not next_step_candidate:
                        next_step_candidate = current_step

                # =========================
                # 🧠 DECISION BEFORE EXECUTION
                # =========================

                session_data = {
                    "session_id": session_id,
                    "decisions": [],
                    "module_count": {},
                    "roi_list": [],
                    "risk_list": [],
                    "confidence_list": [],
                    "outcome_list": [],
                    "active_state": {}
                }

                session_data["active_state"] = {
                    "current_step": current_step,
                    "completed_steps": completed_steps,
                    "step_updates": step_updates,
                    "execution_plan": execution_plan
                }

                result = {
                    "step_decision": {
                        "decision": "execute",
                        "execution_action": "continue",
                        "decision_score": 1,
                        "decision_quality": "execution",
                        "reason": "temp bypass",
                        "metrics": {}
                    }
                }

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

                    previous_step = current_step
                    next_step = next_step_candidate

                    # =========================
                    # ⚡ EXECUTE
                    # =========================
                    step_updates.append({
                        "step": previous_step,
                        "status": "success",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })

                    completed_steps.append(previous_step.strip())

                    # =========================
                    # 🔄 MOVE STEP
                    # =========================
                    current_step = next_step

                    # =========================
                    # 🧾 LOG (CLEAN)
                    # =========================
                    print("STEP:", previous_step)
                    print("NEXT:", current_step)

                    # =========================
                    # 💾 SAVE (ONLY ONE MAIN SAVE)
                    # =========================
                    
                    def save_state_to_sheet(data):
                        print("🧪 STATE SAVE (BYPASSED)")

                    pending_steps = [
                        s for s in execution_plan
                        if s not in completed_steps and s != current_step
                    ]

                    final_response = {
                        "status": "success",
                        "executed_step": previous_step,
                        "next_step": current_step,
                        "decision": decision,
                        "Decision_Quality": decision_quality,
                        "Score": decision_score,
                        "debug": {
                            "current_step": current_step,
                            "completed_steps": completed_steps,
                            "pending_steps": pending_steps,
                            "recent_updates": step_updates[-5:],
                            "product_count": len(product_data)
                        }
                    }
    
                
                    # =========================
                    # ⏱ TIME + FAILURE GUARD (FIXED)
                    # =========================

                    failure_count = sum(
                        1 for s in step_updates
                        if isinstance(s, dict) and s.get("status") == "failed"
                    )

                    if time.time() - start_time > MAX_RUNTIME:
                        if failure_count >= 5:
                            return jsonify({
                                "status": "warning",
                                "decision": "blocked"
                            })

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

                def save_session_to_sheet(data):
                    print("🧪 SESSION SAVE (BYPASSED)")

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
                    final_response = {
                        "status": "success",
                        "decision": "complete",
                        "Decision_Quality": decision_quality,
                        "Score": decision_score,
                        "reason": step_decision.get("reason"),
                        "metrics": step_decision.get("metrics"),
                        "debug": {
                            "current_step": current_step,
                            "completed_steps": completed_steps,
                            "pending_steps": [],
                            "failed_steps": [],
                            "recent_updates": step_updates[-5:]
                        }
                    }
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
    
                def save_decision_to_sheet(data):
                    print("🧪 DECISION LOG (BYPASSED)")

            # 🔥 UPDATE MASTER TRACKER (CORRECT)
       
                def update_tracker(data):
                    print("🧪 TRACKER (BYPASSED)")
        

            # 🔥 AUTO LOG EXECUTION
         
                def log_execution_to_sheet(data):
                    print("🧪 EXECUTION LOG (BYPASSED)")

            return jsonify(final_response)

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