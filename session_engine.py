def evaluate_session_health(session_data, active_state):

    decisions = session_data.get("decisions", [])
    outcomes = session_data.get("outcome_list", [])
    execution_state = active_state or {}

    # =========================
    # SIGNAL 1 — FAILURE RATE
    # =========================

    recent_outcomes = outcomes[-5:] if outcomes else []
    failure_count = sum(1 for o in recent_outcomes if o == "failed")

    failure_rate = failure_count / len(recent_outcomes) if recent_outcomes else 0

    # =========================
    # SIGNAL 2 — STAGNATION
    # =========================

    completed_steps = execution_state.get("completed_steps", [])
    step_updates = execution_state.get("step_updates", [])

    no_progress = len(completed_steps) == 0 and len(step_updates) >= 3

    # =========================
    # SIGNAL 3 — LOOP DETECTION
    # =========================

    current_step = execution_state.get("current_step")

    loop_count = sum(
        1 for u in step_updates
        if u.get("step") == current_step
    )

    loop_detected = loop_count >= 4

    # =========================
    # DECISION LOGIC
    # =========================

    if failure_rate >= 0.6:
        return {
            "session_decision": "reset_session",
            "reason": "High failure rate in recent decisions"
        }

    if no_progress:
        return {
            "session_decision": "reset_session",
            "reason": "Execution stagnation detected"
        }

    if loop_detected:
        return {
            "session_decision": "reset_session",
            "reason": "Execution loop detected"
        }

    return {
        "session_decision": "continue_session",
        "reason": "Session healthy"
    }