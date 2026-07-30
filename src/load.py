import os
import pandas as pd

def save_hive_partition(df, dataset_name, date_str):
    """
    Salva o DataFrame na estrutura de Particionamento Hive.
    Caminho gerado: data/gold/{dataset_name}/date={date_str}/league_code={code}/data.parquet
    """
    if df is None or df.empty:
        return

    # Extrai o código da liga da primeira linha do DataFrame
    code = df['league_code'].iloc[0]
    
    # Monta a árvore de diretórios nativa do Hive
    target_dir = os.path.join("data", "gold", dataset_name, f"date={date_str}", f"league_code={code}")
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, "data.parquet")
    
    # Salva o arquivo particionado em formato Parquet
    df.to_parquet(file_path, index=False)
    print(f"Sucesso: Partição Hive salva em {file_path}")