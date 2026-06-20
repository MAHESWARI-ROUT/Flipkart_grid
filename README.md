# PULSE — Predictive Urban Live Situation Engine

> **Flipkart Gridlock Hackathon 2026 · Event-Driven Congestion (Planned & Unplanned)**
>
> An AI-powered traffic intelligence platform for Bengaluru that predicts incident impact,
> recommends officer and barricade deployment, and generates smart diversion plans —
> before congestion cascades across the city.

---

## 🚀 Live Deployment

| | Link |
|---|---|
| **Frontend (Dashboard)** | https://pulse-alpha-two.vercel.app/ |
| **Backend (API)** | https://flipkart-grid-30ud.onrender.com |
| **API Docs (Swagger)** | https://flipkart-grid-30ud.onrender.com/docs |

---

## Live Dashboard

![PULSE Dashboard — Incident Impact Predictor] (DASHBOARD.png)
*PULSE live dashboard showing the Incident Impact Predictor: a Vehicle Breakdown on Airport New South Road at peak hour (18:00) returns HIGH severity, impact score 68, congestion risk 64.6/100, 77% prediction confidence, Smart Diversion recommendations, and a Resource & Action Plan of 5 officers + 3 barricades.*

---

## What is PULSE?

PULSE is a full-stack, ML-powered traffic management system trained on 8,173 real anonymised incidents from Bengaluru's ASTRAM monitoring network. It gives traffic operators a 5–30 minute head start on resource deployment by predicting incident severity, closure risk, and downstream congestion the moment an incident is reported — not after it has already spread.

---

## The Problem We Solve

Political rallies, cricket matches, festivals, construction, and sudden accidents create localised traffic breakdowns every single day across Bengaluru. Three gaps exist in how the city manages them today:

- **Event impact is not quantified in advance** — response teams deploy on gut feel
- **Resource deployment is experience-driven** — no data-backed officer or barricade allocation
- **No post-event learning system** — the same corridors get overwhelmed repeatedly

PULSE closes all three gaps.

---

## Key Numbers

| Metric | Value |
|---|---|
| Training records | 8,173 ASTRAM incidents |
| Corridors monitored | 22 major Bengaluru corridors |
| Junctions indexed | 294 |
| Hotspot clusters | 92 (K-Means on real GPS data) |
| Road closure model AUC | 0.7507 |
| Cause classifier accuracy | 71 % (11-class problem) |
| Prediction latency | < 10 ms |
| Critical events detected | 59 in training set |

---

## Features

### Incident Impact Predictor
The core of PULSE. Report any incident — vehicle breakdown, accident, procession, construction — and get an instant AI assessment:
- **Impact Score** (0–100) composite severity index
- **Severity Band** — CRITICAL / HIGH / MEDIUM / LOW with SLA timer
- **Congestion Risk Score** — downstream spillover likelihood
- **Road Closure Probability** — LightGBM Model B, AUC 0.7507
- **Prediction Confidence** — how strongly it matches historical patterns
- **Estimated vehicles affected** and delay in minutes

### Resource & Action Plan
Exact physical resources to deploy, derived from a cause-specific lookup table built on ASTRAM history:
- Officer count
- Barricade count
- Diversion required flag
- Step-by-step ordered action checklist

### Smart Diversion Generator
When road closure is predicted or toggled on, PULSE auto-generates corridor-specific alternate route recommendations — so dispatchers have an immediate plan, not a blank page.

### Spatial Intelligence Engine
Every prediction is enriched with three spatial features that go beyond a flat tabular model:

| Feature | What it measures |
|---|---|
| Junction Frequency | Historical incident count at this specific junction |
| Corridor Frequency | Incident density on this corridor vs all others |
| Hotspot Density | Cluster density at the nearest K-Means centroid |

### Hotspot Map
Interactive Leaflet map with all 92 cluster centroids across Bengaluru, colour-coded by risk level. Live predictions pin to the map in real time.

### Analytics Dashboard
- Hourly incident distribution (24-hour view)
- Top corridors by incident count and congestion risk
- Cause breakdown with average impact per cause type
- Top 8 high-frequency junctions
- Model performance metrics (AUC, accuracy, class balance)

### Event Planner
Pre-register planned events (festivals, rallies, sports matches) and receive an advance resource deployment plan before the event happens — directly answering the problem statement's first gap.

