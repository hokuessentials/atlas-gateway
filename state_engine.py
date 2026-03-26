import requests
import datetime
import json

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzE0aSjAWHgONC-GT4hFlMmq830hkMWsKR96Hla2yxOgzLhcPtNH-Ua3Llqjz9GAh5Xkg/exec"

# ================================
# ACTIVE STATE (MAIN MEMORY)
# ================================
ACTIVE_STATE = {
    "phase": "BUILD",
    "current_goal": {},
    "current_task": {},
    "next_best_action": {},
    "blockers": [],
    "focus_module": None,
    "execution_mode": "idle",
    "last_updated": None
}

# ================================
# STATE LOAD / SAVE
# ================================
def load_state():
    try:
        response = requests.get(APPS_SCRIPT_URL + "?action=get_state", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data:
                ACTIVE_STATE.update(data)
    except Exception as e:
        print("State load failed:", e)

def save_state():
    try:
        payload = {
            "action": "update_state",
            "data": ACTIVE_STATE
        }
        requests.post(APPS_SCRIPT_URL, json=payload, timeout=10)
    except Exception as e:
        print("State save failed:", e)

# ================================
# INTELLIGENT ACTION ENGINE
# ================================
def generate_intelligent_action(session_data):

    module_count = session_data.get("module_count", {})
    decisions = session_data.get("decisions", [])

    if not decisions:
        return {
            "action": "Start by logging a decision",
            "priority": "high",
            "reason": "No decisions found"
        }

    last_decision = decisions[-1]

    if not module_count:
        return {
            "action": f"Continue: {last_decision}",
            "priority": "medium",
            "reason": "No module context"
        }

    focus_module = max(module_count, key=module_count.get)

    # 🔥 MODULE INTELLIGENCE

    if focus_module == "Supplier":
        return {
            "action": "Contact supplier → confirm price → negotiate terms",
            "priority": "high",
            "reason": "Supplier workflow continuation"
        }

    elif focus_module == "Product":
        return {
            "action": "Finalize product specs → validate quality → prepare listing",
            "priority": "high",
            "reason": "Product development stage"
        }

    elif focus_module == "Finance":
        return {
            "action": "Update cost sheet → calculate margins → validate pricing",
            "priority": "high",
            "reason": "Financial validation"
        }

    elif focus_module == "Marketing":
        return {
            "action": "Plan creatives → launch ads → monitor performance",
            "priority": "high",
            "reason": "Marketing execution"
        }

    return {
        "action": f"Continue execution after: {last_decision}",
        "priority": "medium",
        "reason": "General workflow"
    }

# ================================
# EXECUTION MODE ENGINE
# ================================
def compute_execution_mode():

    if ACTIVE_STATE.get("blockers"):
        if len(ACTIVE_STATE["blockers"]) > 0:
            return "stuck"

    task = ACTIVE_STATE.get("current_task")

    if task and task.get("status") == "in_progress":
        return "active"

    if not task:
        return "idle"

    return "review"

# ================================
# MAIN STATE UPDATE
# ================================
def update_state(session_data, triggers):

    global ACTIVE_STATE

    # ================================
    # 🔹 1. RESET STATE
    # ================================
    ACTIVE_STATE["current_task"] = {}
    ACTIVE_STATE["focus_module"] = None
    ACTIVE_STATE["next_best_action"] = {}

    decisions = session_data.get("decisions", [])
    module_count = session_data.get("module_count", {})

    # ================================
    # 🔹 2. NO DATA → IDLE
    # ================================
    if not decisions:
        ACTIVE_STATE["execution_mode"] = "idle"
        ACTIVE_STATE["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return

    # ================================
    # 🔹 3. SET FOCUS MODULE (SAFE)
    # ================================
    if module_count:
        ACTIVE_STATE["focus_module"] = max(module_count, key=module_count.get)
    else:
        ACTIVE_STATE["focus_module"] = None  # fallback safety

    # ================================
    # 🔹 4. CREATE CURRENT TASK
    # ================================
    last_decision = decisions[-1]

    ACTIVE_STATE["current_task"] = {
        "task_id": f"T-{int(datetime.datetime.now().timestamp())}",
        "title": last_decision,
        "module": ACTIVE_STATE["focus_module"],
        "status": "in_progress",
        "priority": "high"
    }

    # ================================
    # 🔥 5. INTELLIGENT ACTION (SAFE)
    # ================================
    try:
        action = generate_intelligent_action(session_data)

        if not action:
            action = {
                "action": f"Continue: {last_decision}",
                "priority": "medium",
                "reason": "Fallback (empty intelligence)"
            }

        ACTIVE_STATE["next_best_action"] = action

    except Exception as e:
        print("⚠️ Intelligence error:", e)

        ACTIVE_STATE["next_best_action"] = {
            "action": f"Continue: {last_decision}",
            "priority": "medium",
            "reason": "Fallback (error)"
        }

    # ================================
    # 🔹 6. EXECUTION MODE
    # ================================
    ACTIVE_STATE["execution_mode"] = compute_execution_mode()

    # ================================
    # 🔹 7. TIMESTAMP
    # ================================
    ACTIVE_STATE["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ================================
# BLOCKER MANAGEMENT
# ================================
def add_blocker(description, impact="high"):
    ACTIVE_STATE["blockers"].append({
        "type": "manual",
        "description": description,
        "impact": impact
    })
    save_state()

def clear_blockers():
    ACTIVE_STATE["blockers"] = []
    save_state()

def complete_current_task():

    if not ACTIVE_STATE["current_task"]:
        return

    last_task = ACTIVE_STATE["current_task"]["title"]
    last_module = ACTIVE_STATE["current_task"]["module"]

    ACTIVE_STATE["current_task"] = {
        "task_id": f"T-{int(datetime.datetime.now().timestamp())}",
        "title": f"Next step after: {last_task}",
        "module": last_module,
        "status": "in_progress",
        "priority": "high"
    }

    ACTIVE_STATE["focus_module"] = last_module

    ACTIVE_STATE["next_best_action"] = {
        "action": f"Continue: {last_task}",
        "reason": "Auto continuation",
        "priority": "high"
    }

    ACTIVE_STATE["execution_mode"] = "active"
    ACTIVE_STATE["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_state()