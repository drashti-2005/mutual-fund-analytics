# Mutual Fund Analytics — Day 1: Data Ingestion Pipeline

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Pandas](https://img.shields.io/badge/Pandas-2.2-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Day%201%20Complete-brightgreen)

## Project Overview

A **production-quality data ingestion and analytics pipeline** for Indian mutual fund data, built as part of the Bluestock Fintech internship program.

The pipeline ingests mutual fund NAV (Net Asset Value) data from the [MFAPI.in](https://www.mfapi.in/) public API, performs data quality validation, and stores structured datasets for downstream analytics and dashboard reporting.

---

## Project Structure

```
Bluestock-internship/
├── data/
│   ├── raw/                   # Raw ingested CSV files
│   │   ├── hdfc_top100_nav.csv
│   │   └── all_funds_nav.csv
│   └── processed/             # Cleaned & transformed data
├── notebooks/
│   └── Day1_EDA.ipynb         # Exploratory Data Analysis
├── scripts/
│   ├── data_ingestion.py      # Main ingestion pipeline
│   └── live_nav_fetch.py      # Live NAV API fetcher
├── sql/                       # SQL queries for analysis
├── dashboard/                 # Dashboard assets
├── reports/
│   └── data_quality_summary.md
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Datasets

| File | Description |
|------|-------------|
| `hdfc_top100_nav.csv` | HDFC Top 100 Fund NAV history (scheme: 125497) |
| `all_funds_nav.csv` | Combined NAV for 5 large-cap bluechip funds |

### Scheme Codes Tracked

| Scheme Code | Fund Name |
|-------------|-----------|
| 125497 | HDFC Top 100 Fund |
| 119551 | SBI Bluechip Fund |
| 120503 | ICICI Prudential Bluechip Fund |
| 118632 | Nippon India Large Cap Fund |
| 119092 | Axis Bluechip Fund |
| 120841 | Kotak Bluechip Fund |

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/Bluestock-internship.git
cd Bluestock-internship
```

### 2. Create Virtual Environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Data Ingestion

```bash
python scripts/data_ingestion.py
```

### 5. Fetch Live NAV Data

```bash
python scripts/live_nav_fetch.py
```

### 6. Launch Jupyter Notebook

```bash
jupyter notebook notebooks/Day1_EDA.ipynb
```

---

## Scripts

### `scripts/data_ingestion.py`
- Loads all CSV datasets from `data/raw/`
- Prints shape, dtypes, head, missing values, duplicates, statistics
- Generates a data quality profile saved to `reports/`

### `scripts/live_nav_fetch.py`
- Fetches live NAV data from MFAPI.in REST API
- Supports retry mechanism and API response validation
- Downloads data for 6 mutual fund schemes
- Saves individual + combined master CSV files

---

## Data Quality Report

See [reports/data_quality_summary.md](reports/data_quality_summary.md) for:
- Missing value counts per column
- Duplicate row analysis
- Data type validation
- Outlier detection summary
- AMFI scheme code validation

---

## Technology Stack

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Core language |
| Pandas | Data manipulation |
| NumPy | Numerical computations |
| Requests | API calls |
| Matplotlib / Seaborn | Visualization |
| Plotly | Interactive charts |
| SQLAlchemy | Database ORM |
| Jupyter | Notebook environment |

---

## API Reference

- **Base URL:** `https://api.mfapi.in/mf/`
- **Endpoint:** `GET /mf/{scheme_code}`
- **Response:** JSON with scheme metadata + NAV history

---

## Author

**Bluestock Fintech Internship**  
Day 1 — Data Ingestion & Quality Assessment  
Date: 2026-06-22

---

## License

This project is licensed under the MIT License.
