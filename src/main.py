import pandas as pd
import requests
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')

LEAGUES = {
    "Premier League": "PL",
    "Copa do Mundo": "WC",
    "Champions League": "CL",
    "Mundial de Clubes": "FCWC",
    "Libertadores": "CLI",
    "Brasileirão Série A": "BSA",
    "La Liga": "PD",
    "Ligue 1": "FL1",
    "Serie A Italiana": "SA",
    "Bundesliga": "BL1"
}

def run_pipeline():
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("API_BASE_URL")
    
    if not api_key:
        raise ValueError("API_KEY não encontrada!")

    os.makedirs("data/gold", exist_ok=True)

    for name, code in LEAGUES.items():
        print(f"Processando: {name} ({code})...")
        endpoint = f"{base_url}/competitions/{code}/standings"
        headers = {"X-Auth-Token": api_key}
        
        try:
            response = requests.get(endpoint, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'standings' in data and data['standings']:
                    # Agrega todos os grupos/stages disponíveis
                    all_groups = []
                    for stage in data['standings']:
                        if 'table' in stage:
                            all_groups.append(pd.DataFrame(stage['table']))
                    
                    if all_groups:
                        df = pd.concat(all_groups, ignore_index=True)
                        
                        if 'team' in df.columns:
                            df_team = pd.json_normalize(df['team']).add_prefix('team_')
                            df_final = pd.concat([df.drop(columns=['team']), df_team], axis=1)
                        else:
                            df_final = df
                        
                        df_final.to_parquet(f"data/gold/{code}.parquet")
                        print(f"Sucesso: {name} salvo.")
                    else:
                        print(f"Aviso: Tabela vazia para {name}")
                else:
                    print(f"Aviso: Sem dados de classificação para {name}")
            else:
                print(f"Erro {response.status_code} em {name}")
        except Exception as e:
            print(f"Falha ao processar {name}: {e}")

if __name__ == "__main__":
    run_pipeline()