def decide_step_action(current_step, step_updates):

    step_lower = current_step.strip().lower() if current_step else ""

    # =========================
    # 🧠 MEMORY ANALYSIS
    # =========================

    total = 0
    success = 0
    fail = 0

    for u in step_updates:
        if not isinstance(u, dict):
            continue

        if u.get("step", "").strip().lower() == step_lower:
            total += 1

            if u.get("status") == "success":
                success += 1
            elif u.get("status") == "failed":
                fail += 1

    success_rate = success / total if total > 0 else 0
    failure_rate = fail / total if total > 0 else 0

    retry_count = total

    # =========================
    # ⚙️ STRATEGY MODE (SAFE)
    # =========================

    STRATEGY = "SAFE"   # 🔥 your selected mode

    if STRATEGY == "SAFE":
        risk_weight = 1.5
        retry_limit = 2
    elif STRATEGY == "BALANCED":
        risk_weight = 1.0
        retry_limit = 3
    else:  # AGGRESSIVE
        risk_weight = 0.5
        retry_limit = 5

    # =========================
    # 🧠 DECISION LOGIC
    # =========================

    if failure_rate > 0.6 and retry_count >= retry_limit:
        decision = "hold"
        execution_action = "hold"
        reason = "High failure rate detected"

    elif failure_rate > 0.3:
        decision = "retry"
        execution_action = "continue"
        reason = "Moderate failure → retrying"

    else:
        decision = "proceed"
        execution_action = "execute"
        reason = "Healthy execution"

    # =========================
    # 📊 DYNAMIC SCORING
    # =========================

    score = (
        (success_rate * 5)
        - (failure_rate * 7 * risk_weight)
        - (retry_count * 0.5)
    )

    # normalize score
    score = max(0, min(1, score / 5))

    # =========================
    # 🎯 QUALITY LABEL
    # =========================

    if score > 0.75:
        quality = "high_confidence"
    elif score > 0.4:
        quality = "medium_confidence"
    else:
        quality = "low_confidence"

    # =========================
    # 🧠 FINAL OUTPUT
    # =========================

    return {
        "decision": decision,
        "execution_action": execution_action,
        "decision_score": round(score, 2),
        "decision_quality": quality,
        "reason": reason,
        "metrics": {
            "success_rate": round(success_rate, 2),
            "failure_rate": round(failure_rate, 2),
            "retry_count": retry_count
        }
    }