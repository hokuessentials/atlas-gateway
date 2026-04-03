def apply_time_weight(index, total_length):
    """
    Gives higher weight to recent decisions
    """

    try:
        index = int(index)
        total_length = int(total_length)
    except:
        return 1

    if total_length <= 0:
        return 1

    if index < 0:
        index = 0

    if index >= total_length:
        index = total_length - 1

    position_factor = (index + 1) / total_length

    return 0.5 + position_factor