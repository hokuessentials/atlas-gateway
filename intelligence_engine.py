from scoring_engine import compute_decision_scores, select_best_decision
from reasoning_engine import generate_reason
from sequence_engine import generate_execution_sequence
from execution_engine import build_execution_state

def generate_intelligent_action(session_data):
    
    active_state = session_data.get("active_state", {})
    decisions = session_data.get("decisions", [])
    outcomes = session_data.get("outcome_list", [])

    if not decisions:
        return {
            "action": "Start by logging a decision",
            "priority": "high",
            "reason": "No data",
            "execution_state": build_execution_state([])
        }

    last_decision = decisions[-1]
    last_outcome = str(outcomes[-1]).strip().lower() if outcomes else ""

    scored = compute_decision_scores(session_data)

    if not scored:
        return {
            "action": f"Continue: {last_decision}",
            "priority": "medium",
            "reason": "No scoring data",
            "execution_state": build_execution_state([])
        }

    current_score = 0
    for d in scored:
        if d["title"] == last_decision:
            current_score = d["score"]
            break

    # REMOVE failed decision
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

    best = None
    for d in sorted_decisions:
        if d["title"] != last_decision:
            best = d
            break

    if not best:
        best = sorted_decisions[0]

    best_title = best["title"]
    best_score = best["score"]
    execution_steps = generate_execution_sequence(best_title)
    execution_state = build_execution_state(
    execution_steps,
    active_state.get("completed_steps", [])
    )

    # FORCE SWITCH
    if last_outcome == "failed":
        return {
            "action": f"Switch due to failure: {best_title}",
            "priority": "high",
            "reason": generate_reason(last_decision, best_title, last_outcome),
            "execution_plan": execution_steps,
            "execution_state": execution_state
        }

    # NORMAL SWITCH
    if best_title != last_decision and best_score > current_score + 0.5:
        return {
            "action": f"Switch to higher value: {best_title}",
            "priority": "high",
            "reason": generate_reason(last_decision, best_title, last_outcome),
            "execution_plan": execution_steps,
            "execution_state": execution_state
        }

    return {
        "action": f"Continue: {last_decision}",
        "priority": "high",
        "reason": "Maintain execution flow",
        "execution_plan": execution_steps,
        "execution_state": execution_state
    }