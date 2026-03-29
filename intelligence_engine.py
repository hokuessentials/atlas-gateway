from scoring_engine import compute_decision_scores
from reasoning_engine import generate_reason
from sequence_engine import generate_execution_sequence
from execution_engine import build_execution_state
from step_decision_engine import decide_step_action
from plan_adjustment_engine import adjust_execution_plan
from step_replacement_engine import replace_failed_step

print("🔥 NEW CODE DEPLOYED")

# =========================
# 🧠 STEP DEPENDENCIES
# =========================

STEP_DEPENDENCIES = {
    "Negotiate price": {
        "depends_on": ["Check supplier pricing"],
        "condition": "success"
    },
    "Check sample quality": {
        "depends_on": ["Negotiate price"],
        "condition": "success"
    },
    "Finalize supplier": {
        "depends_on": ["Check sample quality"],
        "condition": "success"
    }
}


# =========================
# 🧠 DEPENDENCY CHECK ENGINE
# =========================

def is_step_allowed(current_step, step_updates, completed_steps=None):

    rule = STEP_DEPENDENCIES.get(current_step)

    # No dependency → allowed
    if not rule:
        return True, None

    completed_steps = completed_steps or []

    for dep in rule["depends_on"]:

        # ✅ FIRST: check completed_steps (STRONG SOURCE)
        if dep in completed_steps:
            continue

        # ✅ SECOND: fallback to step_updates
        matches = [u for u in step_updates if u.get("step") == dep]

        if not matches:
            return False, dep

        latest = matches[-1]

        if rule["condition"] == "success" and latest.get("status") != "success":
            return False, dep

    return True, None

# =========================
# 🧠 CANDIDATE STEP ENGINE (PHASE 4)
# =========================

def get_candidate_steps(plan, completed_steps):
    if not plan:
        return []

    completed_steps = set(completed_steps or [])

    candidates = []

    for step in plan:
        if step not in completed_steps:
            candidates.append(step)

    return candidates


def filter_allowed_candidates(candidates, step_updates, completed_steps):
    allowed_steps = []
    for step in candidates:
        allowed, _ = is_step_allowed(step, step_updates, completed_steps)
        if allowed:
            allowed_steps.append(step)
    return allowed_steps


def score_steps_advanced(current_step, candidates, step_updates, session_data):
    """
    PHASE 4 SCORING:
    Combines:
    - failure penalty
    - ROI influence
    - risk penalty
    - confidence boost
    """

    decisions = session_data.get("decisions", [])
    roi_list = session_data.get("roi_list", [])
    risk_list = session_data.get("risk_list", [])
    conf_list = session_data.get("confidence_list", [])
    try:
        memory = build_step_memory(session_data)
    except:
        memory = {}

    def failure_count(step):
        return sum(
            1 for u in (step_updates or [])
            if u.get("step") == step and u.get("status") == "failed"
        )

    def get_last_metric(step, metric_list):
        for i in range(len(decisions) - 1, -1, -1):
            if decisions[i] == step:
                if i < len(metric_list):
                    return metric_list[i]
        return 0

    scores = {}

    for step in candidates:

        fail = failure_count(step)

        roi = get_last_metric(step, roi_list)
        risk = get_last_metric(step, risk_list)
        conf = get_last_metric(step, conf_list)
        mem = memory.get(step, {})
        success_rate = mem.get("success_rate", 0)
        failure_rate = mem.get("failure_rate", 0)

        # normalize
        roi = min(roi / 20, 1)
        risk = min(risk, 1)
        conf = min(conf, 1)

        # base score
        score = 0.5

        # ROI boost
        score += roi * 0.3

        # confidence boost
        score += conf * 0.2

        # risk penalty
        score -= risk * 0.3

        # failure penalty
        if fail > 0:
            score -= min(0.5, fail * 0.25)

        # ALWAYS APPLY MEMORY
        score += success_rate * 0.3
        score -= failure_rate * 0.3

        scores[step] = round(score, 2)

    # current step score
    current_fail = failure_count(current_step)
    mem = memory.get(current_step, {})
    success_rate = mem.get("success_rate", 0)
    failure_rate = mem.get("failure_rate", 0)
    current_roi = get_last_metric(current_step, roi_list)
    current_risk = get_last_metric(current_step, risk_list)
    current_conf = get_last_metric(current_step, conf_list)

    current_roi = min(current_roi / 20, 1)
    current_risk = min(current_risk, 1)
    current_conf = min(current_conf, 1)

    current_score = (
        0.5
        + success_rate * 0.3
        - failure_rate * 0.3
        + current_roi * 0.3
        + current_conf * 0.2
        - current_risk * 0.3
        - min(0.5, current_fail * 0.25)
)

    return scores, round(current_score, 2)

