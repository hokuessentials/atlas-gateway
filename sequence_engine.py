def generate_execution_sequence(best_decision):

    t = best_decision.lower()

    # Supplier flow
    if "supplier" in t:
        return [
            "Check supplier pricing",
            "Negotiate better terms",
            "Confirm sample quality",
            "Finalize supplier deal"
        ]

    # Product flow
    if "product" in t:
        return [
            "Validate product specs",
            "Check quality standards",
            "Finalize product version"
        ]

    # Default fallback
    return [
        best_decision
    ]