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
            "context_signal": "fresh"
        }

    # SAFETY
    step_updates = step_updates or []

    # FAILURE COUNT
    failure_count = sum(
        1 for update in step_updates
        if update.get("step") == current_step and update.get("status") == "failed"
    )

    # ATTEMPT COUNT
    attempt_count = sum(
        1 for update in step_updates
        if update.get("step") == current_step
    )

    # =========================
    # BASE DECISION LOGIC (LEVEL 3)
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

    # FLAG
    if score >= 0.85:
        flag = "strong"
    elif score >= 0.6:
        flag = "normal"
    else:
        flag = "weak"

    # INFLUENCE
    if flag == "weak":
        if decision == "retry":
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

    # =========================
    # LEVEL 4 — CONTEXT SIGNAL
    # =========================

    if failure_count == 0 and attempt_count <= 1:
        context = "fresh"

    elif failure_count == 0 and attempt_count >= 2:
        context = "progressing"

    elif failure_count >= 1 and attempt_count <= 2:
        context = "recovering"

    else:
        context = "stuck"

    return {
        "decision": decision,
        "reason": reason,
        "decision_quality": quality,
        "decision_score": round(score, 2),
        "decision_flag": flag,
        "decision_filter": decision_filter,
        "execution_action": execution_action,
        "context_signal": context
    }