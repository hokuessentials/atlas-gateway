import requests
import datetime

print("🔥 LEVEL 2 ENGINE ACTIVE")

# ================================
# ACTIVE STATE
# ================================
ACTIVE_STATE = {
    "phase": "BUILD",
    "current_goal": {},
    "current_task": {},
    "next_best_action": {},
    "blockers": [],
    "focus_module": None,
    "execution_mode": "idle",
    "last_updated": None
}

# ================================
# SAFE SCORING ENGINE
# ================================
def compute_score(roi, risk, confidence):
    try:
        roi = float(roi or 0)
        risk = float(risk or 0)
        confidence = float(confidence or 0)

        score = (roi * 2 * confidence) - (risk * 3)
        return round(score, 3)

    except:
        return 0

# ================================
# SAFE BEST DECISION SELECTOR
# ================================
def select_best_decision(session_data):

    decisions = session_data.get("decisions", [])
    roi_list = session_data.get("roi_list", [])
    risk_list = session_data.get("risk_list", [])
    conf_list = session_data.get("confidence_list", [])

    best = None
    best_score = -999

    for i in range(len(decisions)):

        roi = roi_list[i] if i < len(roi_list) else 0
        risk = risk_list[i] if i < len(risk_list) else 0
        conf = conf_list[i] if i < len(conf_list) else 0

        score = compute_score(roi, risk, conf)

        if score > best_score:
            best_score = score
            best = decisions[i]

    return best, best_score

# ================================
# INTELLIGENT ACTION ENGINE
# ================================
def generate_intelligent_action(session_data):

    module_count = session_data.get("module_count", {})
    decisions = session_data.get("decisions", [])

    if not decisions:
        return {
            "action": "Start by logging a decision",
            "priority": "high",
            "reason": "No decisions found"
        }

    last_decision = decisions[-1]

    # 🔥 NEW: scoring integration (SAFE)
    try:
        best_decision, best_score = select_best_decision(session_data)
    except Exception as e:
        print("⚠️ scoring failed:", e)
        best_decision = last_decision
        best_score = 0

    # ================================
    # MODULE LOGIC (OLD SYSTEM SAFE)
    # ================================
    if module_count:

        focus_module = max(module_count, key=module_count.get)

        if focus_module == "Supplier":
            return {
                "action": "Contact supplier → confirm price → negotiate terms",
                "priority": "high",
                "reason": "Supplier workflow continuation"
            }

        elif focus_module == "Product":
            return {
                "action": "Finalize product specs → validate quality → prepare listing",
                "priority": "high",
                "reason": "Product development stage"
            }

        elif focus_module == "Finance":
            return {
                "action": "Update cost sheet → calculate margins → validate pricing",
                "priority": "high",
                "reason": "Financial validation"
            }

        elif focus_module == "Marketing":
            return {
                "action": "Plan creatives → launch ads → monitor performance",
                "priority": "high",
                "reason": "Marketing execution"
            }

    # 🔥 FALLBACK WITH INTELLIGENCE
    if best_decision and best_decision != last_decision:
        return {
            "action": f"Execute immediately: {best_decision}",
            "priority": "high",
            "reason": f"Higher value decision detected (score={best_score})"
        }

    return {
        "action": f"Continue execution after: {last_decision}",
        "priority": "medium",
        "reason": f"Current workflow stable (score={best_score})"
    }

# ================================
# EXECUTION MODE
# ================================
def compute_execution_mode():

    if ACTIVE_STATE.get("blockers"):
        if len(ACTIVE_STATE["blockers"]) > 0:
            return "stuck"

    task = ACTIVE_STATE.get("current_task")

    if task and task.get("status") == "in_progress":
        return "active"

    if not task:
        return "idle"

    return "review"

# ================================
# MAIN STATE UPDATE
# ================================
def update_state(session_data, triggers):

    global ACTIVE_STATE

    ACTIVE_STATE["current_task"] = {}
    ACTIVE_STATE["focus_module"] = None
    ACTIVE_STATE["next_best_action"] = {}

    decisions = session_data.get("decisions", [])
    module_count = session_data.get("module_count", {})

    if not decisions:
        ACTIVE_STATE["execution_mode"] = "idle"
        ACTIVE_STATE["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return

    if module_count:
        ACTIVE_STATE["focus_module"] = max(module_count, key=module_count.get)

    last_decision = decisions[-1]

    ACTIVE_STATE["current_task"] = {
        "task_id": f"T-{int(datetime.datetime.now().timestamp())}",
        "title": last_decision,
        "module": ACTIVE_STATE["focus_module"],
        "status": "in_progress",
        "priority": "high"
    }

    # 🔥 SAFE CALL
    ACTIVE_STATE["next_best_action"] = generate_intelligent_action(session_data)

    ACTIVE_STATE["execution_mode"] = compute_execution_mode()
    ACTIVE_STATE["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")