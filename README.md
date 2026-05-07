# 📦 EaseCargo — Smart Container Space Matching Platform

> Connecting small and medium exporters with unused cargo capacity worldwide.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1-green?style=flat-square&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-blue?style=flat-square&logo=sqlite)

---

## 🎯 Overview

EaseCargo is a full-stack logistics platform that enables exporters to discover and book unused capacity in partially-filled cargo shipments. The system provides:

- **Route-based shipment discovery** with city autocomplete and nearby alternatives
- **AI-powered smart matching** using explainable Fuzzy Logic (scikit-fuzzy)
- **Real-time 2D tracking** with Leaflet + OpenStreetMap
- **Sustainability metrics** tracking CO₂ savings from space sharing
- **10,000 synthetic shipments** across 50 global cities and 4 transport modes

## 🚀 Quick Start

### Recommended (Docker Compose)

Prerequisite:
- Docker Desktop

Run:

```bash
docker-compose up -d --build
docker-compose logs -f easecargo
```

Open **http://localhost:5000** in your browser.

Notes:
- The database is auto-seeded from CSV on first launch.
- A locked baseline snapshot is kept at `instance/easecargo.seed.db`.
- The runtime DB remains writable at `instance/easecargo.db` for bookings/tracking updates.

### Local Python Run (Alternative)

```bash
pip install -r requirements.txt
python data/generate_shipments.py
python app.py
```

## 📐 Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    FRONTEND (Browser)                     │
│  Landing │ Discover │ Smart Match │ Tracking │ Dashboard │
│                      ▲  REST API  ▲                      │
└──────────────────────┼────────────┼──────────────────────┘
                       │            │
┌──────────────────────┼────────────┼──────────────────────┐
│                  BACKEND (Flask/Python)                    │
│  Routes (REST) │ Fuzzy Engine │ Models (SQLAlchemy)       │
│                       │                                   │
│              SQLite Database + CSV/JSON Data              │
└──────────────────────────────────────────────────────────┘
```

## 💻 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Flask 3.1 + Python |
| Database | SQLite + SQLAlchemy |
| Recommendation | scikit-fuzzy (Fuzzy Logic) |
| 2D Maps | Leaflet + OpenStreetMap |
| Data | 10K synthetic CSV + JSON coordinates |
| Frontend | HTML/CSS/JS (no framework) |

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cities` | List all cities with coordinates |
| GET | `/api/cities/nearby?city=X&radius=500` | Find nearby cities |
| GET | `/api/shipments?source=X&destination=Y&mode=Z&page=1` | Filter shipments |
| GET | `/api/shipments/stats` | Aggregate statistics |
| GET | `/api/transport-modes` | Available transport modes |
| POST | `/api/recommend` | Fuzzy logic recommendations |
| POST | `/api/bookings` | Create booking (reduces capacity) |
| GET | `/api/bookings` | List all bookings |
| GET | `/api/tracking/{id}` | Simulated tracking data |
| GET | `/api/sustainability` | Environmental impact metrics |

## 🧠 Fuzzy Logic Engine

The recommendation engine uses **scikit-fuzzy** with three input variables:

1. **Capacity Fit** (0-100): How well remaining capacity matches cargo weight
2. **Cost Efficiency** (0-100): Relative cost ranking
3. **Urgency** (0-100): Timeline match

The engine applies human-readable rules (e.g., *"good capacity + cheap cost = excellent match"*) and produces an explainable score with reasons.

## 🔭 Future Scope

- Reintroduce a 3D globe visualization when global route storytelling becomes an active product requirement.

## 📁 Project Structure

```
EaseCargo/
├── app.py                  # Flask application factory
├── config.py               # Configuration
├── models.py               # SQLAlchemy models
├── routes.py               # REST API endpoints
├── fuzzy_engine.py         # Fuzzy logic recommendation engine
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── data/
│   ├── generate_shipments.py   # Synthetic data generator
│   ├── shipments.csv           # 10,000 shipment records
│   └── city_coordinates.json   # 50 city coordinates
├── static/
│   ├── index.html          # Landing page
│   ├── discover.html       # Shipment discovery
│   ├── recommend.html      # Smart matching
│   ├── tracking.html       # 2D map tracking
│   ├── dashboard.html      # Analytics dashboard
│   ├── about.html          # Architecture & docs
│   ├── css/style.css       # Design system
│   └── js/common.js        # Shared utilities
└── instance/
    └── easecargo.db        # SQLite database (auto-created)
```

## 🔒 Constraints

- ❌ No paid services or APIs
- ❌ No Google Maps / Mapbox paid tiers
- ❌ No real user data (all synthetic)
- ❌ No cloud dependency
- ✅ 100% open-source
- ✅ Runs fully offline after initial asset load

## 📝 License

Academic research project. All rights reserved.
