import os
import math
import numpy as np
import duckdb
import pandas as pd
import gcsfs
import pyarrow.dataset as ds
from scipy.stats import poisson
from src.logging_config import logger

def get_gcs_token():
    """Identifica automaticamente se está na nuvem (Streamlit Secrets) ou local (JSON)"""
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            return dict(st.secrets["gcp_service_account"])
    except Exception:
        pass
    return os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "google_credentials.json")

# =====================================================================
# 1. CONSULTAS OTIMIZADAS (DATA LAKE)
# =====================================================================

def query_hive_standings(league_code: str = None) -> pd.DataFrame:
    parquet_path = os.path.join("data", "gold", "standings", "**", "*.parquet")
    query = f"SELECT * FROM read_parquet('{parquet_path}', hive_partitioning=1, union_by_name=True)"
    
    if league_code:
        query += f" WHERE league_code = '{league_code.upper()}'"
    query += " ORDER BY points DESC, goalDifference DESC"
    
    try:
        return duckdb.query(query).to_df()
    except Exception as e:
        logger.error(f"Erro DuckDB (Standings): {e}")
        return None

def query_hive_matches(league_code: str = None) -> pd.DataFrame:
    """
    Leitura isolada e ultrarrápida: pré-filtra os arquivos pela liga para evitar colisão 
    de esquemas entre PL e BSA, mantendo a velocidade paralela do PyArrow Dataset.
    """
    try:
        token = get_gcs_token()
        fs = gcsfs.GCSFileSystem(token=token)
        bucket_path = "futebol-datalake-global-analytics-2026/data/gold/matches"

        # 1. Mapeia todos os arquivos reais no bucket
        all_files = fs.glob(f"{bucket_path}/**/*.parquet")
        if not all_files:
            logger.warning("Nenhum arquivo encontrado no bucket.")
            return None

        # 2. Separa cirurgicamente apenas os arquivos da liga solicitada
        target_files = []
        if league_code:
            codigo = league_code.upper()
            target_files = [f for f in all_files if f"league_code={codigo}" in f.upper()]
        else:
            target_files = all_files

        if not target_files:
            logger.warning(f"Histórico não encontrado para a liga: {league_code}")
            return None

        # 3. Leitura C++ nativa e exclusiva da liga (sem conflitos com o resto do Data Lake)
        dataset = ds.dataset(target_files, format="parquet", filesystem=fs)
        df = dataset.to_table().to_pandas()

        # 4. Restaura a coluna de identificação caso tenha sido removida pelo particionamento de pastas
        if league_code and 'league_code' not in df.columns:
            df['league_code'] = league_code.upper()

        # 5. Ordenação e formatação final
        if not df.empty and 'utc_date' in df.columns:
            df['utc_date'] = pd.to_datetime(df['utc_date'], errors='coerce')
            df = df.sort_values(by='utc_date', ascending=False)
            
        return df
        
    except Exception as e:
        logger.error(f"Erro fatal ao ler matches do GCS: {e}")
        return None

# =====================================================================
# 2. MOTOR ESTATÍSTICO DE POISSON VETORIZADO
# =====================================================================

def get_match_predictions(league_code: str, home_team: str, away_team: str, match_date: str = None, historical_df: pd.DataFrame = None) -> dict:
    if historical_df is not None:
        df = historical_df.copy()
    else:
        df = query_hive_matches(league_code)
    
    if df is None or df.empty:
        return None

    df_finished = df[df['status'].isin(['FINISHED', 'IN_PLAY'])].copy()
    df_finished = df_finished.dropna(subset=['home_goals', 'away_goals'])
    df_finished['utc_date'] = pd.to_datetime(df_finished['utc_date'])
    
    if match_date:
        current_match_date = pd.to_datetime(match_date)
        df_finished = df_finished[df_finished['utc_date'] < current_match_date]
        data_referencia = current_match_date
    else:
        data_referencia = df_finished['utc_date'].max()
    
    if df_finished.empty or len(df_finished) < 20:
        return None

    df_finished['dias_atras'] = (data_referencia - df_finished['utc_date']).dt.days
    df_finished['dias_atras'] = df_finished['dias_atras'].clip(lower=0)
    df_finished['peso'] = np.exp(-df_finished['dias_atras'] / 365)

    def media_ponderada(dataframe, coluna):
        if dataframe.empty or dataframe['peso'].sum() == 0: 
            return 0.0
        return np.average(dataframe[coluna], weights=dataframe['peso'])

    league_avg_home_goals = media_ponderada(df_finished, 'home_goals')
    league_avg_away_goals = media_ponderada(df_finished, 'away_goals')

    home_stats = df_finished[df_finished['home_team'] == home_team]
    if home_stats.empty: return None
    home_scored_avg = media_ponderada(home_stats, 'home_goals')
    home_conceded_avg = media_ponderada(home_stats, 'away_goals')

    away_stats = df_finished[df_finished['away_team'] == away_team]
    if away_stats.empty: return None
    away_scored_avg = media_ponderada(away_stats, 'away_goals')
    away_conceded_avg = media_ponderada(away_stats, 'home_goals')

    if league_avg_home_goals == 0 or league_avg_away_goals == 0: return None

    home_attack_strength = home_scored_avg / league_avg_home_goals
    away_defense_strength = away_conceded_avg / league_avg_home_goals
    away_attack_strength = away_scored_avg / league_avg_away_goals
    home_defense_strength = home_conceded_avg / league_avg_away_goals

    home_expected_goals = home_attack_strength * away_defense_strength * league_avg_home_goals
    away_expected_goals = away_attack_strength * home_defense_strength * league_avg_away_goals

    goals = np.arange(6)
    prob_home_array = poisson.pmf(goals, home_expected_goals)
    prob_away_array = poisson.pmf(goals, away_expected_goals)
    prob_matrix = np.outer(prob_home_array, prob_away_array)

    prob_home_win = np.tril(prob_matrix, -1).sum()
    prob_away_win = np.triu(prob_matrix, 1).sum()
    prob_draw = np.trace(prob_matrix)

    i_grid, j_grid = np.meshgrid(goals, goals, indexing='ij')
    prob_over_2_5 = prob_matrix[(i_grid + j_grid) > 2.5].sum()

    total_prob = prob_home_win + prob_away_win + prob_draw
    if total_prob == 0: return None
    
    return {
        "home_xg": round(home_expected_goals, 2),
        "away_xg": round(away_expected_goals, 2),
        "home_win_pct": round((prob_home_win / total_prob) * 100, 1),
        "draw_pct": round((prob_draw / total_prob) * 100, 1),
        "away_win_pct": round((prob_away_win / total_prob) * 100, 1),
        "over_2_5_pct": round(prob_over_2_5 * 100, 1)
    }