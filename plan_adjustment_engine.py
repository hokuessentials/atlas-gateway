def adjust_execution_plan(execution_plan, execution_state, step_decision):

    decision = step_decision.get("decision")
    current_step = execution_state.get("current_step")

    # copy original plan
    new_plan = execution_plan.copy()

    if decision == "retry":
        # keep same plan (no change)
        return new_plan

    if decision == "move_next":
        # no change needed
        return new_plan

    if decision == "switch":
        # remove blocked step
        new_plan = [step for step in new_plan if step != current_step]
        return new_plan

    return new_plan