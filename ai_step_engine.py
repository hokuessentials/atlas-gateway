def generate_better_step(current_step):

    if not current_step:
        return current_step

    step = current_step.lower()

    # simple AI-like logic (expandable later)

    if "negotiate" in step:
        return "Collect multiple supplier quotes and renegotiate using best price comparison"

    if "check" in step:
        return "Validate supplier information with cross-checking and verification"

    if "confirm" in step:
        return "Verify product quality through samples and testing before confirmation"

    return f"Improve execution of: {current_step}"