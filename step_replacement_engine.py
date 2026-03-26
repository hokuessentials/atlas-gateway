from ai_step_engine import generate_better_step


def replace_failed_step(execution_plan, execution_state, step_decision):

    if not execution_plan:
        return execution_plan

    current_step = execution_state.get("current_step")

    new_plan = []

    for step in execution_plan:

        # 🔥 FORCE AI ON CURRENT STEP (BETTER THAN INDEX)
        if step == current_step:
            new_plan.append(generate_better_step(step))
        else:
            new_plan.append(step)

    return new_plan