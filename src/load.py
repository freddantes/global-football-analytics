import os
import pandas as pd

def save_data(df, file_name, date_str):
    """Salva um DataFrame em formato Parquet dentro da pasta diária da camada Gold."""
    target_dir = os.path.join("data", "gold", date_str)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, f"{file_name}_{date_str}.parquet")
    df.to_parquet(file_path, index=False)
    print(f"Sucesso: Arquivo salvo em {file_path}")

def save_consolidated_data(dfs_list):
    # Filtra a lista removendo DataFrames que sejam None ou estejam completamente vazios
    valid_dfs = [df for df in dfs_list if df is not None and not df.empty]
    if not valid_dfs:
        return
    
    target_dir = os.path.join("data", "gold")
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, "kpis.parquet")
    
    consolidated_df = pd.concat(valid_dfs, ignore_index=True)
    consolidated_df.to_parquet(file_path, index=False)
    print(f"Sucesso: Base consolidada de classificação salva em {file_path}")

def save_consolidated_matches(dfs_list):
    valid_dfs = [df for df in dfs_list if df is not None and not df.empty]
    if not valid_dfs:
        return
    
    target_dir = os.path.join("data", "gold")
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, "matches.parquet")
    
    consolidated_df = pd.concat(valid_dfs, ignore_index=True)
    consolidated_df.to_parquet(file_path, index=False)
    print(f"Sucesso: Base consolidada de PARTIDAS salva em {file_path}")