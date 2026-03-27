def decide_step_action(current_step, step_updates):

    if not current_step:
        return {
            "decision": "no_action",
            "reason": "No current step",
            "decision_quality": "low",
            "decision_score": 0.0,
            "decision_flag": "weak",
            "decision_filter": "review",
            "execution_action": "hold",
            "context_signal": "fresh",
            "flow_signal": "stable"
        }

    step_updates = step_updates or []

    relevant_updates = [
        u for u in step_updates
        if u.get("step") == current_step
    ]

    failure_count = sum(
        1 for u in relevant_updates
        if u.get("status") == "failed"
    )

    attempt_count = len(relevant_updates)

    # =========================
    # BASE DECISION LOGIC
    # =========================

    decision = None
    reason = ""
    quality = "low"
    score = 0.2

    if failure_count >= 2:
        decision = "improve"
        reason = "Multiple failures, improve step"
        quality = "high"
        score = 0.9

    elif failure_count == 1:
        if attempt_count >= 3:
            decision = "improve"
            reason = "Failure with repeated attempts, improving step"
            quality = "medium"
            score = 0.75
        else:
            decision = "retry"
            reason = "Single failure, retry step"
            quality = "low"
            score = 0.4

    else:
        if attempt_count >= 4:
            decision = "improve"
            reason = "Too many attempts without success, improving step"
            quality = "low"
            score = 0.6
        else:
            decision = "continue"
            reason = "Execution stable, continue"
            quality = "low"
            score = 0.2

    if attempt_count >= 4:
        score += 0.05

    score = min(score, 1.0)

    if score >= 0.85:
        flag = "strong"
    elif score >= 0.6:
        flag = "normal"
    else:
        flag = "weak"

    # =========================
    # CONTEXT SIGNAL
    # =========================

    if failure_count == 0 and attempt_count <= 1:
        context = "fresh"
    elif failure_count == 0 and attempt_count >= 2:
        context = "progressing"
    elif failure_count >= 1 and attempt_count <= 2:
        context = "recovering"
    else:
        context = "stuck"

    # =========================
    # FLOW SIGNAL
    # =========================

    if attempt_count >= 3:
        last_three = relevant_updates[-3:]
        if len(last_three) == 3 and all(u.get("step") == current_step for u in last_three):
            flow = "looping"
        else:
            flow = "stable"
    else:
        flow = "stable"

    if failure_count == 0 and attempt_count >= 4:
        flow = "stagnant"

    if failure_count >= 2 and attempt_count >= 3:
        flow = "volatile"

    # =========================
    # CONTEXT INFLUENCE
    # =========================

    if context == "recovering" and decision == "improve" and flag == "weak":
        decision = "retry"
        reason = "Recovering state, reducing aggressive improvement"

    elif context == "stuck" and decision == "continue":
        decision = "improve"
        reason = "Stuck state detected, forcing improvement"

    elif context == "progressing" and decision == "improve" and flag == "weak":
        decision = "continue"
        reason = "Progressing state, avoiding unnecessary improvement"

    # =========================
    # FLOW INFLUENCE (NEW)
    # =========================

    if flow == "looping" and decision == "retry":
        decision = "improve"
        reason = "Looping detected, forcing improvement"

    elif flow == "stagnant" and decision == "continue":
        decision = "improve"
        reason = "Stagnant flow detected, forcing improvement"

    elif flow == "volatile" and decision == "improve" and flag == "weak":
        decision = "retry"
        reason = "Volatile flow, reducing aggressive improvement"

    # =========================
    # PHASE 8 (FIXED)
    # =========================

    if flag == "weak":

        if decision == "retry" and context != "recovering":
            decision = "improve"
            reason = "Weak retry detected, upgrading to improve"

        elif decision == "continue" and attempt_count >= 3:
            decision = "improve"
            reason = "Weak continue with repeated attempts, improving step"

    # FILTER
    if flag == "weak" and decision in ["improve", "continue"]:
        decision_filter = "review"
    else:
        decision_filter = "pass"

    # EXECUTION CONTROL
    if flag == "strong":
        execution_action = "proceed"
    elif flag == "normal":
        execution_action = "proceed"
    elif flag == "weak" and decision_filter == "review":
        execution_action = "hold"
    else:
        execution_action = "proceed"

    return {
        "decision": decision,
        "reason": reason,
        "decision_quality": quality,
        "decision_score": round(score, 2),
        "decision_flag": flag,
        "decision_filter": decision_filter,
        "execution_action": execution_action,
        "context_signal": context,
        "flow_signal": flow
    }