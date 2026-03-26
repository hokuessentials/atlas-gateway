from scoring_engine import compute_decision_scores, select_best_decision
from reasoning_engine import generate_reason
from sequence_engine import generate_execution_sequence
from execution_engine import build_execution_state
from step_decision_engine import decide_step_action
from plan_adjustment_engine import adjust_execution_plan
from step_replacement_engine import replace_failed_step

print("🔥 NEW CODE DEPLOYED")
def generate_intelligent_action(session_data):

    # 👉 GET ACTIVE STATE
    active_state = session_data.get("active_state", {})

    decisions = session_data.get("decisions", [])
    outcomes = session_data.get("outcome_list", [])

    # 👉 HANDLE EMPTY CASE
    if not decisions:
        execution_state = build_execution_state([])
        step_decision = {
            "decision": "no_action",
            "reason": "No execution available"
        }

        return {
            "action": "Start by logging a decision",
            "priority": "high",
            "reason": "No data",
            "execution_plan": [],
            "execution_state": execution_state,
            "step_decision": step_decision
        }

    last_decision = decisions[-1]
    last_outcome = str(outcomes[-1]).strip().lower() if outcomes else ""

    scored = compute_decision_scores(session_data)

    # 👉 HANDLE NO SCORE CASE
    if not scored:
        execution_state = build_execution_state([])
        step_decision = {
            "decision": "no_action",
            "reason": "No execution available"
        }

        return {
            "action": f"Continue: {last_decision}",
            "priority": "medium",
            "reason": "No scoring data",
            "execution_plan": [],
            "execution_state": execution_state,
            "step_decision": step_decision
        }

    # 👉 FIND CURRENT SCORE
    current_score = 0
    for d in scored:
        if d["title"] == last_decision:
            current_score = d["score"]
            break

    # 👉 REMOVE FAILED DECISION
    filtered = []
    for i, d in enumerate(scored):
        if i == len(scored) - 1 and last_outcome == "failed":
            continue
        filtered.append(d)

    sorted_decisions = sorted(
        filtered if filtered else scored,
        key=lambda x: x["score"],
        reverse=True
    )

    # 👉 PICK BEST DECISION
    best = None
    for d in sorted_decisions:
        if d["title"] != last_decision:
            best = d
            break

    if not best:
        best = sorted_decisions[0]

    best_title = best["title"]
    best_score = best["score"]

    # 👉 GENERATE EXECUTION PLAN
    execution_steps = generate_execution_sequence(best_title)

    # 👉 INPUT DATA
    step_updates = active_state.get("step_updates", [])
    completed_steps = active_state.get("completed_steps", [])

    # 👉 BUILD INITIAL STATE
    execution_state = build_execution_state(
        execution_steps,
        completed_steps
    )

    # 👉 INITIAL STEP DECISION
    step_decision = decide_step_action(
        execution_state.get("current_step"),
        step_updates
    )

    # 👉 ADJUST PLAN
    adjusted_plan = adjust_execution_plan(
        execution_steps,
        execution_state,
        step_decision
    )

    # 👉 REBUILD STATE BEFORE REPLACEMENT (IMPORTANT FIX)
    temp_state = build_execution_state(
        adjusted_plan,
        completed_steps
    )

    # 👉 REPLACE STEP USING UPDATED STATE
    adjusted_plan = replace_failed_step(
        adjusted_plan,
        temp_state,
        step_decision
    )

    # 👉 FINAL STATE (BASED ON FINAL PLAN)
    execution_state = build_execution_state(
        adjusted_plan,
        completed_steps
    )

    # 👉 FINAL STEP DECISION
    step_decision = decide_step_action(
        execution_state.get("current_step"),
        step_updates
    )

    # 👉 FORCE SWITCH
    if last_outcome == "failed":
        return {
            "action": f"Switch due to failure: {best_title}",
            "priority": "high",
            "reason": generate_reason(last_decision, best_title, last_outcome),
            "execution_plan": adjusted_plan,
            "execution_state": execution_state,
            "step_decision": step_decision
        }

    # 👉 NORMAL SWITCH
    if best_title != last_decision and best_score > current_score + 0.5:
        return {
            "action": f"Switch to higher value: {best_title}",
            "priority": "high",
            "reason": generate_reason(last_decision, best_title, last_outcome),
            "execution_plan": adjusted_plan,
            "execution_state": execution_state,
            "step_decision": step_decision
        }

    # 👉 CONTINUE
    return {
        "action": f"Continue: {last_decision}",
        "priority": "high",
        "reason": "Maintain execution flow",
        "execution_plan": adjusted_plan,
        "execution_state": execution_state,
        "step_decision": step_decision
    }