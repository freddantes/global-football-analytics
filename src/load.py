import os
import pandas as pd

def save_data(df, code, date_str):
    """Salva o DataFrame processado na estrutura de pastas versionadas por data."""
    target_dir = os.path.join("data", "gold", date_str)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, f"{code}_{date_str}.parquet")
    df.to_parquet(file_path)
    print(f"Sucesso: Dados de {code} salvos em {file_path}")

def save_consolidated_data(dfs_list):
    """
    Consolida todos os DataFrames das ligas em um único arquivo kpis.parquet.
    Esse arquivo serve como Fonte Única da Verdade para a API FastAPI e análises globais.
    """
    if not dfs_list:
        return
    
    target_dir = os.path.join("data", "gold")
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, "kpis.parquet")
    
    # Une todas as tabelas em um único DataFrame consolidado
    consolidated_df = pd.concat(dfs_list, ignore_index=True)
    consolidated_df.to_parquet(file_path)
    print(f"Sucesso: Arquivo consolidado salvo em {file_path}")