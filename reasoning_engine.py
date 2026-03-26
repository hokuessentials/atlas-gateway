def generate_reason(last_decision, best_decision, last_outcome):

    if last_outcome == "failed":
        return f"Previous decision '{last_decision}' failed, switching to '{best_decision}' to improve outcome and avoid repeated failure"

    if "supplier" in best_decision.lower():
        return f"Prioritizing supplier-related action '{best_decision}' to improve cost, margin, or sourcing stability"

    if "finalize" in best_decision.lower():
        return f"Moving toward execution by finalizing '{best_decision}' to secure business progress"

    if "test" in best_decision.lower() or "random" in best_decision.lower():
        return f"Avoiding low-impact task '{best_decision}' in favor of more meaningful action"

    return f"Selecting '{best_decision}' as it offers better expected outcome compared to current decision"