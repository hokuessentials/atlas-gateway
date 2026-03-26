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
# RESET STATE
# ================================
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
# MODULE DETECTION
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

    if total == 0:
        return []

    for i in range(total):

        title = str(decisions[i])

        roi = float(roi_list[i]) if i < len(roi_list) else 0
        risk = float(risk_list[i]) if i < len(risk_list) else 0
        conf = float(conf_list[i]) if i < len(conf_list) else 0

        # NORMALIZATION
        roi_norm = roi / 20
        risk_norm = risk
        conf_norm = conf

        # RECENCY
        recency_weight = (i + 1) / total

        # FINAL SCORE
        score = (roi_norm * 5 * conf_norm) - (risk_norm * 3) + (recency_weight * 2)

        scored.append({
            "title": title,
            "score": round(score, 3),
            "roi": roi,
            "risk": risk,
            "confidence": conf,
            "recency": round(recency_weight, 3)
        })

    return scored

# ================================
# DECISION SELECTOR
# ================================
def select_best_decision(scored):

    if not scored:
        return None

    valid = [d for d in scored if isinstance(d.get("score"), (int, float))]

    if not valid:
        return None

    best = sorted(valid, key=lambda x: x["score"], reverse=True)[0]

    return best

# ================================
# INTELLIGENCE ENGINE
# ================================
def generate_intelligent_action(session_data):

    decisions = session_data.get("decisions", [])

    if not decisions:
        return {
            "action": "Start by logging a decision",
            "priority": "high",
            "reason": "No decision data available"
        }

    last_decision = decisions[-1]

    try:
        scored = compute_decision_scores(session_data)
        best = select_best_decision(scored)

    except Exception as e:
        print("🔥 INTELLIGENCE ERROR:", e)
        return {
            "action": f"Continue: {last_decision}",
            "priority": "medium",
            "reason": "Error fallback"
        }

    if not best:
        return {
            "action": f"Continue: {last_decision}",
            "priority": "medium",
            "reason": "No valid scoring data"
        }

    best_title = best["title"]
    best_score = best["score"]

    # BEST = CURRENT
    if best_title == last_decision:
        return {
            "action": f"Execute immediately: {last_decision}",
            "priority": "high",
            "reason": f"Best decision (score={best_score}) with strong ROI & confidence"
        }

    # BETTER OPTION EXISTS
    if best_score > 6:
        return {
            "action": f"Execute immediately: {best_title}",
            "priority": "high",
            "reason": f"Higher value decision detected (score={best_score})"
        }

    # CONTINUE FLOW
    return {
        "action": f"Continue execution: {last_decision}",
        "priority": "medium",
        "reason": f"Maintain workflow (score={best_score})"
    }

# ================================
# EXECUTION MODE
# ================================
def compute_execution_mode():

    if ACTIVE_STATE.get("blockers") and len(ACTIVE_STATE["blockers"]) > 0:
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

    # MODULE DETECTION
    if module_count:
        ACTIVE_STATE["focus_module"] = max(module_count, key=module_count.get).lower()
    else:
        ACTIVE_STATE["focus_module"] = detect_module_from_title(decisions[-1])

    last_decision = decisions[-1]

    # CURRENT TASK
    ACTIVE_STATE["current_task"] = {
        "task_id": f"T-{int(datetime.datetime.now().timestamp())}",
        "title": last_decision,
        "module": ACTIVE_STATE["focus_module"],
        "status": "in_progress",
        "priority": "high"
    }

    # INTELLIGENCE
    ACTIVE_STATE["next_best_action"] = generate_intelligent_action(session_data)

    # EXECUTION MODE
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