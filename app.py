import streamlit as st
import pandas as pd
import duckdb
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

@st.cache_data
def load_standings_via_duckdb(league_code: str):
    """
    Usa o DuckDB para consultar as partições Hive da tabela de classificação
    de forma ultra-rápida, aplicando Partition Pruning automático.
    """
    parquet_path = os.path.join("data", "gold", "standings", "**", "*.parquet")
    if not os.path.exists(os.path.join("data", "gold", "standings")):
        return None
        
    query = f"""
        SELECT * 
        FROM read_parquet('{parquet_path}', hive_partitioning=1)
        WHERE league_code = '{league_code}'
    """
    try:
        df = duckdb.query(query).to_df()
        if df.empty:
            return None
        return df
    except Exception:
        return None

# Carrega todos os dados históricos da liga selecionada
selected_league_name = st.sidebar.selectbox("Selecione a Competição:", list(LEAGUES.keys()))
league_code = LEAGUES[selected_league_name]

df_league_history = load_standings_via_duckdb(league_code)

if df_league_history is not None and not df_league_history.empty:
    # Identifica as datas disponíveis ordenadas cronologicamente
    available_dates = sorted(df_league_history['date'].unique(), reverse=True) if 'date' in df_league_history.columns else sorted(df_league_history['__file_nameừ'].unique(), reverse=True)
    
    # Se a coluna 'date' não vier explícita pelo hive_partitioning, extraímos do caminho do arquivo
    # Garantimos a listagem de datas distinta presente no dataset
    dates = sorted(df_league_history['date'].unique(), reverse=True) if 'date' in df_league_history.columns else []
    
    if not dates:
        # Fallback caso a coluna date precise ser mapeada do path
        df_league_history['date'] = df_league_history['__file_path__'].apply(lambda x: x.split('date=')[1].split('/')[0] if 'date=' in x else 'latest')
        dates = sorted(df_league_history['date'].unique(), reverse=True)

    latest_date = dates[0]
    past_date = dates[1] if len(dates) > 1 else None

    # DataFrame da execução mais recente
    df = df_league_history[df_league_history['date'] == latest_date].copy()
    
    # DataFrame da execução anterior (para calcular o Delta de posição)
    df_past = df_league_history[df_league_history['date'] == past_date].copy() if past_date else pd.DataFrame()

    # Lógica de Volatilidade (Delta)
    if not df_past.empty:
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
            if 'team_crest' in filtered_df.columns:
                crest = filtered_df['team_crest'].values[0]
                if pd.notna(crest):
                    st.image(crest, width=200)
        with col_info:
            st.title(selected_team)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Posição", int(filtered_df['position'].values[0]), delta=int(filtered_df['delta'].values[0]))
            c2.metric("Pontos", int(filtered_df['points'].values[0]))
            c3.metric("Gols/Jogo", filtered_df['goals_per_game'].values[0])
            c4.metric("Aproveitamento", f"{int(filtered_df['points_pct'].values[0]*100)}%")

    st.markdown("---")
    
    # Gráfico de Tendência Histórica via DuckDB
    st.subheader(f"Tendência de Posição: {selected_team}")
    
    team_history_query = f"""
        SELECT date, position as posicao 
        FROM read_parquet('data/gold/standings/**/*.parquet', hive_partitioning=1)
        WHERE league_code = '{league_code}' AND team_name = '{selected_team}'
        ORDER BY date ASC
    """
    df_history = duckdb.query(team_history_query).to_df()
    
    if not df_history.empty and len(df_history) > 1:
        fig_trend = px.line(df_history, x='date', y='posicao', markers=True)
        fig_trend.update_yaxes(autorange="reversed") 
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Histórico insuficiente para gerar gráfico de tendência (execute o pipeline em dias diferentes para acumular histórico).")

    st.markdown("---")
    st.subheader("Comparativo de Pontuação")
    fig = px.bar(
        df.sort_values('points', ascending=False), 
        x='team_name', y='points', 
        color='points', color_continuous_scale='Blues'
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"Classificação Completa: {selected_league_name}")
    st.dataframe(
        df[['position', 'delta', 'team_name', 'playedGames', 'won', 'draw', 'lost', 'points', 'goalDifference', 'goals_per_game']], 
        use_container_width=True, hide_index=True
    )
else:
    st.warning("Nenhuma partição encontrada. Execute `python -m src.main` para popular o Data Lake.")