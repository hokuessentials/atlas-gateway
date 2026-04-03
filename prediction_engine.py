def estimate_success_probability(title, decisions, outcomes):

    if not decisions or not isinstance(decisions, list):
        return 0.5

    if not outcomes or not isinstance(outcomes, list):
        return 0.5

    total = 0
    success = 0

    for i in range(len(decisions)):
        if str(decisions[i]).strip().lower() == str(title).strip().lower():
            total += 1

            outcome = str(outcomes[i]).strip().lower() if i < len(outcomes) else ""

            if outcome == "success":
                success += 1

    if total == 0:
        return 0.5

    prob = success / total
    prob = max(min(prob, 0.9), 0.1)

    return prob