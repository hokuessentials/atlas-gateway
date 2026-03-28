def build_failure_memory(decisions, outcomes):

    failure_count = {}

    for i in range(len(decisions)):
        outcome = str(outcomes[i]).strip().lower() if i < len(outcomes) else ""

        if outcome == "failed":
            title = str(decisions[i])
            failure_count[title] = failure_count.get(title, 0) + 1

    return failure_count

def save_session_to_sheet(session_data):

    payload = {
        "action": "save_session",
        "data": session_data
    }

    try:
        resp = requests.post(APPS_SCRIPT_URL, json=payload, timeout=10)
        print("🔥 SESSION SAVE:", resp.text)
    except Exception as e:
        print("❌ SESSION SAVE ERROR:", e) 