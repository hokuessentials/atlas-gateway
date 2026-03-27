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

    updates = [u for u in (step_updates or []) if u.get("step") == current_step]
    failure_count = sum(1 for u in updates if u.get("status") == "failed")
    attempt_count = len(updates)

    # =========================
    # BASE DECISION
    # =========================

    if failure_count >= 2:
        decision, reason, quality, score = "improve", "Multiple failures, improve step", "high", 0.9
    elif failure_count == 1:
        if attempt_count >= 3:
            decision, reason, quality, score = "improve", "Failure with repeated attempts, improving step", "medium", 0.75
        else:
            decision, reason, quality, score = "retry", "Single failure, retry step", "low", 0.4
    else:
        if attempt_count >= 4:
            decision, reason, quality, score = "improve", "Too many attempts without success, improving step", "low", 0.6
        else:
            decision, reason, quality, score = "continue", "Execution stable, continue", "low", 0.2

    score = min(score + (0.05 if attempt_count >= 4 else 0), 1.0)

    flag = "strong" if score >= 0.85 else "normal" if score >= 0.6 else "weak"

    # =========================
    # CONTEXT
    # =========================

    if failure_count == 0 and attempt_count <= 1:
        context = "fresh"
    elif failure_count == 0:
        context = "progressing"
    elif attempt_count <= 2:
        context = "recovering"
    else:
        context = "stuck"

    # =========================
    # FLOW
    # =========================

    if failure_count >= 2 and attempt_count >= 3:
        flow = "volatile"
    elif failure_count == 0 and attempt_count >= 4:
        flow = "stagnant"
    elif attempt_count >= 3:
        flow = "looping"
    else:
        flow = "stable"

    # =========================
    # CONTEXT INFLUENCE
    # =========================

    if context == "recovering" and decision == "improve" and flag == "weak":
        decision, reason = "retry", "Recovering state, reducing aggressive improvement"
    elif context == "stuck" and decision == "continue":
        decision, reason = "improve", "Stuck state detected, forcing improvement"
    elif context == "progressing" and decision == "improve" and flag == "weak":
        decision, reason = "continue", "Progressing state, avoiding unnecessary improvement"

    # =========================
    # FLOW INFLUENCE
    # =========================

    if flow == "looping" and decision == "retry":
        decision, reason = "improve", "Looping detected, forcing improvement"
    elif flow == "stagnant" and decision == "continue":
        decision, reason = "improve", "Stagnant flow detected, forcing improvement"
    elif flow == "volatile" and decision == "improve" and flag == "weak":
        decision, reason = "retry", "Volatile flow, reducing aggressive improvement"

    # =========================
    # PHASE 8 (SAFE)
    # =========================

    if flag == "weak":
        if decision == "retry" and context != "recovering":
            decision, reason = "improve", "Weak retry detected, upgrading to improve"
        elif decision == "continue" and attempt_count >= 3:
            decision, reason = "improve", "Weak continue with repeated attempts, improving step"

    # =========================
    # FILTER + EXECUTION
    # =========================

    decision_filter = "review" if flag == "weak" and decision in ["improve", "continue"] else "pass"
    execution_action = "hold" if flag == "weak" and decision_filter == "review" else "proceed"

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