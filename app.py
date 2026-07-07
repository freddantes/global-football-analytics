import streamlit as st
import pandas as pd
import os

# Configuração da página para um visual profissional
st.set_page_config(page_title="Premier League Dashboard", layout="wide")

st.title("⚽ Premier League Dashboard")
st.markdown("---")

# Caminho do arquivo parquet gerado pelo pipeline
DATA_PATH = "data/gold/kpis.parquet"

def load_data():
    if os.path.exists(DATA_PATH):
        return pd.read_parquet(DATA_PATH)
    else:
        return None

df = load_data()

if df is not None:
    # Barra lateral para o filtro de times
    st.sidebar.header("Filtros")
    team_list = sorted(df['team_name'].unique())
    selected_team = st.sidebar.selectbox("Selecione um time:", team_list)

    # Filtragem dos dados para o time selecionado
    filtered_df = df[df['team_name'] == selected_team]

    # Layout de exibição com imagem e métricas
    col_img, col_info = st.columns([1, 4])
    
    with col_img:
        # Exibe o escudo do time
        st.image(filtered_df['team_crest'].values[0], width=150)
        
    with col_info:
        st.subheader(f"Perfil: {selected_team}")
        
        # Linha de métricas rápidas
        c1, c2, c3 = st.columns(3)
        c1.metric("Pontos", filtered_df['points'].values[0])
        c2.metric("Jogos", filtered_df['playedGames'].values[0])
        c3.metric("Saldo de Gols", filtered_df['goalDifference'].values[0])

    st.markdown("---")
    st.subheader("Dados Detalhados")
    st.dataframe(filtered_df, use_container_width=True)

else:
    st.error("Erro: Arquivo de dados não encontrado.")
    st.info("Certifique-se de que o pipeline rodou com sucesso para gerar o arquivo 'data/gold/kpis.parquet'.")