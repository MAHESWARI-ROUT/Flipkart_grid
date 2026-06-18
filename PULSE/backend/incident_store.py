import json
import os
import uuid
from datetime import datetime

FILE = "incidents.json"

def save_incident(data):

    incidents = []

    if os.path.exists(FILE):
     try:
        with open(FILE, "r") as f:
            incidents = json.load(f)
     except:
        incidents = []

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