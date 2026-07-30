from fastapi import FastAPI, HTTPException, Query
import pandas as pd
import os
from typing import List, Any, Optional

app = FastAPI(
    title="Global Football Analytics API",
    description="API com leitura otimizada de partições Hive da camada Gold."
)

def get_latest_standings(league_code: Optional[str] = None):
    base_dir = os.path.join("data", "gold", "standings")
    if not os.path.exists(base_dir):
        return None
        
    dates = sorted([d for d in os.listdir(base_dir) if d.startswith("date=")], reverse=True)
    if not dates:
        return None
        
    latest_date = dates[0]
    path_to_read = os.path.join(base_dir, latest_date)
    
    if league_code:
        path_to_read = os.path.join(base_dir, latest_date, f"league_code={league_code.upper()}")
        if not os.path.exists(path_to_read):
            return None
            
    return pd.read_parquet(path_to_read)

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à Global Football Analytics API!"}

@app.get("/standings", response_model=List[Any])
def get_standings(league_code: Optional[str] = Query(None, description="Sigla da liga (ex: PL, BSA)")):
    df = get_latest_standings(league_code)
    
    if df is None:
        raise HTTPException(
            status_code=404, 
            detail="Nenhuma partição encontrada. Execute o pipeline ETL primeiro."
        )
        
    return df.to_dict(orient="records")