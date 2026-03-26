from ai_step_engine import generate_better_step


def replace_failed_step(execution_plan, execution_state, step_decision):

    if not execution_plan:
        return execution_plan

    new_plan = []

    for i, step in enumerate(execution_plan):

        # 🔥 FORCE AI on second step (index 1)
        if i == 1:
            new_plan.append(generate_better_step(step))
        else:
            new_plan.append(step)

    return new_plan