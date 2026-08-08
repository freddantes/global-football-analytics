import pandas as pd
import os

# ==========================================
# 1. CONFIGURAÇÃO DE ACESSO À NUVEM
# ==========================================
# Autentica o seu computador local no Google Cloud usando o arquivo de credenciais
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
 BUCKET_PATH = "gs://futebol-datalake-global-analytics-2026/data/gold/matches"
# LOCAL_PATH = os.path.join("data", "gold", "matches") # apenas para teste local

def run_backfill():
    print("Iniciando leitura do arquivo CSV...")
    
    # ==========================================
    # 2. EXTRAÇÃO E TRATAMENTO DE DADOS
    # ==========================================
    # Lê o CSV baixado
    df = pd.read_csv("brasileirao_historico.csv")
    
    # Padroniza as colunas vitais para o modelo
    colunas_map = {
        'Date': 'utc_date',
        'Home': 'home_team',
        'Away': 'away_team',
        'HG': 'home_goals',
        'AG': 'away_goals'
    }
    df = df.rename(columns=colunas_map)
    
    # --- DICIONÁRIO DE-PARA DE TIMES (MASTER DATA) ---
    # Mapeamento completo baseado na listagem do CSV para os nomes oficiais da API
    tradutor_times = {
        "Palmeiras": "SE Palmeiras",
        "Sport Recife": "Sport Club do Recife",
        "Figueirense": "Figueirense FC",
        "Botafogo RJ": "Botafogo FR",
        "Corinthians": "SC Corinthians Paulista",
        "Internacional": "SC Internacional",
        "Ponte Preta": "AA Ponte Preta",
        "Bahia": "EC Bahia",
        "Cruzeiro": "Cruzeiro EC",
        "Vasco": "CR Vasco da Gama",
        "Atletico GO": "Atlético Clube Goianiense",
        "Flamengo RJ": "CR Flamengo",
        "Portuguesa": "Associação Portuguesa de Desportos",
        "Nautico": "Clube Náutico Capibaribe",
        "Atletico-MG": "CA Mineiro",
        "Coritiba": "Coritiba FBC",
        "Santos": "Santos FC",
        "Sao Paulo": "São Paulo FC",
        "Fluminense": "Fluminense FC",
        "Gremio": "Grêmio FBPA",
        "Vitoria": "EC Vitória",
        "Criciuma": "Criciúma EC",
        "Athletico-PR": "CA Paranaense",
        "Goias": "Goiás EC",
        "Chapecoense-": "Associação Chapecoense de Futebol",
        "Avai": "Avaí FC",
        "Joinville": "Joinville EC",
        "Santa Cruz": "Santa Cruz FC",
        "America MG": "América FC",
        "Parana": "Paraná Clube",
        "Ceara": "Ceará SC",
        "CSA": "Centro Sportivo Alagoano",
        "Fortaleza": "Fortaleza EC",
        "Bragantino": "RB Bragantino",
        "Cuiaba": "Cuiabá EC",
        "Juventude": "EC Juventude",
        "Mirassol": "Mirassol FC",
        "Remo": "Clube do Remo"
    }
    
    # Aplica a tradução nas colunas de mandante e visitante
    df['home_team'] = df['home_team'].replace(tradutor_times)
    df['away_team'] = df['away_team'].replace(tradutor_times)
    
    # Converte a data garantindo que o Pandas entenda o formato Dia/Mês/Ano
    df['utc_date'] = pd.to_datetime(df['utc_date'], dayfirst=True)
    
    # Cria a coluna 'date' apenas com Ano-Mês-Dia para o particionamento Hive
    df['date'] = df['utc_date'].dt.strftime('%Y-%m-%d')
    
    # ==========================================
    # 3. REGRAS DE NEGÓCIO DO MOTOR ESTATÍSTICO
    # ==========================================
    # Forçamos o status para finalizado e atribuímos o código da liga
    df['status'] = 'FINISHED'
    df['league_code'] = 'BSA'
    
    # Converte os gols para números decimais (Float) para bater com a ingestão diária
    df['home_goals'] = df['home_goals'].astype(float)
    df['away_goals'] = df['away_goals'].astype(float)
    
    # --- NOVO: GARANTINDO QUE AS ODDS FINANCEIRAS SEJAM LIDAS ---
    # Convertendo as colunas da Pinnacle para decimal (se existirem no CSV)
    if 'PSCH' in df.columns:
        df['PSCH'] = df['PSCH'].astype(float)
    if 'PSCD' in df.columns:
        df['PSCD'] = df['PSCD'].astype(float)
    if 'PSCA' in df.columns:
        df['PSCA'] = df['PSCA'].astype(float)
    
    # Seleciona estritamente as colunas que o Data Lake armazena, AGORA INCLUINDO AS ODDS
    colunas_finais = [
        'utc_date', 'status', 'home_team', 'away_team', 
        'home_goals', 'away_goals', 'date', 'league_code',
        'PSCH', 'PSCD', 'PSCA' 
    ]
    
    # Filtra de forma inteligente: pega apenas as colunas da lista acima que realmente estão no arquivo
    colunas_finais_presentes = [col for col in colunas_finais if col in df.columns]
    df_final = df[colunas_finais_presentes].copy()
    
    # ==========================================
    # 4. CARGA PARA O GOOGLE CLOUD (DATA LAKE)
    # ==========================================
    print(f"Dados formatados. Total de partidas prontas para upload: {len(df_final)}")
    print("Iniciando particionamento e envio via PyArrow...")
    
    # Aumentamos o limite de partições e arquivos abertos para 3000
    # garantindo espaço de sobra para os 1609 dias de jogos.
    df_final.to_parquet(
        BUCKET_PATH,
        #LOCAL_PATH, # apenas para teste local
        engine="pyarrow",
        partition_cols=["date", "league_code"],
        index=False,
        max_partitions=3000,
        max_open_files=3000 
    )
    print("🚀 Backfill do Brasileirão finalizado com sucesso! Pode verificar o painel.")

if __name__ == "__main__":
    run_backfill()