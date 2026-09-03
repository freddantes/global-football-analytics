import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import pyarrow.dataset as ds
import gcsfs

from src.analytics import get_match_predictions

st.set_page_config(page_title="Dashboard Global de Futebol", layout="wide")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

LEAGUES = {
    "Premier League": "PL", "Copa do Mundo": "WC", "Champions League": "CL",
    "Mundial de Clubes": "FCWC", "Libertadores": "CLI", "Brasileirão Série A": "BSA",
    "La Liga": "PD", "Ligue 1": "FL1", "Serie A Italiana": "SA", "Bundesliga": "BL1"
}

@st.cache_resource
def get_gcs_filesystem():
    try:
        if "gcp_service_account" in st.secrets:
            gcp_cred = dict(st.secrets["gcp_service_account"])
            return gcsfs.GCSFileSystem(token=gcp_cred)
    except Exception as e:
        st.warning(f"Erro ao carregar secrets, usando credenciais padrão. Detalhe: {e}")
    return gcsfs.GCSFileSystem()

# ==========================================
# CACHE OTIMIZADO COM TTL (Expira em 1 hora para liberar RAM)
# ==========================================
@st.cache_data(ttl=3600, show_spinner="Lendo dados otimizados do Data Lake...")
def load_standings_via_duckdb(league_code: str):
    bucket_path = "futebol-datalake-global-analytics-2026/data/gold/standings"
        
    try:
        fs = get_gcs_filesystem()
        arquivos = fs.glob(f"{bucket_path}/**/*.parquet")
        if not arquivos:
            return None
            
        arquivos.sort(reverse=True)
        
        import pyarrow.parquet as pq
        import pyarrow as pa
        
        with fs.open(arquivos[0]) as f:
            esquema_atualizado = pq.read_schema(f)
        
        if 'date' not in esquema_atualizado.names:
            esquema_atualizado = esquema_atualizado.append(pa.field('date', pa.string()))
        if 'league_code' not in esquema_atualizado.names:
            esquema_atualizado = esquema_atualizado.append(pa.field('league_code', pa.string()))
        
        dataset = ds.dataset(
            bucket_path, 
            format="parquet", 
            filesystem=fs, 
            partitioning="hive",
            schema=esquema_atualizado
        )
        
        # Filtro direto na query para puxar apenas a liga selecionada, economizando memória
        query = f"SELECT * FROM dataset WHERE league_code = '{league_code}'"
        df = duckdb.query(query).to_df()
        
        if df.empty:
            return None
        return df
        
    except Exception as e:
        st.error(f"Erro ao conectar com o Data Lake: {e}")
        return None

# ==========================================
# UI: NAVEGAÇÃO PRINCIPAL (ESTILO MODERNO)
# ==========================================
st.markdown("### 🧭 Menu Principal")

opcoes_menu = ["📊 Classificação", "🎯 Simulador Quantitativo", "📖 Metodologia Técnica"]

if hasattr(st, 'pills'):
    pagina_selecionada = st.pills("Navegação:", opcoes_menu, default="📊 Classificação", label_visibility="collapsed")
    if not pagina_selecionada: 
        pagina_selecionada = "📊 Classificação"
else:
    pagina_selecionada = st.radio("Navegação:", opcoes_menu, horizontal=True, label_visibility="collapsed")

st.markdown("---")

# ==========================================
# UI: FILTRO MACRO (COMPETIÇÃO)
# ==========================================
if pagina_selecionada in ["📊 Classificação", "🎯 Simulador Quantitativo"]:
    st.markdown("### ⚙️ Seleção de Campeonato")
    selected_league_name = st.selectbox("Escolha a Competição:", list(LEAGUES.keys()), label_visibility="collapsed")
    league_code = LEAGUES[selected_league_name]

    with st.spinner("Lendo dados do Data Lake no Google Cloud..."):
        df_league_history = load_standings_via_duckdb(league_code)
    
    st.markdown("---")

# ==========================================
# RENDERIZAÇÃO DAS PÁGINAS
# ==========================================

