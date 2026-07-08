# Global Football Analytics Pipeline

A professional-grade, automated data pipeline and dashboard designed to extract, transform, and analyze football data from multiple major competitions. This project leverages Python, pandas, Streamlit, and GitHub Actions for automated, scalable data workflows.

## 🚀 Project Overview
This project performs automated daily data collection from the [Football-Data API](https://www.football-data.org/). It transforms raw, nested API responses into cleaned, analytical-ready structures (Parquet format), which are then visualized through an interactive Streamlit dashboard.

## 🛠️ Tech Stack
- **Language:** Python 3.x
- **Data Manipulation:** pandas
- **Dashboard:** Streamlit
- **Automation:** GitHub Actions
- **Data Format:** Apache Parquet
- **Deployment:** Streamlit Cloud

## ⚙️ How it Works
1. **Extraction:** Automated daily collection of standings for various global leagues (Premier League, Champions League, Brasileirão, etc.).
2. **Transformation:** Normalizes nested JSON data into a flat, tabular structure for better analysis.
3. **Resilience:** The dashboard features an API-fallback mechanism, ensuring data accessibility even if local Parquet files are unavailable.
4. **Orchestration:** GitHub Actions triggers the process automatically.

## 📋 Getting Started
To run this project locally:

1. Clone the repository: `git clone https://github.com/freddantes/premier-league-analytics.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set your `API_KEY` in a `.env` file (base_url: `https://api.football-data.org/v4`).
4. Run the pipeline: `python -m src.main`
5. Launch the dashboard: `streamlit run app.py`

## 📊 Supported Competitions
The platform currently supports: Premier League, FIFA World Cup, Champions League, Club World Cup, Copa Libertadores, Brasileirão Série A, La Liga, Ligue 1, Serie A Italiana, and Bundesliga.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!