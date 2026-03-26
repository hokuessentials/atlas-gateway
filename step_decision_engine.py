def decide_step_action(current_step, step_updates):

    if not current_step:
        return {
            "decision": "no_action",
            "reason": "No current step"
        }

    step_status = None

    for update in step_updates:
        if update.get("step") == current_step:
            step_status = update.get("status")
            break

    if not step_status:
        return {
            "decision": "continue",
            "reason": "No update, continue execution"
        }

    if step_status == "completed":
        return {
            "decision": "move_next",
            "reason": "Step completed successfully"
        }

    if step_status == "failed":
        return {
            "decision": "retry",
            "reason": "Step failed, retry required"
        }

    if step_status == "blocked":
        return {
            "decision": "switch",
            "reason": "Step blocked, need alternative path"
        }

    return {
        "decision": "continue",
        "reason": "Unknown status"
    }