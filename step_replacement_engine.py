from ai_step_engine import generate_better_step


def replace_failed_step(execution_plan, execution_state, step_decision):

    if not execution_plan:
        return execution_plan

    current_step = execution_state.get("current_step", "").lower()

    new_plan = []

    for step in execution_plan:

        step_lower = step.lower()

        # 🔥 REVERSE MATCH (THIS IS THE FIX)
        if step_lower and step_lower in current_step:
            new_plan.append(generate_better_step(step))
        else:
            new_plan.append(step)

    return new_plan