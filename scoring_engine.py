# ================================
# SCORING ENGINE
# ================================
def compute_decision_scores(session_data):

    decisions = session_data.get("decisions", [])[-5:]
    roi_list = session_data.get("roi_list", [])[-5:]
    risk_list = session_data.get("risk_list", [])[-5:]
    conf_list = session_data.get("confidence_list", [])[-5:]
    outcomes = session_data.get("outcome_list", [])[-5:]

    scored = []

    for i in range(len(decisions)):

        title = str(decisions[i])

        roi = float(roi_list[i]) if i < len(roi_list) else 0
        risk = float(risk_list[i]) if i < len(risk_list) else 0
        conf = float(conf_list[i]) if i < len(conf_list) else 0

        outcome = str(outcomes[i]).strip().lower() if i < len(outcomes) else ""

        success_weight = 1

        if outcome == "success":
            success_weight = 1.5
        elif outcome == "failed":
            success_weight = 0.2

        score = ((roi * conf) - risk) * success_weight

        scored.append({
            "title": title,
            "score": score
        })

    return scored

def select_best_decision(scored):
    if not scored:
        return None
    return sorted(scored, key=lambda x: x["score"], reverse=True)[0]