# Global Football Analytics Pipeline ⚽

[![Python Tests](https://github.com/freddantes/global-football-analytics/actions/workflows/tests.yml/badge.svg)](https://github.com/freddantes/global-football-analytics/actions/workflows/tests.yml)

A professional-grade, automated data pipeline and dashboard designed to extract, transform, and analyze football data from multiple global competitions. Built with a focus on modularity, data quality, and scalability.

## 🏗️ Architecture & Engineering
This project follows a professional **ETL (Extract, Transform, Load)** pattern:
*   **Extract (`src/extract.py`):** Handles API communication and raw data retrieval.
*   **Transform (`src/transform.py`):** Encapsulates business logic, data normalization, and KPI calculations. Logic is validated via unit tests.
*   **Load (`src/load.py`):** Manages data persistence using versioned Parquet files.
*   **CI/CD Pipeline:** Automated testing via GitHub Actions ensures data integrity.

## 🚀 Key Features
*   **Automated Pipeline:** Daily data ingestion via GitHub Actions.
*   **Data Quality:** Fully tested transformation logic using `pytest`.
*   **Advanced Analytics:** Volatility analysis (delta position) and historical trend visualization.
*   **Interactive Dashboard:** Built with `streamlit`.

## 🛠️ Tech Stack
- **Language:** Python 3.12+
- **Data Engineering:** `pandas`, `pyarrow`
- **Dashboard:** `streamlit`, `plotly`
- **Automation/Testing:** `pytest`, GitHub Actions

## 📋 Local Setup
1. **Clone the repository:** `git clone https://github.com/freddantes/global-football-analytics.git`
2. **Install dependencies:** `pip install -r requirements.txt`
3. **Configure Environment:** Create a `.env` file with your `API_KEY`.
4. **Run Pipeline:** `python -m src.main`
5. **Launch Dashboard:** `streamlit run app.py`
6. **Run Tests:** `python -m pytest`