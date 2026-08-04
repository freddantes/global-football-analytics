import streamlit as st
import pandas as pd
import duckdb
import os
import json
import plotly.express as px

# Importando o novo motor estatístico de Poisson
from src.analytics import get_match_predictions

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Dashboard Global de Futebol", layout="wide")

LEAGUES = {
    "Premier League": "PL", "Copa do Mundo": "WC", "Champions League": "CL",
    "Mundial de Clubes": "FCWC", "Libertadores": "CLI", "Brasileirão Série A": "BSA",
    "La Liga": "PD", "Ligue 1": "FL1", "Serie A Italiana": "SA", "Bundesliga": "BL1"
}

st.title("⚽ Dashboard Global de Futebol & Analytics")
st.markdown("---")

# ==========================================
# AUTENTICAÇÃO NO GOOGLE CLOUD (SECRETS)
# ==========================================
@st.cache_resource
def configure_gcp_credentials():
    """
    Lê a chave de segurança do Google Cloud (GCP) dos Secrets do Streamlit
    e cria um arquivo temporário de credenciais para autorizar a leitura dos dados.
    """
    if "gcp_service_account" in st.secrets:
        gcp_cred_dict = dict(st.secrets["gcp_service_account"])
        with open("google_credentials.json", "w") as f:
            json.dump(gcp_cred_dict, f)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
        return True
    return False

# Executa a configuração de credenciais logo ao abrir o app
configure_gcp_credentials()

# ==========================================
# EXTRAÇÃO DE DADOS (DATA LAKE NO GCP)
# ==========================================
@st.cache_data
def load_standings_via_duckdb(league_code: str):
    """
    Usa o DuckDB para consultar as partições Hive da tabela de classificação
    diretamente do Google Cloud Storage de forma ultra-rápida.
    """
    # Novo caminho apontando diretamente para o seu Bucket na nuvem
    parquet_path = "gs://futebol-datalake-global-analytics-2026/data/gold/standings/**/*.parquet"
        
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
    except Exception as e:
        st.error(f"Erro ao conectar com o Data Lake: {e}")
        return None

# Carrega todos os dados históricos da liga selecionada
selected_league_name = st.sidebar.selectbox("Selecione a Competição:", list(LEAGUES.keys()))
league_code = LEAGUES[selected_league_name]

# Criando as abas de navegação
tab_classificacao, tab_modelagem = st.tabs(["📊 Classificação Geral", "🎯 Modelagem & Prop Bets"])

with st.spinner("Lendo dados do Data Lake no Google Cloud..."):
    df_league_history = load_standings_via_duckdb(league_code)

# ==========================================
# ABA 1: CLASSIFICAÇÃO TRADICIONAL
# ==========================================
with tab_classificacao:
    if df_league_history is not None and not df_league_history.empty:
        # Identifica as datas disponíveis ordenadas cronologicamente
        if 'date' in df_league_history.columns:
            dates = sorted(df_league_history['date'].unique(), reverse=True)
        else:
            df_league_history['date'] = df_league_history['__file_path__'].apply(
                lambda x: x.split('date=')[1].split('/')[0] if 'date=' in x else 'latest'
            )
            dates = sorted(df_league_history['date'].unique(), reverse=True)

        latest_date = dates[0]
        past_date = dates[1] if len(dates) > 1 else None

        df = df_league_history[df_league_history['date'] == latest_date].copy()
        df_past = df_league_history[df_league_history['date'] == past_date].copy() if past_date else pd.DataFrame()

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
                        st.image(crest, width=150)
            with col_info:
                st.subheader(selected_team)
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
            FROM read_parquet('gs://futebol-datalake-global-analytics-2026/data/gold/standings/**/*.parquet', hive_partitioning=1)
            WHERE league_code = '{league_code}' AND team_name = '{selected_team}'
            ORDER BY date ASC
        """
        try:
            df_history = duckdb.query(team_history_query).to_df()
            if not df_history.empty and len(df_history) > 1:
                fig_trend = px.line(df_history, x='date', y='posicao', markers=True)
                fig_trend.update_yaxes(autorange="reversed") 
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("Histórico insuficiente para gerar gráfico de tendência.")
        except Exception:
            pass

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
        st.warning("Nenhuma partição de classificação encontrada. Execute o pipeline ETL.")

# ==========================================
# ABA 2: MODELAGEM QUANTITATIVA & PROP BETS
# ==========================================
with tab_modelagem:
    st.header("🔮 Simulador Quantitativo (Distribuição de Poisson)")
    st.markdown("Calcula probabilidades baseadas na Força de Ataque e Defesa histórica de cada equipe no campeonato, processadas via DuckDB.")
    
    if df_league_history is not None and not df_league_history.empty:
        team_list_model = sorted(df_league_history['team_name'].unique())
        
        col_home, col_away = st.columns(2)
        with col_home:
            home_team_model = st.selectbox("Mandante (Home):", team_list_model, index=0)
        with col_away:
            default_away_index = 1 if len(team_list_model) > 1 else 0
            away_team_model = st.selectbox("Visitante (Away):", team_list_model, index=default_away_index)
            
        if home_team_model == away_team_model:
            st.error("Por favor, selecione equipes diferentes para o confronto.")
        else:
            if st.button("Executar Modelo Preditivo", type="primary"):
                with st.spinner("Lendo histórico no Data Lake e processando estatísticas..."):
                    preds = get_match_predictions(league_code, home_team_model, away_team_model)
                    
                    if preds:
                        st.markdown("### 📊 Probabilidades do Confronto (Moneyline)")
                        mc1, mc2, mc3 = st.columns(3)
                        mc1.metric(f"Vitória - {home_team_model}", f"{preds['home_win_pct']}%")
                        mc2.metric("Empate", f"{preds['draw_pct']}%")
                        mc3.metric(f"Vitória - {away_team_model}", f"{preds['away_win_pct']}%")
                        
                        st.markdown("### 🎯 Mercado de Gols (Prop Bets)")
                        pc1, pc2, pc3 = st.columns(3)
                        pc1.metric("Expected Goals (xG) Mandante", preds['home_xg'])
                        pc2.metric("Expected Goals (xG) Visitante", preds['away_xg'])
                        pc3.metric("Prob. Over 2.5 Gols", f"{preds['over_2_5_pct']}%")
                    else:
                        st.warning("Histórico insuficiente na tabela de partidas para calcular a força de ataque/defesa destas equipes.")
    else:
        st.warning("Nenhum dado encontrado para alimentar o modelo matemático.")