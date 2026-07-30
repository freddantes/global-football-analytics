from fastapi import FastAPI, HTTPException, Query
import pandas as pd
import duckdb
import os
from typing import List, Any, Optional

app = FastAPI(
    title="Global Football Analytics API",
    description="API analítica ultra-rápida utilizando DuckDB sobre partições Hive da camada Gold."
)

def query_standings_via_duckdb(league_code: Optional[str] = None) -> pd.DataFrame:
    """
    Usa o DuckDB para consultar os arquivos Parquet particionados no Hive 
    diretamente no disco, aplicando filtragem inteligente (Partition Pruning).
    """
    parquet_path = os.path.join("data", "gold", "standings", "**", "*.parquet")
    
    if not os.path.exists(os.path.join("data", "gold", "standings")):
        return None

    query = f"""
        SELECT * 
        FROM read_parquet('{parquet_path}', hive_partitioning=1)
    """
    
    # Se uma liga específica foi solicitada, filtramos direto na consulta SQL
    if league_code:
        query += f" WHERE league_code = '{league_code.upper()}'"
        
    query += " ORDER BY points DESC, goalDifference DESC"
    
    try:
        df = duckdb.query(query).to_df()
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"Erro no DuckDB: {e}")
        return None

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à Global Football Analytics API (Powered by DuckDB)!"}

@app.get("/standings", response_model=List[Any])
def get_standings(
    league_code: Optional[str] = Query(None, description="Filtrar por sigla da liga (ex: PL, BSA, CL)")
):
    df = query_standings_via_duckdb(league_code)
    
    if df is None:
        raise HTTPException(
            status_code=404, 
            detail="Nenhum dado encontrado. Execute o pipeline ETL (python -m src.main) primeiro."
        )
        
    return df.to_dict(orient="records")