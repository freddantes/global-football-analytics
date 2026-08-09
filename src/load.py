import os
import pandas as pd

def save_hive_partition(df, dataset_name, date_str):
    """
    Salva o DataFrame localmente (backup) e faz o upload direto para o
    Data Lake particionado no Google Cloud Storage (GCS).
    """
    if df is None or df.empty:
        return

    # Extrai o código da liga da primeira linha do DataFrame
    code = df['league_code'].iloc[0]
    
    # ---------------------------------------------------------
    # 1. SALVAR NO DISCO LOCAL (Backup do Robô)
    # ---------------------------------------------------------
    target_dir = os.path.join("data", "gold", dataset_name, f"date={date_str}", f"league_code={code}")
    os.makedirs(target_dir, exist_ok=True)
    
    local_file_path = os.path.join(target_dir, "data.parquet")
    df.to_parquet(local_file_path, index=False)
    print(f"Backup Local salvo em: {local_file_path}")

    # ---------------------------------------------------------
    # 2. UPLOAD PARA A NUVEM (Google Cloud Storage)
    # ---------------------------------------------------------
    bucket_name = "futebol-datalake-global-analytics-2026"
    gcs_path = f"gs://{bucket_name}/data/gold/{dataset_name}/date={date_str}/league_code={code}/data.parquet"
    
    try:
        # O Pandas envia o arquivo Parquet direto para a nuvem
        df.to_parquet(gcs_path, index=False)
        print(f"Sucesso: Partição Hive salva na NUVEM em {gcs_path}")
    except Exception as e:
        print(f"Erro Crítico ao enviar para o Google Cloud: {e}")