### Incident History
All session predictions are logged. Review predicted vs reported severity and export structured incident reports.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Async, auto-Swagger docs, Pydantic validation |
| ML | LightGBM 4.3 | Handles tabular imbalanced data; fast inference; native feature importance |
| ML | scikit-learn | Label encoding, K-Means clustering, preprocessing |
| Frontend | React 18 + Vite 5 | Component-driven; HMR makes iteration fast |
| Styling | Tailwind CSS 3.4 | Dark-mode utility classes; no CSS file bloat |
| Maps | Leaflet + React-Leaflet | Lightweight; works offline; no API key required |
| Charts | Recharts 2.12 | React-native charts; responsive out of the box |
| HTTP | Axios 1.7 | Promise-based with consistent error handling |
| Data | ASTRAM Bengaluru | Real anonymised incident data from live monitoring |

---

## Project Structure

```
Flipkart_Grid/
│
├── Astram event data_anonymized.csv      Training dataset (8,173 records)
├── final_training_model.py               ML pipeline (root-level copy)
│
└── PULSE/
    │
    ├── backend/
    │   ├── main.py                       FastAPI app + all API endpoints
    │   ├── predictor.py                  ML inference engine (315 lines)
    │   ├── requirements.txt              Python package dependencies
    │   └── models/                       All serialised ML artifacts [GENERATED]
    │       ├── closure_model.pkl         LightGBM road closure classifier
    │       ├── closure_features.pkl      Feature list for closure model
    │       ├── cause_model.pkl           LightGBM cause classifier (11 classes)
    │       ├── cause_features.pkl        Feature list for cause model
    │       ├── cause_severity.pkl        Cause → severity score mapping
    │       ├── cause_group_encoder.pkl   Cause group label encoder
    │       ├── encoders.pkl              LabelEncoders (corridor, zone, junction)
    │       ├── junction_freq_map.pkl     Junction-level incident frequency lookup
    │       ├── corridor_freq_map.pkl     Corridor-level incident frequency lookup
    │       ├── cluster_centers.pkl       92 K-Means hotspot cluster centroids
    │       ├── cluster_density_map.pkl   Incident density per cluster
    │       ├── cluster_stats.pkl         Per-cluster statistics
    │       ├── model_metadata.pkl        Training metadata + feature importance
    │       ├── hotspot_density_map.pkl   Lat/lon → hotspot density lookup
    │       ├── hotspot_encoder.pkl       Hotspot label encoder
    │       ├── hotspot_hour_encoder.pkl  Hotspot × hour encoder
    │       ├── junction_hour_encoder.pkl Junction × hour encoder
    │       ├── corridor_hour_encoder.pkl Corridor × hour encoder
    │       ├── hotspots.json             Hotspot GeoJSON for map rendering
    │       ├── dashboard_hotspots.json   Condensed hotspot data for analytics tab
    │       ├── resource_table.json       Cause → officers/barricades/diversion lookup
    │       └── feature_importance.json   LightGBM feature importance scores
    │
    ├── frontend/
    │   ├── index.html                    Root HTML (Vite entry point)
    │   ├── package.json                  Node.js dependencies
    │   ├── vite.config.js                Bundler config
    │   ├── tailwind.config.js            Tailwind CSS config
    │   ├── postcss.config.js             PostCSS config
    │   └── src/
    │       ├── App.jsx                   Root component + tab router
    │       ├── main.jsx                  React DOM mount point
    │       ├── index.css                 Global styles + Tailwind directives
    │       └── components/
    │           ├── IncidentForm.jsx      Input form + API call + submission handler
    │           ├── ResultCard.jsx        Impact score + severity band display
    │           ├── ResourcePanel.jsx     Officers / barricades / action checklist UI
    │           ├── Map.jsx               Leaflet map with 92 hotspot cluster pins
    │           └── Analytics.jsx         Recharts dashboard (hourly, corridors, causes)
    │
    └── ml/
        └── final_training_model.py       Complete ML training pipeline (1,087 lines)
                                          Reads:  Astram event data_anonymized.csv
                                          Writes: all .pkl and .json into backend/models/
```

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- The ASTRAM dataset CSV in the project root

---

### Step 1 — Train the ML Models *(run once)*

Skip if `PULSE/backend/models/` already has the `.pkl` files.