if pagina_selecionada == "📊 Classificação":
    
    if df_league_history is not None and not df_league_history.empty:
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

        # ---------------------------------------------------------
        # PARTE 1: VISÃO GERAL DO CAMPEONATO
        # ---------------------------------------------------------
        st.title(f"🏆 Visão Geral: {selected_league_name}")
        
        st.subheader("Comparativo de Pontuação")
        fig = px.bar(
            df.sort_values('points', ascending=False), 
            x='team_name', y='points', 
            color='points', color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, width="stretch")

        st.subheader("Tabela de Classificação Completa")
        df_display = df[['position', 'delta', 'team_name', 'playedGames', 'won', 'draw', 'lost', 'points', 'goalDifference', 'goals_per_game']].copy()
        df_display['goals_per_game'] = df_display['goals_per_game'].round(2)
        st.dataframe(df_display, width="stretch", hide_index=True)
        
        st.markdown("---")

        # ---------------------------------------------------------
        # PARTE 2: VISÃO ESPECÍFICA DO TIME
        # ---------------------------------------------------------
        st.title("🔍 Análise Individual da Equipe")
        team_list = sorted(df['team_name'].unique())
        selected_team = st.selectbox("Selecione a Equipe para detalhar:", team_list)
        
        filtered_df = df[df['team_name'] == selected_team]

        
        with st.container(border=True):
            col_img, col_info = st.columns([1, 5])
            
            with col_img:
                # O DETETIVE DE ESCUDOS: Procura pelas colunas mais comuns vindas da API
                coluna_imagem = None
                for col_name in ['crest', 'team_crest', 'logo', 'team_logo']:
                    if col_name in filtered_df.columns:
                        coluna_imagem = col_name
                        break
                
                if coluna_imagem:
                    crest_url = filtered_df[coluna_imagem].values[0]
                    if pd.notna(crest_url) and str(crest_url).strip() != "":
                        st.image(crest_url, width=100)
                    else:
                        st.markdown("🛡️ *Escudo não disponível*")
                else:
                    st.markdown("🛡️ *Escudo não disponível*")
            
            with col_info:
                st.subheader(selected_team)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Posição", int(filtered_df['position'].values[0]), delta=int(filtered_df['delta'].values[0]))
                c2.metric("Pontos", int(filtered_df['points'].values[0]))
                
                gols_por_jogo = float(filtered_df['goals_per_game'].values[0])
                c3.metric("Gols/Jogo", f"{gols_por_jogo:.2f}")
                
                c4.metric("Aproveitamento", f"{int(filtered_df['points_pct'].values[0]*100)}%")

        st.subheader(f"Tendência de Posição")
        try:
            fs_trend = get_gcs_filesystem()
            dataset_trend = ds.dataset("futebol-datalake-global-analytics-2026/data/gold/standings", format="parquet", filesystem=fs_trend, partitioning="hive")
            
            team_history_query = f"""
                SELECT playedGames as rodada, position as posicao 
                FROM dataset_trend 
                WHERE league_code = '{league_code}' AND team_name = '{selected_team}' 
                ORDER BY date ASC
            """
            df_history = duckdb.query(team_history_query).to_df()
            
            if not df_history.empty and len(df_history) > 1:
                df_history = df_history.drop_duplicates(subset=['rodada'], keep='last')
                fig_trend = px.line(df_history, x='rodada', y='posicao', markers=True)
                fig_trend.update_yaxes(autorange="reversed") 
                fig_trend.update_xaxes(dtick=1)
                st.plotly_chart(fig_trend, width="stretch")
            else:
                st.info("Histórico insuficiente para gerar gráfico de tendência por rodadas.")
        except Exception:
            pass
        
    else:
        st.warning("Nenhuma partição de classificação encontrada. Verifique o Data Lake.")

