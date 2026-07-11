import pandas as pd
import requests
import os
from datetime import datetime
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
    today = datetime.now().strftime("%Y-%m-%d")
    
    if not api_key:
        raise ValueError("API_KEY não encontrada!")

    # Cria pasta com a data de hoje para versionamento
    target_dir = f"data/gold/{today}"
    os.makedirs(target_dir, exist_ok=True)

    for name, code in LEAGUES.items():
        print(f"Processando: {name} ({code})...")
        endpoint = f"{base_url}/competitions/{code}/standings"
        headers = {"X-Auth-Token": api_key}
        
        try:
            response = requests.get(endpoint, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'standings' in data and data['standings']:
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
                        
                        # Cálculo de métricas
                        df_final['goals_per_game'] = (df_final['goalsFor'] / df_final['playedGames']).fillna(0).round(2)
                        df_final['points_pct'] = (df_final['points'] / (df_final['playedGames'] * 3)).fillna(0).round(2)
                        
                        # Salva arquivo versionado pela data
                        df_final.to_parquet(f"{target_dir}/{code}_{today}.parquet")
                        print(f"Sucesso: {name} salvo em {target_dir}")
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