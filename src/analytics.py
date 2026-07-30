import os
import duckdb
import pandas as pd
from src.logging_config import logger

def query_hive_standings(league_code: str = None) -> pd.DataFrame:
    """
    Utiliza o DuckDB para consultar as partições Hive da tabela de classificação (standings)
    diretamente no disco usando SQL, sem carregar arquivos manualmente.
    """
    # Caminho base coringa que aponta para qualquer data e qualquer liga nas partições Hive
    parquet_path = os.path.join("data", "gold", "standings", "**", "*.parquet")
    
    query = f"""
        SELECT * 
        FROM read_parquet('{parquet_path}', hive_partitioning=1)
    """
    
    # Se o usuário escolheu uma liga específica, filtramos direto no SQL (Partition Pruning otimizado)
    if league_code:
        query += f" WHERE league_code = '{league_code.upper()}'"
        
    query += " ORDER BY points DESC, goalDifference DESC"
    
    try:
        logger.info(f"Executando consulta SQL via DuckDB para standings (Liga: {league_code or 'Todas'})")
        df = duckdb.query(query).to_df()
        return df
    except Exception as e:
        logger.error(f"Erro ao executar consulta analítica no DuckDB: {e}")
        return None

def query_hive_matches(league_code: str = None) -> pd.DataFrame:
    """
    Utiliza o DuckDB para consultar o histórico de partidas (matches) particionadas no Hive.
    """
    parquet_path = os.path.join("data", "gold", "matches", "**", "*.parquet")
    
    query = f"""
        SELECT * 
        FROM read_parquet('{parquet_path}', hive_partitioning=1)
    """
    
    if league_code:
        query += f" WHERE league_code = '{league_code.upper()}'"
        
    query += " ORDER BY utc_date DESC"
    
    try:
        logger.info(f"Executando consulta SQL via DuckDB para matches (Liga: {league_code or 'Todas'})")
        df = duckdb.query(query).to_df()
        return df
    except Exception as e:
        logger.error(f"Erro ao consultar partidas no DuckDB: {e}")
        return None