elif pagina_selecionada == "🎯 Simulador Quantitativo":
    st.title("🎯 Simulador Quantitativo (Distribuição de Poisson)")
    st.markdown("Calcula probabilidades baseadas na Força de Ataque e Defesa histórica de cada equipe, processadas via DuckDB e balanceadas pelo decaimento temporal (*Time Decay*).")
    
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
            st.markdown("---")
            st.markdown("### 💰 Analisador de Valor Esperado (+EV)")
            st.markdown("Insira as *Odds* (cotações) oferecidas pela casa de apostas para verificar se há vantagem matemática sobre o mercado.")
            
            # Entradas de Dados para as Cotações
            col_odd1, col_oddX, col_odd2 = st.columns(3)
            with col_odd1:
                odd_home = st.number_input(f"Odd Vitória {home_team_model}:", min_value=1.01, value=2.00, step=0.05)
            with col_oddX:
                odd_draw = st.number_input("Odd Empate:", min_value=1.01, value=3.00, step=0.05)
            with col_odd2:
                odd_away = st.number_input(f"Odd Vitória {away_team_model}:", min_value=1.01, value=2.00, step=0.05)

            st.markdown("---")

            if st.button("Executar Modelo Preditivo", type="primary", use_container_width=True):
                with st.spinner("Processando estatísticas matemáticas e comparando com o mercado..."):
                    preds = get_match_predictions(league_code, home_team_model, away_team_model)
                    
                    if preds:
                        # Convertendo as porcentagens para decimais padrão (ex: 45.5% vira 0.455)
                        prob_home_decimal = preds['home_win_pct'] / 100
                        prob_draw_decimal = preds['draw_pct'] / 100
                        prob_away_decimal = preds['away_win_pct'] / 100

                        # Fórmula Matemática do Expected Value (EV)
                        ev_home = (prob_home_decimal * odd_home) - 1
                        ev_draw = (prob_draw_decimal * odd_draw) - 1
                        ev_away = (prob_away_decimal * odd_away) - 1

                        st.markdown("### 📊 Probabilidades do Confronto (Moneyline)")
                        mc1, mc2, mc3 = st.columns(3)
                        mc1.metric(f"Vitória - {home_team_model}", f"{preds['home_win_pct']}%")
                        mc2.metric("Empate", f"{preds['draw_pct']}%")
                        mc3.metric(f"Vitória - {away_team_model}", f"{preds['away_win_pct']}%")
                        
                        # Bloco Visual do Radar de Oportunidades (+EV)
                        st.markdown("### 🚨 Radar de Valor Esperado (EV)")
                        
                        ev_found = False 
                        
                        if ev_home > 0:
                            st.success(f"**🔥 OPORTUNIDADE (+EV):** Apostar no **{home_team_model}** tem um retorno esperado de **+{ev_home*100:.2f}%** a longo prazo.")
                            ev_found = True
                            
                        if ev_draw > 0:
                            st.success(f"**🔥 OPORTUNIDADE (+EV):** Apostar no **Empate** tem um retorno esperado de **+{ev_draw*100:.2f}%** a longo prazo.")
                            ev_found = True
                            
                        if ev_away > 0:
                            st.success(f"**🔥 OPORTUNIDADE (+EV):** Apostar no **{away_team_model}** tem um retorno esperado de **+{ev_away*100:.2f}%** a longo prazo.")
                            ev_found = True

                        if not ev_found:
                            st.warning("⚠️ **Nenhuma oportunidade detectada (-EV).** As cotações da casa não possuem margem de valor frente às estatísticas. Fique de fora.")

                        st.markdown("---")
                        st.markdown("### 🎯 Mercado de Gols (Prop Bets)")
                        pc1, pc2, pc3 = st.columns(3)
                        pc1.metric("Expected Goals (xG) Mandante", preds['home_xg'])
                        pc2.metric("Expected Goals (xG) Visitante", preds['away_xg'])
                        pc3.metric("Probabilidade Over 2.5 Gols", f"{preds['over_2_5_pct']}%")
                    else:
                        st.error("Histórico insuficiente na tabela de partidas para calcular a força de ataque/defesa destas equipes com segurança estatística.")
    else:
        st.warning("Nenhum dado encontrado para alimentar o modelo matemático.")

elif pagina_selecionada == "📖 Metodologia Técnica":
    st.title("📖 Documentação e Arquitetura")
    try:
        with open("TECHNICAL_REPORT.md", "r", encoding="utf-8") as file:
            conteudo_markdown = file.read()
            
        st.write(conteudo_markdown)
        
    except FileNotFoundError:
        st.error("O arquivo TECHNICAL_REPORT.md não foi encontrado. Certifique-se de que ele está na mesma pasta raiz do projeto.")