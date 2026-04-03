def apply_risk_penalty(title, risk_value):

    # base penalty from sheet
    try:
        penalty = float(risk_value)
    except:
        penalty = 0

    t = title.lower()

    # increase penalty for sensitive actions
    if "finalize" in t:
        penalty *= 1.2

    if "deal" in t:
        penalty *= 1.1

    penalty = min(penalty, 1)

    return penalty