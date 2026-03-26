def apply_priority_boost(title):

    t = title.lower()

    boost = 0

    # HIGH IMPACT KEYWORDS
    if "finalize" in t:
        boost += 2

    if "deal" in t:
        boost += 1.5

    if "supplier" in t:
        boost += 1

    if "margin" in t:
        boost += 1

    # LOW VALUE TASKS
    if "test" in t or "random" in t:
        boost -= 1.5

    return boost