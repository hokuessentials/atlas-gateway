def decide_step_action(current_step, step_updates):

    # =========================
    # 🧠 BUILD MEMORY
    # =========================
    total = len(step_updates)

    success_count = sum(
        1 for s in step_updates if s.get("status") == "success"
    )

    failure_count = sum(
        1 for s in step_updates if s.get("status") == "failed"
    )

    retry_count = sum(
        1 for s in step_updates
        if s.get("step", "").strip().lower() == current_step.strip().lower()
    )

    success_rate = success_count / total if total > 0 else 0
    failure_rate = failure_count / total if total > 0 else 0

    # =========================
    # 🎯 DECISION SCORE
    # =========================
    score = 0

    score += success_rate * 5
    score -= failure_rate * 7
    score -= retry_count * 2

    # normalize
    decision_score = max(0, min(1, (score + 5) / 10))

    # =========================
    # 🧠 DECISION LOGIC
    # =========================
    if failure_rate > 0.5:
        decision = "hold"
        execution_action = "hold"
        reason = "High failure rate detected"
    else:
        decision = "proceed"
        execution_action = "execute"
        reason = "Healthy execution flow"

    # =========================
    # 📊 METRICS
    # =========================
    metrics = {
        "success_rate": round(success_rate, 2),
        "failure_rate": round(failure_rate, 2),
        "retry_count": retry_count
    }

    return {
        "decision": decision,
        "execution_action": execution_action,
        "decision_score": round(decision_score, 2),
        "decision_quality": "execution",
        "reason": reason,
        "metrics": metrics
    }