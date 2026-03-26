def estimate_success_probability(title, decisions, outcomes):

    total = 0
    success = 0

    for i in range(len(decisions)):
        if str(decisions[i]) == title:
            total += 1

            outcome = str(outcomes[i]).strip().lower() if i < len(outcomes) else ""

            if outcome == "success":
                success += 1

    if total == 0:
        return 0.5  # neutral probability

    return success / total