from ai_step_engine import generate_better_step


def replace_failed_step(execution_plan, execution_state, step_decision):

    if not execution_plan:
        return execution_plan

    new_plan = []

    current_step = execution_state.get("current_step", "")

    for step in execution_plan:

        # ✅ ONLY IMPROVE CURRENT STEP
        if step == current_step:

            # ✅ GUARD: skip already optimized steps
            if len(step.split()) < 6 or "improve execution" in step.lower():
                new_plan.append(step)
            else:
                improved_step = generate_better_step(step)
                new_plan.append(improved_step)

        else:
            # ✅ keep other steps unchanged
            new_plan.append(step)

    return new_plan