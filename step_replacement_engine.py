from ai_step_engine import generate_better_step


def replace_failed_step(execution_plan, execution_state, step_decision):

    decision = step_decision.get("decision")
    current_step = execution_state.get("current_step")

    if not current_step:
        return execution_plan

    new_plan = []

    for step in execution_plan:

        if current_step and current_step.lower() in step.lower():
            new_plan.append(generate_better_step(step))
        else:
            new_plan.append(step)

    return new_plan