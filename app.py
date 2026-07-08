import streamlit as st
import pandas as pd
import requests
import os

st.set_page_config(page_title="Dashboard Global de Futebol", layout="wide")

LEAGUES = {
    "Premier League": "PL", "Copa do Mundo": "WC", "Champions League": "CL",
    "Mundial de Clubes": "FCWC", "Libertadores": "CLI", "Brasileirão Série A": "BSA",
    "La Liga": "PD", "Ligue 1": "FL1", "Serie A Italiana": "SA", "Bundesliga": "BL1"
}

st.title("⚽ Dashboard Global de Futebol")
st.markdown("---")

def fetch_data(league_code):
    api_key = st.secrets.get("API_KEY")
    if not api_key: return None
        
    url = f"https://api.football-data.org/v4/competitions/{league_code}/standings"
    headers = {"X-Auth-Token": api_key}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        all_groups = [pd.DataFrame(stage['table']) for stage in data['standings'] if 'table' in stage]
        df = pd.concat(all_groups, ignore_index=True)
        df_team = pd.json_normalize(df['team']).add_prefix('team_')
        return pd.concat([df.drop(columns=['team']), df_team], axis=1)
    return None

def load_data(league_code):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "data", "gold", f"{league_code}.parquet")
    
    if os.path.exists(file_path):
        return pd.read_parquet(file_path)
    else:
        return fetch_data(league_code)

selected_league_name = st.sidebar.selectbox("Selecione a Competição:", list(LEAGUES.keys()))
league_code = LEAGUES[selected_league_name]

df = load_data(league_code)

if df is not None:
    team_list = sorted(df['team_name'].unique())
    selected_team = st.sidebar.selectbox("Selecione o Time:", team_list)
    
    filtered_df = df[df['team_name'] == selected_team]
    
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(filtered_df['team_crest'].values[0], width=150)
    with col2:
        st.subheader(f"Perfil: {selected_team}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Pontos", int(filtered_df['points'].values[0]))
        c2.metric("Jogos", int(filtered_df['playedGames'].values[0]))
        c3.metric("Saldo", int(filtered_df['goalDifference'].values[0]))
        
    st.dataframe(filtered_df, use_container_width=True)
else:
    st.error("Não foi possível carregar os dados. Verifique a API_KEY.")