def decide_step_action(current_step, step_updates):

    if not current_step:
        return {
            "decision": "no_action",
            "reason": "No current step",
            "decision_quality": "low",
            "decision_score": 0.0
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
    # LEVEL 3 — PHASE 6 LOGIC
    # =========================

    decision = None
    reason = ""
    quality = "low"
    score = 0.2  # default for continue

    # STRONG FAILURE → IMPROVE (HIGH)
    if failure_count >= 2:
        decision = "improve"
        reason = "Multiple failures, improve step"
        quality = "high"
        score = 0.9

    # SINGLE FAILURE
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

    # NO FAILURE
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

    # 🔴 PRESSURE ADJUSTMENT
    if attempt_count >= 4:
        score += 0.05

    # CAP SCORE
    score = min(score, 1.0)

    return {
        "decision": decision,
        "reason": reason,
        "decision_quality": quality,
        "decision_score": round(score, 2)
    }