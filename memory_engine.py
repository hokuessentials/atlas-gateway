def build_failure_memory(decisions, outcomes):

    failure_count = {}

    for i in range(len(decisions)):
        outcome = str(outcomes[i]).strip().lower() if i < len(outcomes) else ""

        if outcome == "failed":
            title = str(decisions[i])
            failure_count[title] = failure_count.get(title, 0) + 1

    return failure_count