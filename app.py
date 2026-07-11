import streamlit as st
import pandas as pd
import requests
import os
import plotly.express as px

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
        df_final = pd.concat([df.drop(columns=['team']), df_team], axis=1)
        df_final['goals_per_game'] = (df_final['goalsFor'] / df_final['playedGames']).fillna(0).round(2)
        df_final['points_pct'] = (df_final['points'] / (df_final['playedGames'] * 3)).fillna(0).round(2)
        return df_final
    return None

def get_latest_data(league_code):
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "gold")
    if not os.path.exists(base_dir): return fetch_data(league_code)
    
    # Lista pastas de datas e pega a mais recente
    dates = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))], reverse=True)
    
    for date in dates:
        file_path = os.path.join(base_dir, date, f"{league_code}_{date}.parquet")
        if os.path.exists(file_path):
            return pd.read_parquet(file_path)
    return fetch_data(league_code)

selected_league_name = st.sidebar.selectbox("Selecione a Competição:", list(LEAGUES.keys()))
league_code = LEAGUES[selected_league_name]
df = get_latest_data(league_code)

if df is not None:
    team_list = sorted(df['team_name'].unique())
    selected_team = st.sidebar.selectbox("Selecione o Time para Destaque:", team_list)
    filtered_df = df[df['team_name'] == selected_team]
    
    with st.container():
        col_img, col_info = st.columns([1, 4])
        with col_img:
            st.image(filtered_df['team_crest'].values[0], width=200)
        with col_info:
            st.title(selected_team)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Pontos", int(filtered_df['points'].values[0]))
            c2.metric("Gols/Jogo", filtered_df['goals_per_game'].values[0])
            c3.metric("Aproveitamento", f"{int(filtered_df['points_pct'].values[0]*100)}%")
            c4.metric("Saldo de Gols", int(filtered_df['goalDifference'].values[0]))

    st.markdown("---")
    st.subheader("Comparativo de Pontuação")
    fig = px.bar(df.sort_values('points', ascending=False), 
                 x='team_name', y='points', 
                 color='points', color_continuous_scale='Blues')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"Classificação Completa: {selected_league_name}")
    st.dataframe(
        df[['position', 'team_name', 'playedGames', 'won', 'draw', 'lost', 'points', 'goalDifference', 'goals_per_game']], 
        use_container_width=True, hide_index=True
    )
else:
    st.error("Não foi possível carregar os dados. Verifique a API_KEY.")