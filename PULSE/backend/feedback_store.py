import json
import os

FILE = "feedback.json"

def save_feedback(data):
    records = []

    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            records = json.load(f)

    records.append(data)

    with open(FILE, "w") as f:
        json.dump(records, f, indent=2)

def load_feedback():
    if not os.path.exists(FILE):
        return []

    with open(FILE, "r") as f:
        return json.load(f)
    
def calculate_feedback_stats():

    data = load_feedback()

    if not data:
        return {
            "events_reviewed": 0,
            "diversion_success_rate": 0,
            "prediction_accuracy": 0,
            "resource_accuracy": 0
        }

    diversion_success = sum(
        1 for x in data if x["diversion_effective"]
    )

    severity_matches = sum(
        1 for x in data
        if x["predicted_severity"].lower()
        == x["actual_severity"].lower()
    )

    resource_matches = sum(
        1 for x in data
        if abs(
            x["officers_deployed"]
            - x.get("officers_recommended", x["officers_deployed"])
        ) <= 1
    )

    total = len(data)

    return {
        "events_reviewed": total,
        "diversion_success_rate":
            round(diversion_success * 100 / total, 1),

        "prediction_accuracy":
            round(severity_matches * 100 / total, 1),

        "resource_accuracy":
            round(resource_matches * 100 / total, 1)
    }