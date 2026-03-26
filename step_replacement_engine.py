def replace_failed_step(execution_plan, execution_state, step_decision):

    decision = step_decision.get("decision")
    current_step = execution_state.get("current_step")

    # if not retry, do nothing
    if decision != "retry" or not current_step:
        return execution_plan

    new_plan = []

    for step in execution_plan:

        if step == current_step:
            # replace with improved step
            new_plan.append(f"Improve: {step}")
        else:
            new_plan.append(step)

    return new_plan