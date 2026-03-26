import datetime
print("🔥 NEW ENGINE LIVE")
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

def reset_state():
    ACTIVE_STATE.clear()
    ACTIVE_STATE.update({
        "phase": "BUILD",
        "current_goal": {},
        "current_task": {},
        "next_best_action": {},
        "blockers": [],
        "focus_module": None,
        "execution_mode": "idle",
        "last_updated": None
    })

# ================================
# MODULE DETECTION (NEW FIX)
# ================================
def detect_module_from_title(title):

    t = title.lower()

    if "supplier" in t:
        return "supplier"
    elif "product" in t:
        return "product"
    elif "finance" in t:
        return "finance"
    elif "marketing" in t:
        return "marketing"

    return "general"

# ================================
# SCORING ENGINE
# ================================
def compute_decision_scores(session_data):

    decisions = session_data.get("decisions", [])
    roi_list = session_data.get("roi_list", [])
    risk_list = session_data.get("risk_list", [])
    conf_list = session_data.get("confidence_list", [])

    scored = []
    total = len(decisions)

    for i in range(total):

        title = str(decisions[i])

        try:
            roi = float(roi_list[i]) if i < len(roi_list) else 0
        except:
            roi = 0

        try:
            risk = float(risk_list[i]) if i < len(risk_list) else 0
        except:
            risk = 0

        try:
            conf = float(conf_list[i]) if i < len(conf_list) else 0
        except:
            conf = 0

        # 🔥 RECENCY WEIGHT (IMPORTANT)
        recency_weight = (i + 1) / total   # newer = closer to 1

        # 🔥 FINAL SCORE
        score = (roi * conf) - risk + (recency_weight * 5)

        scored.append({
            "title": title,
            "score": score
        })

    return scored

def select_best_decision(scored):

    if not scored:
        return None

    # sort by score (highest first)
    best = sorted(scored, key=lambda x: x.get("score", 0), reverse=True)[0]

    return best
# ================================
# INTELLIGENCE
# ================================
def generate_intelligent_action(session_data):

    decisions = session_data.get("decisions", [])
    if not decisions:
        return {
            "action": "Start by logging a decision",
            "priority": "high",
            "reason": "No data"
        }

    last_decision = decisions[-1]

    scored = compute_decision_scores(session_data)
    best = select_best_decision(scored)

    if not best:
        return {
            "action": f"Continue: {last_decision}",
            "priority": "medium",
            "reason": "No scoring data"
        }

    best_title = best["title"]
    best_score = best["score"]

    if best_title == last_decision:
        return {
            "action": f"Execute immediately: {last_decision}",
            "priority": "high",
            "reason": f"Score: {best.get('score')} (ROI high, risk controlled)"
        }

    if best_score > 8:
        return {
            "action": f"Execute immediately: {best_title}",
            "priority": "high",
            "reason": "Higher value decision available"
        }

    return {
        "action": f"Continue execution: {last_decision}",
        "priority": "medium",
        "reason": "Maintain workflow"
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
# MAIN ENGINE
# ================================
def update_state(session_data, triggers):

    reset_state()

    decisions = session_data.get("decisions", [])
    module_count = session_data.get("module_count", {})

    if not decisions:
        ACTIVE_STATE["execution_mode"] = "idle"
        ACTIVE_STATE["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return

    # 🔥 FIXED MODULE LOGIC
    if module_count:
        ACTIVE_STATE["focus_module"] = max(module_count, key=module_count.get).lower()
    else:
        ACTIVE_STATE["focus_module"] = detect_module_from_title(decisions[-1])

    last_decision = decisions[-1]

    ACTIVE_STATE["current_task"] = {
        "task_id": f"T-{int(datetime.datetime.now().timestamp())}",
        "title": last_decision,
        "module": ACTIVE_STATE["focus_module"],
        "status": "in_progress",
        "priority": "high"
    }

    ACTIVE_STATE["next_best_action"] = generate_intelligent_action(session_data)

    ACTIVE_STATE["execution_mode"] = compute_execution_mode()
    ACTIVE_STATE["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ================================
# BLOCKERS
# ================================
def add_blocker(description, impact="high"):
    ACTIVE_STATE["blockers"].append({
        "type": "manual",
        "description": description,
        "impact": impact
    })

def clear_blockers():
    ACTIVE_STATE["blockers"] = []

def complete_current_task():

    if not ACTIVE_STATE["current_task"]:
        return

    last_task = ACTIVE_STATE["current_task"]["title"]
    last_module = ACTIVE_STATE["current_task"]["module"]

    ACTIVE_STATE["current_task"] = {
        "task_id": f"T-{int(datetime.datetime.now().timestamp())}",
        "title": f"Next step after: {last_task}",
        "module": last_module,
        "status": "in_progress",
        "priority": "high"
    }

    ACTIVE_STATE["focus_module"] = last_module

    ACTIVE_STATE["next_best_action"] = {
        "action": f"Continue: {last_task}",
        "reason": "Auto continuation",
        "priority": "high"
    }

    ACTIVE_STATE["execution_mode"] = "active"
    ACTIVE_STATE["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