```bash
cd Flipkart_Grid
pip install pandas numpy scikit-learn lightgbm joblib
python final_training_model.py
```

Reads the ASTRAM CSV and writes all 18 `.pkl` + 3 `.json` model files into `PULSE/backend/models/`.
Takes roughly 2–5 minutes on a standard laptop.

---

### Step 2 — Start the Backend

```bash
cd PULSE/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend: https://flipkart-grid-30ud.onrender.com
API Docs: https://flipkart-grid-30ud.onrender.com/docs

---

### Step 3 — Start the Frontend

```bash
cd PULSE/frontend
npm install
npm run dev
```

Frontend: https://pulse-alpha-two.vercel.app/
The green **API Connected** badge in the top-right confirms the backend connection is live.

---

### Step 4 — Verify Everything Works

1. Open https://pulse-alpha-two.vercel.app/
2. Confirm the green **API Connected** badge is visible
3. On the **Predict** tab: select *Accident*, corridor *Mysore Road*, hour *08*, toggle Road Closure ON
4. Click **Predict Impact & Get Resource Plan** — you should see CRITICAL severity, score 75+
5. Switch to **Hotspot Map** — 92 cluster pins should appear across Bengaluru
6. Switch to **Analytics** — hourly distribution and corridor risk charts should load

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check — used by frontend for the API status badge |
| `POST` | `/predict` | Main prediction — returns full impact report + resource plan |
| `GET` | `/hotspots` | All 92 hotspot cluster centroids for the Leaflet map |
| `GET` | `/analytics` | Pre-computed stats: corridors, causes, hourly distribution |
| `GET` | `/corridors` | List of all 22 monitored corridors |
| `GET` | `/zones` | List of all 11 city zones |

---

## Impact Score Formula

```
Impact Score  = (cause_severity × 5) + (road_closure × 20) + (is_major_corridor × 10) + (is_peak_hour × 5)
                Clamped to [0, 100]

Congestion Risk = (0.4 × impact) + (20 × is_peak) + (15 × is_major) + (10 × closure_flag)
                  Clamped to [0, 100]
```

Road closure is weighted most heavily (20 pts) because it has the largest real-world effect on traffic flow.
The formula is intentionally transparent — any operator can audit it without ML knowledge.

**Cause severity scores (domain-expert assigned, scale 1–10):**

| Cause | Severity | Cause | Severity |
|---|---|---|---|
| Public event / Procession | 10 | Accident | 9 |
| Rare event (VIP, protest) | 9 | Construction | 7 |
| Tree fall | 6 | Congestion | 5 |
| Water logging | 5 | Vehicle breakdown | 4 |
| Road conditions | 3 | Pot holes | 2 |

**Severity response SLAs:**
- CRITICAL (≥ 75) → respond within 5 minutes
- HIGH (≥ 50) → respond within 10 minutes
- MEDIUM (≥ 25) → respond within 20 minutes
- LOW (< 25) → respond within 30 minutes

---

## ML Model Details

| Model | Type | Task | Performance |
|---|---|---|---|
| Model A | Domain formula | Impact scoring | Expert-validated |
| Model B | LightGBM classifier | Road closure prediction | AUC 0.7507 |
| Model C | Rule-based | Priority labelling (HIGH / LOW) | Fully auditable |
| Model D | LightGBM classifier | Cause classification | 71 % (11 classes) |

**Training dataset breakdown:**
- Total records: 8,173 ASTRAM incidents
- Top cause: Vehicle breakdown — 4,896 incidents (59.9 %)
- Road closure events: ~8.3 % of dataset (imbalanced — handled in training)
- Corridors: 22 | Junctions: 294 | City zones: 11

---

## Troubleshooting

| Problem | Fix |
|---|---|
| API Offline badge showing | Backend not running — check Step 2, ensure port 8000 is free |
| `ModuleNotFoundError` on startup | `pip install -r requirements.txt` inside the backend folder |
| Model files missing error | Run `python final_training_model.py` first (Step 1) |
| CORS error in browser console | Ensure backend is on port 8000 exactly |
| Map not loading | Leaflet CSS loads from CDN — check internet connection |
| `npm install` fails | Use Node.js 18+, check with `node --version` |

---

*PULSE — Built for Bengaluru. Built for real.*
*Flipkart Gridlock Hackathon 2026 | Event-Driven Congestion Track*
