from ai_step_engine import generate_better_step


def replace_failed_step(execution_plan, execution_state, step_decision):

    if not execution_plan:
        return execution_plan

    new_plan = []

    current_step = execution_state.get("current_step", "")
    decision = (step_decision or {}).get("decision", "").lower()

    for step in execution_plan:

        # ✅ STRICT CONDITION
        if step == current_step and decision in ["retry", "failed"]:

            print("🔥 AI TRIGGERED FOR STEP:", step)
            print("STEP:", step)
            print("CURRENT:", current_step)
            print("DECISION:", decision)

            # loop protection
            if "improve execution" in step.lower():
                new_plan.append(step)
            else:
                improved_step = generate_better_step(step)
                new_plan.append(improved_step)

        else:
            new_plan.append(step)

    return new_plan