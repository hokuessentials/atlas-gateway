def build_execution_state(execution_plan, completed_steps=None):

    if not execution_plan:
        return {
            "current_step": None,
            "completed_steps": [],
            "pending_steps": []
        }

    if not completed_steps:
        return {
            "current_step": execution_plan[0],
            "completed_steps": [],
            "pending_steps": execution_plan[1:]
        }

    # find how many steps are completed IN ORDER
    completed_count = 0

    for i, step in enumerate(execution_plan):
        if i < len(completed_steps) and step == completed_steps[i]:
            completed_count += 1
        else:
            break

    # determine current + pending
    remaining_steps = execution_plan[completed_count:]

    current_step = remaining_steps[0] if remaining_steps else None
    pending_steps = remaining_steps[1:] if len(remaining_steps) > 1 else []

    return {
        "current_step": current_step,
        "completed_steps": execution_plan[:completed_count],
        "pending_steps": pending_steps
    }