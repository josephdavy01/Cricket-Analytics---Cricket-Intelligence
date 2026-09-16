# 🏏 Cricket Analytics & Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-017CEE?style=for-the-badge&logo=apache-airflow&logoColor=white)](https://airflow.apache.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)

An end-to-end **Cricket Intelligence & Analytics Platform** combining automated data engineering pipelines, ball-by-ball PostgreSQL data warehousing, machine learning win-probability models, a high-performance **FastAPI** backend, and an interactive **Django** dashboard.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Database Schema & Analytics Views](#-database-schema--analytics-views)
- [Machine Learning Pipeline](#-machine-learning-pipeline)
- [API Reference](#-api-reference)
- [Installation & Getting Started](#-installation--getting-started)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Clone & Environment Setup](#2-clone--environment-setup)
  - [3. Database Setup](#3-database-setup)
  - [4. Data Ingestion Pipeline](#4-data-ingestion-pipeline)
  - [5. Machine Learning Training](#5-machine-learning-training)
  - [6. Running Backend & Frontend](#6-running-backend--frontend)
- [Airflow Orchestration](#-airflow-orchestration)
- [Contributing & License](#-contributing--license)

---

## 🌟 Overview

The **Cricket Analytics Platform** automates the ingestion, transformation, analysis, and predictive modeling of International T20 (T20I) and franchise cricket data:

1. **Automated Scraping & Ingestion**: Crawls player career statistics and profiles from ESPNcricinfo using anti-bot bypass mechanisms (`nodriver`) alongside Cricsheet ball-by-ball JSON match logs.
2. **Scalable Data Pipeline**: Orchestrated with **Apache Airflow** in Docker, transforming unstructured and semi-structured logs into normalized relational tables and materialized statistical views in **PostgreSQL**.
3. **Machine Learning Win Predictor**: Random Forest ML model trained on 29+ engineered features (form, head-to-head, venue dynamics, toss impact, and player matchup matrices) to compute dynamic win probabilities.
4. **Interactive Intelligence Dashboard**: Django-based web interface offering deep-dive player profiles, pitch/venue analytics, batter vs. bowler faceoff matrices, playing XI simulators, and match outcome predictions.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Data_Engineering["1. Data Sourcing & Ingestion"]
        A1[ESPNcricinfo Squads & Profiles] -->|nodriver / Headless Chrome| S1[step1.py & step2.py]
        A2[Cricsheet Ball-by-Ball JSONs] --> S3[step3.py / Ingestion Engine]
        S1 --> S3
        AF[Apache Airflow DAGs] -->|Orchestrates| S1
        AF -->|Orchestrates| S3
    end

    subgraph Storage["2. Data Warehouse (PostgreSQL)"]
        S3 --> DB[(PostgreSQL)]
        DB --> T1[players, matches, deliveries]
        DB --> T2[Analytical & Aggregation Views]
        DB --> T3[ml_training_dataset_v2]
    end

    subgraph ML_Layer["3. Machine Learning & Modeling"]
        T3 --> TR[train_final_model.py]
        TR --> MDL[t20i_prediction_model.joblib]
        MDL --> PRE[predict_match.py]
    end

    subgraph Service_Layer["4. Backend Service (FastAPI)"]
        DB --> API[FastAPI REST API /api]
        PRE --> API
        API --> R1[/api/dashboard]
        API --> R2[/api/players]
        API --> R3[/api/matchups]
        API --> R4[/api/teams & /api/venues]
        API --> R5[/api/predict]
    end

    subgraph Client_Layer["5. Frontend Interface (Django)"]
        API --> DJ[Django Web Application]
        DJ --> UI1[Analytics Dashboard]
        DJ --> UI2[Player Career Profiles]
        DJ --> UI3[Head-to-Head & Matchups]
        DJ --> UI4[Playing XI Simulator]
        DJ --> UI5[Live Match Predictor]
    end
```

---

## ✨ Key Features

- **📊 Comprehensive Analytics Dashboard**: Real-time aggregation of top run scorers, leading wicket-takers, strike rates, economy rates, and venue scoring trends.
- **👤 In-depth Player Profiles**: Detailed career statistics, boundary rates, bowling economy by phase (powerplay, middle, death overs), and historical splits.
- **⚔️ Batter vs. Bowler Matchup Matrix**: Ball-by-ball historical face-off comparisons including strike rate, dismissals, dot ball percentage, and run distributions.
- **🏟️ Venue & Pitch Intelligence**: Win percentages by toss decision (batting first vs. chasing), average 1st innings score, boundary boundaries, and pace vs. spin effectiveness.
- **🔮 Match Outcome Predictor**: Machine learning model providing probabilistic win predictions based on squad selection, toss decision, venue history, and team momentum.
- **🛡️ Automated Data Scraping**: Resilient crawling pipeline with anti-detection capabilities to keep squads and player statistics updated.

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Data Ingestion & Scraping** | Python 3.10+, `nodriver` (undetected Chrome), `BeautifulSoup4`, `Xvfb` |
| **Pipeline Orchestration** | Apache Airflow 2.x, Docker Compose |
| **Database & Analytics** | PostgreSQL 14+, SQLAlchemy, Psycopg2 |
| **Machine Learning** | Scikit-Learn (RandomForestClassifier), Pandas, NumPy, Joblib |
| **Backend REST API** | FastAPI, Uvicorn, Pydantic, CORS Middleware |
| **Frontend Web App** | Django 4.x/5.x, HTML5, Vanilla CSS3 (Custom Design System), JavaScript |

---

## 📂 Project Structure

```text
Cricket/
├── backend/                             # FastAPI Backend Service
│   ├── routes/
│   │   ├── dashboard.py                 # Summary KPIs and dashboard feeds
│   │   ├── matchups.py                  # Batter vs Bowler head-to-head queries
│   │   ├── players.py                   # Player stats and profile endpoints
│   │   ├── predictions.py               # ML prediction endpoints & feature builders
│   │   ├── teams.py                     # Team win/loss & historical aggregates
│   │   └── venues.py                    # Venue dynamics & pitch statistics
│   ├── database.py                      # SQLAlchemy engine & session manager
│   ├── ipl_match_model.joblib           # Pre-trained match predictor artifact
│   ├── main.py                          # FastAPI entrypoint & router assembly
│   └── requirements.txt                 # Backend dependencies
│
├── frontend/                            # Django Web Application
│   ├── cricket/
│   │   ├── templates/cricket/           # UI Templates
│   │   │   ├── base.html                # Base layout & navigation
│   │   │   ├── dashboard.html           # Main analytics dashboard
│   │   │   ├── head_to_head.html        # Matchup explorer
│   │   │   ├── player_detail.html       # Player deep-dive page
│   │   │   ├── players.html             # Player directory & search
│   │   │   ├── playing_xi.html          # Team builder
│   │   │   ├── prediction.html          # Match win predictor UI
│   │   │   ├── team_vs_team.html        # Team vs Team rivalry analytics
│   │   │   ├── teams.html               # Teams overview
│   │   │   └── venues.html              # Venue statistics
│   │   ├── api_client.py                # FastAPI HTTP client service
│   │   ├── urls.py                      # Frontend routing
│   │   └── views.py                     # Django template views
│   ├── ipl_frontend/                    # Django project configuration
│   └── manage.py                        # Django management CLI
│
├── cricket_data_engineering/            # Airflow Pipeline & Docker configs
│   ├── dags/
│   │   ├── cricket_pipeline.py          # Airflow DAG definition
│   │   ├── step1.py                     # Team discovery & squad URLs scraper
│   │   ├── step2.py                     # Player profile scraper
│   │   └── step3.py                     # Database loading script
│   ├── docker-compose.yaml              # Multi-container Airflow setup
│   ├── Dockerfile                       # Custom Airflow worker image with Chrome
│   └── requirements.txt                 # Airflow custom dependencies
│
├── t20s_json/                           # Cricsheet match JSON data store
├── step1.py                             # Root scraper: squad & player URL discovery
├── step2.py                             # Root scraper: detailed player career stats
├── step3.py                             # Ingestion pipeline: players, matches, deliveries
├── database.sql                         # DDL schemas, constraints, and analytical SQL views
├── train_final_model.py                 # ML training script (V2 29-feature dataset)
├── predict_match.py                     # Standalone CLI match predictor
├── t20i_prediction_model.joblib         # Saved Random Forest model artifact
└── README.md
```

---

## 🗄️ Database Schema & Analytics Views

The database schema (`database.sql`) is organized into normalized transactional tables and high-performance analytical views:

### Core Tables
- `players`: Biographical data, playing role, batting/bowling style, career aggregates (runs, wickets, averages, SR, econ).
- `matches`: Match metadata, venue, city, teams, toss decisions, winner, margin, player of the match.
- `deliveries`: Ball-by-ball events, batter, bowler, non-striker, runs, extras, dismissals, dismissal types, and fielders.

### Key Analytical Views
- `player_t20_batting_stats`: Match innings aggregates, strike rates, 4s/6s count, milestone counts.
- `player_t20_bowling_stats`: Overs, maidens, wickets, runs conceded, dot balls, economy rate.
- `team_head_to_head_summary`: Historical wins, win percentages, and average scores per rivalry.
- `venue_statistics`: Batting first vs. chasing win rates, average par scores, highest chased targets.
- `ml_training_dataset_v2`: 29-feature rolling dataset synthesized for machine learning model training.

---

## 🤖 Machine Learning Pipeline

The prediction model estimates pre-match and innings win probabilities using a **Random Forest Classifier**:

### Feature Engineering Highlights (29 Features)
- **Team Quality Metrics**: Elo-based ratings, recent 5-match rolling win rates.
- **Head-to-Head Ratio**: Historic win-loss percentage between competing teams.
- **Venue Affinity**: Team win rate at the specific venue and pitch conditions.
- **Toss Advantage**: Match toss winner and elected decision (bat/field).
- **Squad Strength Indices**: Weighted average batting strike rates and bowling economy rates of the selected Playing XI.

### Retraining the Model

```bash
python train_final_model.py
```

Outputs the trained model artifact to `t20i_prediction_model.joblib`.

---

## 🔌 API Reference

The **FastAPI** backend exposes interactive OpenAPI docs at `http://localhost:8000/docs`.

| Endpoint | Method | Description |
|---|---|---|
| `/api/dashboard/stats` | `GET` | High-level tournament KPIs and overview metrics |
| `/api/players` | `GET` | List/search players with pagination and role filters |
| `/api/players/{player_id}` | `GET` | Complete career stats and phase breakdowns for a player |
| `/api/teams` | `GET` | List of teams and aggregate win statistics |
| `/api/teams/{team_name}/stats` | `GET` | Deep-dive performance analytics for a specific team |
| `/api/venues` | `GET` | Venue list with pitch statistics and chase metrics |
| `/api/matchups` | `GET` | Head-to-head statistics between a specific batter and bowler |
| `/api/predict` | `POST` | Computes match win probability given teams, venue, toss, and XIs |

---

## 🚀 Installation & Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **PostgreSQL 14+**
- **Docker & Docker Compose** (for Airflow, optional for standalone execution)
- **Google Chrome** (for scrapers)

---

### 2. Clone & Environment Setup

```bash
git clone https://github.com/josephdavy01/Cricket-Analytics---Cricket-Intelligence.git
cd Cricket-Analytics---Cricket-Intelligence

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

---

### 3. Database Setup

1. Start your local PostgreSQL server and create the database:
   ```sql
   CREATE DATABASE t20i_cricket_analytics;
   ```

2. Apply the schema and views:
   ```bash
   psql -U postgres -d t20i_cricket_analytics -f database.sql
   ```

---

### 4. Data Ingestion Pipeline

To populate the database from scratch:

```bash
# Step 1: Discover international teams and player links
python step1.py

# Step 2: Scrape detailed player statistics and career bios
python step2.py

# Step 3: Parse Cricsheet match JSONs & ingest into PostgreSQL
python step3.py
```

---

### 5. Machine Learning Training

Train the model and save the artifact:

```bash
python train_final_model.py
```

---

### 6. Running Backend & Frontend

#### Start the FastAPI Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

#### Start the Django Frontend
In a new terminal window:
```bash
cd frontend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8001
```
Web Application UI: [http://localhost:8001](http://localhost:8001)

---

## 🌪️ Airflow Orchestration

For fully automated, containerized pipeline execution:

```bash
cd cricket_data_engineering

# Launch Airflow containers (Webserver, Scheduler, Postgres, Redis, Worker)
docker-compose up -d

# Open Airflow UI at http://localhost:8080 (Default credentials: airflow / airflow)
# Trigger the 'cricket_pipeline' DAG
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