# =========================
# 🧠 MEMORY M2 — STEP INTELLIGENCE
# =========================

def build_step_memory(session_data):

    decisions = session_data.get("decisions", [])
    outcomes = session_data.get("outcome_list", [])

    memory = {}

    for i in range(len(decisions)):
        step = decisions[i]
        outcome = outcomes[i] if i < len(outcomes) else ""

        if step not in memory:
            memory[step] = {
                "success": 0,
                "fail": 0,
                "total": 0
            }

        memory[step]["total"] += 1

        if str(outcome).lower() == "success":
            memory[step]["success"] += 1
        elif str(outcome).lower() == "failed":
            memory[step]["fail"] += 1

    for step in memory:
        total = memory[step]["total"]

        if total > 0:
            memory[step]["success_rate"] = memory[step]["success"] / total
            memory[step]["failure_rate"] = memory[step]["fail"] / total
        else:
            memory[step]["success_rate"] = 0
            memory[step]["failure_rate"] = 0

    return memory    


def select_better_step(current_step, candidates, step_updates, completed_steps, session_data):
    """
    PHASE 4 SWITCHING (CLEAN FINAL)
    """

    if not current_step or not candidates:
        return current_step

    # =========================
    # RULE 1: dependency block
    # =========================
    allowed, _ = is_step_allowed(current_step, step_updates, completed_steps)
    if not allowed:
        return candidates[0]

    # =========================
    # ADVANCED SCORING
    # =========================
    scores, current_score = score_steps_advanced(
        current_step,
        candidates,
        step_updates,
        session_data
    )
    if not scores:
        return current_step

    best_step = max(scores, key=scores.get)
    best_score = scores[best_step]

    print("📊 STEP SCORES:", scores, "| CURRENT:", current_score)

    # =========================
    # RULE 2: SWITCH ONLY IF CLEARLY BETTER
    # =========================
    if best_score > current_score + 0.2:
        print("⚡ SWITCH DECISION:", current_step, "→", best_step)
        return best_step

    return current_step

