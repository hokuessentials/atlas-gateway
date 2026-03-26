def replace_failed_step(execution_plan, execution_state, step_decision):

    decision = step_decision.get("decision")
    current_step = execution_state.get("current_step")

    if decision != "retry" or not current_step:
        return execution_plan

    new_plan = []

    for step in execution_plan:

        if step == current_step:

            # smarter replacement rules
            if "negotiate" in step.lower():
                new_plan.append("Compare supplier quotes and renegotiate pricing")

            elif "check" in step.lower():
                new_plan.append("Validate supplier data with cross-verification")

            elif "confirm" in step.lower():
                new_plan.append("Verify quality through sample testing and feedback")

            else:
                new_plan.append(f"Improve execution of: {step}")

        else:
            new_plan.append(step)

    return new_plan