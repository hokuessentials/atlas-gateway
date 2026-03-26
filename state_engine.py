import datetime

print("🔥 LEVEL 2 ENGINE ACTIVE")

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

print("🔥 REQUEST HIT:", datetime.datetime.now())

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

    decisions = session_data.get("decisions", [])[-5:]
    roi_list = session_data.get("roi_list", [])[-5:]
    risk_list = session_data.get("risk_list", [])[-5:]
    conf_list = session_data.get("confidence_list", [])[-5:]
    outcomes = session_data.get("outcome_list", [])[-5:]

    scored = []

    for i in range(len(decisions)):

        title = str(decisions[i])

        roi = float(roi_list[i]) if i < len(roi_list) else 0
        risk = float(risk_list[i]) if i < len(risk_list) else 0
        conf = float(conf_list[i]) if i < len(conf_list) else 0

        outcome = str(outcomes[i]).strip().lower() if i < len(outcomes) else ""

        success_weight = 1

        if outcome == "success":
            success_weight = 1.5
        elif outcome == "failed":
            success_weight = 0.2

        score = ((roi * conf) - risk) * success_weight

        scored.append({
            "title": title,
            "score": score
        })

    return scored

def select_best_decision(scored):
    if not scored:
        return None
    return sorted(scored, key=lambda x: x["score"], reverse=True)[0]

# ================================
# INTELLIGENCE (FIXED PROPERLY)
# ================================
def generate_intelligent_action(session_data):

    decisions = session_data.get("decisions", [])
    outcomes = session_data.get("outcome_list", [])

    if not decisions:
        return {
            "action": "Start by logging a decision",
            "priority": "high",
            "reason": "No data"
        }

    last_decision = decisions[-1]
    last_outcome = str(outcomes[-1]).strip().lower() if outcomes else ""

    scored = compute_decision_scores(session_data)

    if not scored:
        return {
            "action": f"Continue: {last_decision}",
            "priority": "medium",
            "reason": "No scoring data"
        }

    current_score = scored[-1]["score"]

    # REMOVE failed decision from candidates
    filtered = []

    for i, d in enumerate(scored):
        if i == len(scored) - 1 and last_outcome == "failed":
            continue
        filtered.append(d)

    # pick NEXT BEST (not same as last)
    sorted_decisions = sorted(filtered if filtered else scored, key=lambda x: x["score"], reverse=True)

    best = None
    for d in sorted_decisions:
        if d["title"] != last_decision:
           best = d
           break

    if not best:
    best = sorted_decisions[0]

    best_title = best["title"]
    best_score = best["score"]

    # FORCE SWITCH IF FAILED
    if last_outcome == "failed":
        return {
            "action": f"Switch due to failure: {best_title}",
            "priority": "high",
            "reason": "Last decision failed → forcing change"
        }

    # NORMAL LOGIC
    if best_title != last_decision and best_score > current_score + 0.5:
        return {
            "action": f"Switch to higher value: {best_title}",
            "priority": "high",
            "reason": f"Better decision (current={round(current_score,2)}, best={round(best_score,2)})"
        }

    return {
        "action": f"Continue: {last_decision}",
        "priority": "high",
        "reason": "Maintain execution flow"
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