def generate_intelligent_action(session_data):
    
    # =========================
    # GET STATE
    # =========================

    active_state = session_data.get("active_state", {})
    existing_state = active_state if active_state else {}

    decisions = session_data.get("decisions", [])
    outcomes = session_data.get("outcome_list", [])

    # =========================
    # EMPTY CASE
    # =========================
    
    existing_state = active_state if active_state else {}

    # =========================
    # 🔥 MEMORY CONTROL FIX
    # =========================

    force_mode = active_state.get("force_mode", False)

    has_memory = (
        existing_state
        and existing_state.get("current_step")
        and "execution_plan" in existing_state
    )

    if has_memory and not force_mode:

        execution_state = existing_state
        execution_steps = existing_state.get("execution_plan", [])
        step_updates = existing_state.get("step_updates", [])

        step_decision = decide_step_action(
            execution_state.get("current_step"),
            step_updates
        )

        return {
            "action": "Continue from memory",
            "priority": "high",
            "reason": "Resuming saved execution state",
            "execution_plan": execution_steps,
            "execution_state": execution_state,
            "step_decision": step_decision
        }
    if not decisions:
        execution_state = existing_state if existing_state.get("current_step") else build_execution_state([])

        return {
            "action": "Start by logging a decision",
            "priority": "high",
            "reason": "No data",
            "execution_plan": [],
            "execution_state": execution_state,
            "step_decision": {
                "decision": "no_action",
                "reason": "No execution available"
            }
        }

    last_decision = decisions[-1]
    last_outcome = str(outcomes[-1]).strip().lower() if outcomes else ""

    # =========================
    # SCORING
    # =========================

    scored = compute_decision_scores(session_data)

    if not scored:
        execution_state = existing_state if existing_state.get("current_step") else build_execution_state([])

        return {
            "action": f"Continue: {last_decision}",
            "priority": "medium",
            "reason": "No scoring data",
            "execution_plan": [],
            "execution_state": execution_state,
            "step_decision": {
                "decision": "no_action",
                "reason": "No execution available"
            }
        }

    # =========================
    # FIND CURRENT SCORE
    # =========================

    current_score = next((d["score"] for d in scored if d["title"] == last_decision), 0)

    # REMOVE FAILED
    filtered = [
        d for i, d in enumerate(scored)
        if not (i == len(scored) - 1 and last_outcome == "failed")
    ]

    sorted_decisions = sorted(
        filtered if filtered else scored,
        key=lambda x: x["score"],
        reverse=True
    )

    # =========================
    # PICK BEST
    # =========================

    best = next((d for d in sorted_decisions if d["title"] != last_decision), sorted_decisions[0])

    best_title = best["title"]
    best_score = best["score"]

    # =========================
    # EXECUTION PLAN
    # =========================

    if existing_state and existing_state.get("current_step") and existing_state.get("execution_plan"):
        execution_steps = existing_state.get("execution_plan", [])
    else:
        execution_steps = generate_execution_sequence(best_title)

    step_updates = active_state.get("step_updates", [])
    completed_steps = active_state.get("completed_steps", [])

    # =========================
    # 🔥 MEMORY-FIRST STATE
    # =========================

    if existing_state and existing_state.get("current_step") and existing_state.get("execution_plan"):
        execution_state = existing_state
    else:
        execution_state = build_execution_state(
            execution_steps,
            completed_steps
        )

    # =========================
    # STEP DECISION
    # =========================

    step_decision = decide_step_action(
        execution_state.get("current_step"),
        step_updates
    )

    # =========================
    # PLAN ADJUSTMENT
    # =========================

    adjusted_plan = adjust_execution_plan(
        execution_steps,
        execution_state,
        step_decision
    )

    # 👉 ONLY rebuild if NO memory
    if not (existing_state and existing_state.get("current_step") and "execution_plan" in existing_state):
        execution_state = build_execution_state(
            adjusted_plan,
            completed_steps
        )

    # =========================
    # AI STEP REPLACEMENT
    # =========================

    adjusted_plan = replace_failed_step(
        adjusted_plan,
        execution_state,
        step_decision
    )
    # ✅ SYNC current step with plan
    current = execution_state.get("current_step")

    if current and current not in adjusted_plan:
        adjusted_plan.insert(0, current)

    # 👉 ALWAYS SYNC STATE WITH UPDATED PLAN
    execution_state["execution_plan"] = adjusted_plan

    # REMOVE COMPLETED STEPS NOT IN PLAN
    execution_state["completed_steps"] = [
        s for s in execution_state.get("completed_steps", [])
        if s in adjusted_plan
    ]

    # FIX current_step if invalid
    current = execution_state.get("current_step")

    if current not in adjusted_plan:
        execution_state["current_step"] = adjusted_plan[0]

    # =========================
    # FINAL STEP DECISION
    # =========================

    step_decision = decide_step_action(
        execution_state.get("current_step"),
        step_updates
    )

    best_score = best.get("score", 0)

    if best_score >= 0.7:
        decision_quality = "strong"
        execution_action = "execute"
    elif best_score >= 0.5:
        decision_quality = "moderate"
        execution_action = "continue"
    else:
        decision_quality = "weak"
        execution_action = "hold"

    step_decision["decision_score"] = round(best_score, 2)
    step_decision["decision_quality"] = decision_quality
    step_decision["execution_action"] = execution_action
    step_decision["decision"] = execution_action

    if execution_action == "execute":
        step_decision["reason"] = "High confidence decision, execute immediately"
    elif execution_action == "continue":
        step_decision["reason"] = "Moderate confidence, continue execution"
    else:
        step_decision["reason"] = "Low confidence, hold execution"

    # =========================
    # OUTPUT
    # =========================

    if last_outcome == "failed":
        return {
            "action": f"Switch due to failure: {best_title}",
            "priority": "high",
            "reason": generate_reason(last_decision, best_title, last_outcome),
            "execution_plan": adjusted_plan,
            "execution_state": execution_state,
            "execution_state": execution_state,
            "step_decision": step_decision
        }

    if best_title != last_decision and best_score > current_score + 0.15:
        return {
            "action": f"Switch to higher value: {best_title}",
            "priority": "high",
            "reason": generate_reason(last_decision, best_title, last_outcome),
            "execution_plan": adjusted_plan,
            "execution_state": execution_state,
            "execution_state": execution_state,
            "step_decision": step_decision
        }

    return {
        "action": f"Continue: {last_decision}",
        "priority": "high",
        "reason": "Maintain execution flow",
        "execution_plan": adjusted_plan,
        "execution_state": execution_state,
        "execution_state": execution_state,
        "step_decision": step_decision
    }