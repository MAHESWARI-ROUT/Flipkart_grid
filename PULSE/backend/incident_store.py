import json
import os
import uuid
from datetime import datetime

FILE = "incidents.json"

# Seconds window within which identical incident_type + corridor + severity
# is treated as a duplicate and NOT saved again.
_DEDUP_WINDOW_SECONDS = 10


def _is_duplicate(incidents: list, data: dict) -> bool:
    """Return True if the last saved incident looks identical to data
    and was created within the dedup window."""
    if not incidents:
        return False
    last = incidents[-1]
    try:
        last_time = datetime.strptime(last["timestamp"], "%d-%b-%Y %H:%M")
        now = datetime.now()
        diff = (now - last_time).total_seconds()
    except Exception:
        return False

    return (
        diff <= _DEDUP_WINDOW_SECONDS
        and last.get("incident_type") == data.get("incident_type")
        and last.get("corridor") == data.get("corridor")
        and last.get("severity") == data.get("severity")
    )


def save_incident(data):
    incidents = []

    if os.path.exists(FILE):
        try:
            with open(FILE, "r") as f:
                incidents = json.load(f)
        except Exception:
            incidents = []

    # --- dedup guard ---
    if _is_duplicate(incidents, data):
        return  # silently skip — same incident submitted twice quickly

    data["id"] = str(uuid.uuid4())
    data["timestamp"] = datetime.now().strftime("%d-%b-%Y %H:%M")

    incidents.append(data)

    with open(FILE, "w") as f:
        json.dump(incidents, f, indent=2)


def load_incidents():
    if not os.path.exists(FILE):
        return []

    with open(FILE, "r") as f:
        return json.load(f)
