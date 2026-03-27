def generate_execution_sequence(best_decision):

    t = best_decision.lower().strip()

    # Supplier flow (RAW + SIMPLE)
    if "supplier" in t:
        return [
            "Check supplier pricing",
            "Negotiate price",
            "Check sample quality",
            "Finalize supplier"
        ]

    # Product flow (RAW + SIMPLE)
    if "product" in t:
        return [
            "Check product specs",
            "Verify quality",
            "Finalize product"
        ]

    # Default fallback (KEEP RAW)
    return [
        best_decision.strip()
    ]