def decide_step_action(current_step, step_updates):

    if not current_step:
        return {
            "decision": "no_action",
            "reason": "No current step"
        }

    # ✅ SAFETY
    step_updates = step_updates or []

    # ✅ FAILURE COUNT (ONLY LOGIC ALLOWED)
    failure_count = sum(
        1 for update in step_updates
        if update.get("step") == current_step and update.get("status") == "failed"
    )

    # =========================
    # 🧠 LEVEL 3 — PHASE 1 LOGIC
    # =========================

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