def decide_step_action(current_step, step_updates):

    if not current_step:
        return {
            "decision": "no_action",
            "reason": "No current step"
        }

    # SAFETY
    step_updates = step_updates or []

    # FAILURE COUNT
    failure_count = sum(
        1 for update in step_updates
        if update.get("step") == current_step and update.get("status") == "failed"
    )

    # ATTEMPT COUNT
    attempt_count = sum(
        1 for update in step_updates
        if update.get("step") == current_step
    )

    # =========================
    # LEVEL 3 — PHASE 4 LOGIC
    # =========================

    # STRONG FAILURE → IMPROVE
    if failure_count >= 2:
        return {
            "decision": "improve",
            "reason": "Multiple failures, improve step"
        }

    # SINGLE FAILURE
    if failure_count == 1:
        if attempt_count >= 3:
            return {
                "decision": "improve",
                "reason": "Failure with repeated attempts, improving step"
            }
        else:
            return {
                "decision": "retry",
                "reason": "Single failure, retry step"
            }

    # NO FAILURE
    if failure_count == 0:
        if attempt_count >= 4:
            return {
                "decision": "improve",
                "reason": "Too many attempts without success, improving step"
            }
        else:
            return {
                "decision": "continue",
                "reason": "Execution stable, continue"
            }