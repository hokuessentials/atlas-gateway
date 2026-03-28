from memory_engine import build_failure_memory
from time_engine import apply_time_weight
from priority_engine import apply_priority_boost
from prediction_engine import estimate_success_probability
from risk_engine import apply_risk_penalty

def compute_decision_scores(session_data):

    decisions = session_data.get("decisions", [])[-5:]
    roi_list = session_data.get("roi_list", [])[-5:]
    risk_list = session_data.get("risk_list", [])[-5:]
    conf_list = session_data.get("confidence_list", [])[-5:]
    outcomes = session_data.get("outcome_list", [])[-5:]

    scored = []
    failure_count = build_failure_memory(decisions, outcomes)

    for i in range(len(decisions)):

        title = str(decisions[i])

        roi = float(roi_list[i]) if i < len(roi_list) else 0
        risk = float(risk_list[i]) if i < len(risk_list) else 0
        conf = float(conf_list[i]) if i < len(conf_list) else 0
        risk = apply_risk_penalty(title, risk)
        
        outcome = str(outcomes[i]).strip().lower() if i < len(outcomes) else ""
        prob = estimate_success_probability(title, decisions, outcomes)

        success_weight = 1

        if outcome == "success":
            success_weight = 1.5
        elif outcome == "failed":
            success_weight = 0.2

        # NORMALIZED WEIGHTED SCORE

        roi_weight = 0.4
        conf_weight = 0.3
        risk_weight = 0.3

        normalized_roi = min(roi / 20, 1)
        normalized_conf = conf
        normalized_risk = risk

        base_score = (
            (normalized_roi * roi_weight) +
            (normalized_conf * conf_weight) -
            (normalized_risk * risk_weight)
        )

        fail_penalty = failure_count.get(title, 0)

        if fail_penalty > 0:
           base_score *= (1 / (1 + fail_penalty))
        
        time_weight = apply_time_weight(i, len(decisions))

        priority_boost = apply_priority_boost(title)

        raw_score = (base_score * success_weight * time_weight * prob) + priority_boost

        # soft normalization instead of hard clipping
        score = raw_score / (1 + abs(raw_score))

        scored.append({
            "title": title,
            "score": round(score, 2)
        })

    return scored

def select_best_decision(scored):
    if not scored:
        return None
    return sorted(scored, key=lambda x: x["score"], reverse=True)[0]