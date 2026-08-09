import pandas as pd
import duckdb
import pytest
import os

def test_no_duplicate_teams_in_gold_layer():
    # Apontamos para a raiz da pasta Gold particionada no ambiente de desenvolvimento
    gold_path = os.path.join("data", "gold", "standings", "**", "*.parquet")
    
    # Verifica se a pasta principal existe localmente antes de rodar
    if not os.path.exists(os.path.join("data", "gold", "standings")):
        pytest.skip("Pasta da camada Gold não encontrada. Execute o pipeline ETL primeiro.")

    # Usamos o DuckDB para ler todas as partições como uma tabela única
    try:
        query = f"SELECT * FROM read_parquet('{gold_path}', hive_partitioning=1)"
        df = duckdb.query(query).to_df()
    except Exception as e:
        pytest.fail(f"Falha ao ler os arquivos parquet com DuckDB: {e}")

    # Verificamos duplicatas na combinação de time e liga
    duplicatas = df.duplicated(subset=['team_name', 'league_code'])
    total_duplicatas = duplicatas.sum()
    
    assert total_duplicatas == 0, f"Alerta Crítico: Foram encontradas {total_duplicatas} linhas duplicadas na camada Gold!"