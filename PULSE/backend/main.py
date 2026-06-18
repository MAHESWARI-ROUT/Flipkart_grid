from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os, json
from predictor import load_models, predict, get_analytics
from fastapi.responses import FileResponse
from pdf_generator import generate_incident_pdf

app = FastAPI(
    title="PULSE API",
    description="PULSE — Predictive Urban Live Situation Engine for Bengaluru",
    version="2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

@app.on_event("startup")
def startup():
    load_models(MODEL_DIR)

# Request schema
class IncidentRequest(BaseModel):
    event_cause:            str             = Field(..., example="accident")
    event_type:             Optional[str]   = Field("unplanned", example="unplanned")
    requires_road_closure:  Optional[bool]  = Field(False)
    hour:                   int             = Field(..., ge=0, le=23, example=8)
    minute:                 Optional[int]   = Field(None, ge=0, le=59)
    month:                  Optional[int]   = Field(None, ge=1, le=12)
    latitude:               Optional[float] = Field(12.97, example=13.04)
    longitude:              Optional[float] = Field(77.59, example=77.52)
    corridor:               Optional[str]   = Field("Non-corridor")
    zone:                   Optional[str]   = Field("Unknown")
    junction:               Optional[str]   = Field("Unknown")
    # NEW: crowd-size bucket for event-attendance impact scoring
    expected_attendance:    Optional[str]   = Field(
        "lt_500",
        example="2000_5000",
        description="One of: lt_500, 500_2000, 2000_5000, 5000_10000, gt_10000",
    )

# Endpoints
@app.get("/")
def root():
    return {"message": "PULSE API v2", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
def predict_incident(req: IncidentRequest):
    try:
        return predict(req.dict())
    except AssertionError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")

@app.get("/hotspots")
def get_hotspots():
    path = os.path.join(MODEL_DIR, "hotspots.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="hotspots.json not found")
    with open(path) as f:
        return json.load(f)

@app.get("/analytics")
def analytics():
    return get_analytics()

@app.get("/corridors")
def corridors():
    return {
        "corridors": [
            "Non-corridor","Mysore Road","Bellary Road 1","Bellary Road 2",
            "Tumkur Road","Hosur Road","ORR North 1","ORR North 2",
            "Old Madras Road","Magadi Road","ORR East 1","ORR East 2",
            "ORR West 1","Bannerghata Road","West of Chord Road",
            "Airport New South Road","Varthur Road","Hennur Main Road",
            "Old Airport Road","CBD 1","CBD 2","IRR(Thanisandra road)"
        ]
    }

@app.get("/zones")
def zones():
    return {
        "zones": [
            "Central Zone 1","Central Zone 2","North Zone 1","North Zone 2",
            "South Zone 1","South Zone 2","East Zone 1","East Zone 2",
            "West Zone 1","West Zone 2","Unknown"
        ]}


@app.post("/export-report")
def export_report(req: IncidentRequest):

     result = predict(req.dict())

     

     pdf_data = {
    # Incident Inputs
    "Incident Type": req.event_cause,
    "Event Type": req.event_type,
    "Corridor": req.corridor,
    "Zone": req.zone,
    "Junction": req.junction,
    "Hour": req.hour,
    "Road Closure Reported": "Yes" if req.requires_road_closure else "No",

    # Prediction Outputs
    "Severity": result["severity"],
    "Impact Score": result["impact_score"],
    "Congestion Risk": f"{result['congestion_risk']}%",
    "Road Closure Probability": f"{result['road_closure_probability']}%",
    "Officers Required": result["officers_needed"],
    "Barricades Required": result["barricades_needed"],
    "Diversion Required": "Yes" if result["diversion_needed"] else "No",
    "Estimated Delay": f"{result['estimated_delay_mins']} mins",
    "Vehicles Affected": result["vehicles_affected_est"],

    # Explainability
    "Prediction Drivers": result["prediction_drivers"],
    "Prediction Explanation": result["prediction_explanation"],

    # Actions
    "Actions": result["actions"],

    # Spatial Intelligence
    "Junction Frequency": result["junction_freq"],
    "Corridor Frequency": result["corridor_freq"],
    "Hotspot Density": result["hotspot_density"]
}

     output_file = "incident_report.pdf"

     generate_incident_pdf(
        pdf_data,
        output_file
    )

     return FileResponse(
        output_file,
        media_type="application/pdf",
        filename="incident_report.pdf"
    )
    
