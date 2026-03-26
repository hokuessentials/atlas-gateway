def build_execution_state(execution_plan, completed_steps=None):

    if not execution_plan:
        return {
            "current_step": None,
            "completed_steps": [],
            "pending_steps": []
        }

    if completed_steps is None:
        completed_steps = []

    pending_steps = [step for step in execution_plan if step not in completed_steps]

    current_step = pending_steps[0] if pending_steps else None

    return {
        "current_step": current_step,
        "completed_steps": completed_steps,
        "pending_steps": pending_steps[1:] if len(pending_steps) > 1 else []
    }