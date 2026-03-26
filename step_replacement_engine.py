from ai_step_engine import generate_better_step


def replace_failed_step(execution_plan, execution_state, step_decision):

    if not execution_plan:
        return execution_plan

    new_plan = []

    for step in execution_plan:

        # 🔥 FORCE AI FOR TESTING (NO CONDITION)
        new_plan.append(generate_better_step(step))

    return new_plan