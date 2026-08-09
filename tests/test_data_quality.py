import pandas as pd
import duckdb
import pytest
import os

def test_no_duplicate_teams_in_gold_layer():
    # Caminho base usando padrão glob para abranger as partições Hive (*/**/*.parquet)
    gold_path = os.path.join("data", "gold", "standings", "**", "*.parquet")
    
    # Se a pasta principal da camada Gold não existir, pulamos o teste para não falhar sem dados locais
    if not os.path.exists(os.path.join("data", "gold", "standings")):
        pytest.skip("Pasta da camada Gold não encontrada. Execute o pipeline ETL primeiro.")

    # Lemos os dados particionados usando o DuckDB com suporte a Hive
    try:
        query = f"SELECT * FROM read_parquet('{gold_path}', hive_partitioning=1)"
        df = duckdb.query(query).to_df()
    except Exception as e:
        pytest.fail(f"Falha ao ler os arquivos parquet particionados com DuckDB: {e}")

    # Se por acaso o DataFrame estiver vazio, pulamos o teste
    if df.empty:
        pytest.skip("Nenhum dado encontrado nas partições da camada Gold.")

    # Verificamos se há duplicatas na combinação de chaves que deveria ser única
    duplicatas = df.duplicated(subset=['team_name', 'league_code'])
    
    total_duplicatas = duplicatas.sum()
    
    assert total_duplicatas == 0, f"Alerta Crítico: Foram encontradas {total_duplicatas} linhas duplicadas na camada Gold!"