from scoring_engine import compute_decision_scores
from reasoning_engine import generate_reason
from sequence_engine import generate_execution_sequence
from execution_engine import build_execution_state
from step_decision_engine import decide_step_action
from plan_adjustment_engine import adjust_execution_plan
from step_replacement_engine import replace_failed_step

print("🔥 NEW CODE DEPLOYED")

def is_step_allowed(current_step, step_updates):
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

    has_memory = (
        existing_state
        and existing_state.get("current_step")
        and "execution_plan" in existing_state
    )
    if has_memory:

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

    # 👉 FINAL STATE (ONLY IF NO MEMORY)
    if not (existing_state and existing_state.get("current_step")):
        execution_state = build_execution_state(
            adjusted_plan,
            completed_steps
        )

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