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

    # LEVEL 3 — PHASE 2 LOGIC

    if failure_count == 0 and attempt_count >= 4:
        return {
            "decision": "improve",
            "reason": "Too many attempts without success, improving step"
        }

    if failure_count == 0:
        return {
            "decision": "continue",
            "reason": "No failures, continue execution"
        }

    elif failure_count == 1:
        return {
            "decision": "retry",
            "reason": "One failure, retry step"
        }

    else:
        return {
            "decision": "improve",
            "reason": "Multiple failures, improve step"
        }