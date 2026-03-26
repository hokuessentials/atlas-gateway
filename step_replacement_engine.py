from ai_step_engine import generate_better_step


def replace_failed_step(execution_plan, execution_state, step_decision):

    current_step = execution_state.get("current_step")

    if not current_step or not execution_plan:
        return execution_plan

    new_plan = []

    for i, step in enumerate(execution_plan):

        # 🔥 replace ONLY first pending step (by position, not string)
        if i == len(execution_state.get("completed_steps", [])):
            new_plan.append(generate_better_step(step))
        else:
            new_plan.append(step)

    return new_plan