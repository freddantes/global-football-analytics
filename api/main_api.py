from fastapi import FastAPI, HTTPException, Query
import pandas as pd
import duckdb
from typing import List, Any, Optional

# Novas bibliotecas necessárias para ler da nuvem
import pyarrow.dataset as ds
import gcsfs

app = FastAPI(
    title="Global Football Analytics API",
    description="API analítica ultra-rápida utilizando DuckDB sobre partições Hive da camada Gold no GCP."
)

# Caminho do seu bucket no Google Cloud (Substitua se necessário)
GCS_BUCKET_PATH = "futebol-datalake-global-analytics-2026/data/gold/standings"

def query_standings_via_duckdb(league_code: Optional[str] = None) -> pd.DataFrame:
    """
    Usa o DuckDB para consultar os arquivos Parquet particionados no Hive 
    diretamente no GCP, aplicando filtragem inteligente (Partition Pruning).
    """
    try:
        # 1. Cria a conexão com o sistema de arquivos do Google Cloud
        fs = gcsfs.GCSFileSystem()
        
        # 2. Verifica se a pasta existe lá na nuvem (substitui o os.path.exists)
        if not fs.exists(GCS_BUCKET_PATH):
            return None

        # 3. Mapeia os dados na nuvem e avisa que eles usam partições do tipo Hive
        dataset = ds.dataset(
            GCS_BUCKET_PATH, 
            filesystem=fs, 
            format="parquet", 
            partitioning="hive"
        )
    except Exception as e:
        print(f"Erro ao conectar com o GCP: {e}")
        return None

    # 4. A consulta SQL agora aponta para a variável 'dataset' que criamos acima!
    query = """
        SELECT * 
        FROM dataset
    """
    
    # Se uma liga específica foi solicitada, filtramos direto na consulta SQL
    if league_code:
        query += f" WHERE league_code = '{league_code.upper()}'"
        
    query += " ORDER BY points DESC, goalDifference DESC"
    
    try:
        # O duckdb.query() é inteligente o suficiente para achar a variável 'dataset' no código
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
            detail="Nenhum dado encontrado. Verifique se os arquivos foram enviados para o Data Lake no GCP."
        )
        
    return df.to_dict(orient="records")