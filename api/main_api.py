from fastapi import FastAPI, HTTPException, Query
import pandas as pd
import os
from typing import List, Any, Optional

app = FastAPI(
    title="Global Football Analytics API",
    description="API para consumo de dados consolidados de futebol da camada Gold[cite: 1]."
)

def get_gold_data():
    """Lê o arquivo consolidado gerado pelo pipeline ETL[cite: 1]."""
    file_path = os.path.join("data", "gold", "kpis.parquet")
    if not os.path.exists(file_path):
        return None
    return pd.read_parquet(file_path)

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à Global Football Analytics API!"}

@app.get("/standings", response_model=List[Any])
def get_standings(
    league_code: Optional[str] = Query(None, description="Filtrar por sigla da liga (ex: PL, BSA, CL)")
):
    df = get_gold_data()
    if df is None:
        raise HTTPException(
            status_code=404, 
            detail="Arquivo consolidado não encontrado (data/gold/kpis.parquet). Execute o pipeline ETL (python -m src.main) primeiro."
        )
    
    # Aplica filtro por competição caso o parâmetro seja fornecido na URL
    if league_code and 'league_code' in df.columns:
        df = df[df['league_code'] == league_code.upper()]
        
    return df.to_dict(orient="records")