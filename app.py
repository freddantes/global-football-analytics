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

def get_data_by_date(league_code, date_str):
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "gold", date_str, f"{league_code}_{date_str}.parquet")
    if os.path.exists(file_path):
        return pd.read_parquet(file_path)
    return None

def get_latest_data(league_code):
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "gold")
    if not os.path.exists(base_dir): return fetch_data(league_code), None, None
    
    dates = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))], reverse=True)
    if not dates: return fetch_data(league_code), None, None
    
    df_now = get_data_by_date(league_code, dates[0])
    df_past = get_data_by_date(league_code, dates[1]) if len(dates) > 1 else None
    return df_now, dates[0], df_past

selected_league_name = st.sidebar.selectbox("Selecione a Competição:", list(LEAGUES.keys()))
league_code = LEAGUES[selected_league_name]
df, date_now, df_past = get_latest_data(league_code)

if df is not None:
    # Lógica de Volatilidade
    if df_past is not None:
        comparison = df[['team_name', 'position']].merge(
            df_past[['team_name', 'position']], on='team_name', suffixes=('_now', '_past')
        )
        comparison['delta'] = comparison['position_past'] - comparison['position_now']
        df = df.merge(comparison[['team_name', 'delta']], on='team_name', how='left')
    else:
        df['delta'] = 0

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
            c1.metric("Posição", int(filtered_df['position'].values[0]), delta=int(filtered_df['delta'].values[0]))
            c2.metric("Pontos", int(filtered_df['points'].values[0]))
            c3.metric("Gols/Jogo", filtered_df['goals_per_game'].values[0])
            c4.metric("Aproveitamento", f"{int(filtered_df['points_pct'].values[0]*100)}%")

    st.markdown("---")
    
    # Análise de Tendência Histórica
    st.subheader(f"Tendência de Posição: {selected_team}")
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "gold")
    dates = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])
    
    history = []
    for date in dates:
        df_hist = get_data_by_date(league_code, date)
        if df_hist is not None and selected_team in df_hist['team_name'].values:
            pos = df_hist[df_hist['team_name'] == selected_team]['position'].values[0]
            history.append({'data': date, 'posicao': pos})
    
    if history:
        df_history = pd.DataFrame(history)
        fig_trend = px.line(df_history, x='data', y='posicao', markers=True)
        fig_trend.update_yaxes(autorange="reversed") 
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Histórico insuficiente para gerar gráfico de tendência.")

    st.markdown("---")
    st.subheader("Comparativo de Pontuação")
    fig = px.bar(df.sort_values('points', ascending=False), 
                 x='team_name', y='points', 
                 color='points', color_continuous_scale='Blues')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"Classificação Completa: {selected_league_name}")
    st.dataframe(
        df[['position', 'delta', 'team_name', 'playedGames', 'won', 'draw', 'lost', 'points', 'goalDifference', 'goals_per_game']], 
        use_container_width=True, hide_index=True
    )
else:
    st.error("Não foi possível carregar os dados. Verifique a API_KEY.")