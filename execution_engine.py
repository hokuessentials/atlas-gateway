def build_execution_state(execution_plan):

    if not execution_plan:
        return {
            "current_step": None,
            "completed_steps": [],
            "pending_steps": []
        }

    return {
        "current_step": execution_plan[0],
        "completed_steps": [],
        "pending_steps": execution_plan[1:]
    }