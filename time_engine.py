def apply_time_weight(index, total_length):
    """
    Gives higher weight to recent decisions
    """

    if total_length == 0:
        return 1

    # newer decisions get higher weight
    position_factor = (index + 1) / total_length

    # scale between 0.5 → 1.5
    return 0.5 + position_factor