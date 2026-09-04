import os
import math
import numpy as np
import duckdb
import pandas as pd
import gcsfs
import pyarrow.parquet as pq
from scipy.stats import poisson
from src.logging_config import logger

# =====================================================================
# 1. CONSULTAS SQL VIA DUCKDB / GCSFS
# =====================================================================

def query_hive_standings(league_code: str = None) -> pd.DataFrame:
    parquet_path = os.path.join("data", "gold", "standings", "**", "*.parquet")
    query = f"SELECT * FROM read_parquet('{parquet_path}', hive_partitioning=1, union_by_name=True)"
    
    if league_code:
        query += f" WHERE league_code = '{league_code.upper()}'"
    query += " ORDER BY points DESC, goalDifference DESC"
    
    try:
        logger.info(f"Executando SQL DuckDB para standings (Liga: {league_code or 'Todas'})")
        return duckdb.query(query).to_df()
    except Exception as e:
        logger.error(f"Erro DuckDB (Standings): {e}")
        return None

def query_hive_matches(league_code: str = None) -> pd.DataFrame:
    """
    Carrega o histórico de partidas de forma segura do GCS, filtrando a liga 
    e ignorando diretórios de partição órfãos ou corrompidos, evitando falhas do DuckDB com gs://.
    """
    try:
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "google_credentials.json")
        fs = gcsfs.GCSFileSystem(token=creds_path)
        
        bucket_path = "futebol-datalake-global-analytics-2026/data/gold/matches"
        
        # Se um código de liga foi especificado, tentamos buscar direto na subpasta para otimizar
        if league_code:
            caminho_busca = f"{bucket_path}/league_code={league_code.upper()}/**/*.parquet"
        else:
            caminho_busca = f"{bucket_path}/**/*.parquet"
            
        arquivos = fs.glob(caminho_busca)
        
        # Se não achar por subpasta exata, faz a busca global segura ignorando pastas de data órfãs
        if not arquivos:
            arquivos = [f for f in fs.glob(f"{bucket_path}/**/*.parquet") if "date=" in f]

        if not arquivos:
            logger.warning("Nenhum arquivo de partida encontrado no Data Lake.")
            return None
            
        dfs = []
        for arq in arquivos:
            try:
                with fs.open(arq, 'rb') as f:
                    table = pq.read_table(f)
                    df_temp = table.to_pandas()
                    
                    # Garante que a coluna league_code existe (recuperando do caminho se necessário)
                    if 'league_code' not in df_temp.columns:
                        if 'league_code=PL' in arq:
                            df_temp['league_code'] = 'PL'
                        elif 'league_code=BSA' in arq:
                            df_temp['league_code'] = 'BSA'
                            
                    if league_code and 'league_code' in df_temp.columns:
                        df_temp = df_temp[df_temp['league_code'] == league_code.upper()]
                        
                    if not df_temp.empty:
                        dfs.append(df_temp)
            except Exception:
                continue
                
        if not dfs:
            return None
            
        df_final = pd.concat(dfs, ignore_index=True)
        if 'utc_date' in df_final.columns:
            df_final['utc_date'] = pd.to_datetime(df_final['utc_date'])
            df_final = df_final.sort_values(by='utc_date', ascending=False)
            
        logger.info(f"Dados carregados com sucesso para a liga: {league_code or 'Todas'}")
        return df_final
        
    except Exception as e:
        logger.error(f"Erro ao carregar matches via GCSFS: {e}")
        return None

# =====================================================================
# 2. MOTOR ESTATÍSTICO DE POISSON VETORIZADO
# =====================================================================

def get_match_predictions(league_code: str, home_team: str, away_team: str, match_date: str = None, historical_df: pd.DataFrame = None) -> dict:
    """
    Gera probabilidades aplicando Time Decay e Operações Matriciais (Vetorização).
    Recebe 'historical_df' opcionalmente para evitar múltiplas consultas ao DB durante backtests.
    """
    if historical_df is not None:
        df = historical_df.copy()
    else:
        df = query_hive_matches(league_code)
    
    if df is None or df.empty:
        return None

    df_finished = df[df['status'].isin(['FINISHED', 'IN_PLAY'])].copy()
    df_finished = df_finished.dropna(subset=['home_goals', 'away_goals'])
    df_finished['utc_date'] = pd.to_datetime(df_finished['utc_date'])
    
    # Prevenção de Time Travel
    if match_date:
        current_match_date = pd.to_datetime(match_date)
        df_finished = df_finished[df_finished['utc_date'] < current_match_date]
        data_referencia = current_match_date
    else:
        data_referencia = df_finished['utc_date'].max()
    
    if df_finished.empty or len(df_finished) < 20:
        return None

    # Time Decay
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

    # -----------------------------------------------------------------
    # VETORIZAÇÃO: Criando a Matriz de Probabilidades Instantaneamente
    # -----------------------------------------------------------------
    # Cria um array de gols de 0 a 5
    goals = np.arange(6)
    
    # Calcula as probabilidades de todos os 6 cenários de gols de uma vez
    prob_home_array = poisson.pmf(goals, home_expected_goals)
    prob_away_array = poisson.pmf(goals, away_expected_goals)
    
    # Produto externo (outer) multiplica os dois vetores formando uma grade 6x6
    prob_matrix = np.outer(prob_home_array, prob_away_array)

    # Vitória do Mandante: Soma o triângulo inferior da matriz (Onde Gols Mandante > Visitante)
    prob_home_win = np.tril(prob_matrix, -1).sum()
    
    # Vitória do Visitante: Soma o triângulo superior (Onde Gols Visitante > Mandante)
    prob_away_win = np.triu(prob_matrix, 1).sum()
    
    # Empate: Soma a diagonal principal (Onde Gols Mandante == Visitante)
    prob_draw = np.trace(prob_matrix)

    # Mercado Prop Bet Over 2.5: Identifica as coordenadas da matriz onde a soma dos gols é maior que 2.5
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