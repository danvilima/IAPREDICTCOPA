import os
import sys
import altair as alt
import pandas as pd
import streamlit as st
import numpy as np

# Injetando o src no Path para imports limpos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Ponte de cloud secrets vs local enviroment
try:
    if "DATABASE_URL" in st.secrets and "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
except Exception:
    pass

from db import get_engine
from previsao import carregar_modelos, prever_jogo
from monte_carlo import preparar, simular_uma_vez
from bandeiras import com_bandeira

st.set_page_config(page_title="IAPredict — Copa 2026", layout="wide")
TOP_N = 12

# ==========================================
# CACHING DE MODELOS E CONEXÕES
# ==========================================
@st.cache_resource
def injetar_dependencias():
    engine = get_engine()
    carregar_modelos()
    df_jogos, df_grupos, df_mata = preparar()
    return engine, df_jogos, df_grupos, df_mata

@st.cache_data(ttl=3600)
def buscar_probabilidades():
    engine = get_engine()
    query = """
        SELECT selecao, prob_grupo, prob_oitavas, prob_quartas, prob_semi, prob_final, prob_campea
        FROM gold_probabilidades_copa
        ORDER BY prob_campea DESC
        LIMIT 12;
    """
    df = pd.read_sql(query, engine)
    df['selecao'] = df['selecao'].apply(com_bandeira)
    return df

engine, df_jogos, df_grupos, df_mata = injetar_dependencias()

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("⚽ Copa 2026 (AI)")
page = st.sidebar.radio("Navegação", ["Probabilidades Pré-computadas", "Simulação ao vivo", "Explorador de partidas"])

# ==========================================
# PÁGINA 1: PROBABILIDADES ESTÁVEIS
# ==========================================
if page == "Probabilidades Pré-computadas":
    st.title("🏆 Favoritas da Copa (Machine Learning)")
    st.markdown("Projeções oficiais consolidadas após simulação massiva de Monte Carlo (60.000 Copas). O modelo leva em consideração força recente de Elo e as complexidades de chaveamento da competição.")
    
    df_probs = buscar_probabilidades()
    
    # Prepara DF para o Altair (percentual puro para gráfico de barras visual)
    df_plot = df_probs.copy()
    df_plot['Chances de Título (%)'] = df_plot['prob_campea'] * 100
    
    chart = alt.Chart(df_plot).mark_bar().encode(
        x=alt.X('selecao:N', sort="-y", title="Seleção"),
        y=alt.Y('Chances de Título (%):Q', title="Probabilidade (%)"),
        tooltip=['selecao', 'Chances de Título (%)']
    ).properties(height=400)
    
    st.altair_chart(chart, use_container_width=True)
    
    # Tabela formato 0.00%
    st.markdown("### 📊 Raio-X por Fase do Torneio")
    format_pct = lambda x: f"{x:.1%}" if isinstance(x, float) else x
    df_display = df_probs.copy()
    for col in ['prob_grupo', 'prob_oitavas', 'prob_quartas', 'prob_semi', 'prob_final', 'prob_campea']:
        df_display[col] = df_display[col].apply(format_pct)
        
    df_display.columns = ["Seleção", "Grupos (R32)", "Oitavas", "Quartas", "Semifinal", "Final", "Campeã"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)

# ==========================================
# PÁGINA 2: SIMULADOR AO VIVO (UMA ITERAÇÃO)
# ==========================================
elif page == "Simulação ao vivo":
    st.title("🎲 Multiverso da Copa (Ao Vivo)")
    st.markdown("A cada clique, a Inteligência Artificial joga os dados matemáticos do Poisson gerando uma nova linha temporal exclusiva da Copa inteira.")
    
    if st.button("▶ Rodar Simulação Interativa!", type="primary"):
        # Garante a aleatoriedade destravando seeds
        np.random.seed(None)
        
        # Simula a copa completa de forma interativa
        with st.spinner("Gerando universos alternativos..."):
            # Para extrair detalhes, precisamos acoplar simular_uma_vez + coleta de rastros
            # Aqui recriaremos uma chamada envelopada para extrair quem enfrentou quem
            from monte_carlo import simular_torneio_detalhado
            resultado = simular_torneio_detalhado(df_jogos, df_grupos, df_mata)
            st.session_state['resultado_live'] = resultado
            
    if 'resultado_live' in st.session_state:
        res = st.session_state['resultado_live']
        podio = res['podio']
        
        # Pódio Highlight
        st.success(f"### 🥇 **CAMPEÃO:** {com_bandeira(podio.get('campeao', 'Unknown'))}")
        c1, c2 = st.columns(2)
        c1.info(f"🥈 Vice: {com_bandeira(podio.get('vice', 'Unknown'))}")
        c2.warning(f"🥉 Terceiro: {com_bandeira(podio.get('terceiro', 'Unknown'))}")
        
        # Mata-Mata Acordeão
        st.markdown("---")
        st.subheader("⚔️ Caminho do Mata-Mata")
        
        mata_data = res['mata_mata']
        etapas = [
            ("Final", 'FINAL'),
            ("Disputa 3º", '3RD_PLACE'),
            ("Semifinais", 'SF'),
            ("Quartas", 'QF'),
            ("Oitavas", 'R16'),
            ("32-Avos (R32)", 'R32')
        ]
        
        for titulo, chave in etapas:
            jogos_fase = mata_data.get(chave, [])
            if not jogos_fase: continue
                
            with st.expander(f"{titulo} ({len(jogos_fase)} jogos)", expanded=(chave=='FINAL')):
                for j in jogos_fase:
                    tc = com_bandeira(j['time_casa'])
                    tv = com_bandeira(j['time_visitante'])
                    gc = j['gols_casa']
                    gv = j['gols_visitante']
                    
                    texto_placar = f"{tc} **{gc} x {gv}** {tv}"
                    
                    if j['penaltis']:
                        pc = j['pen_casa']
                        pv = j['pen_visitante']
                        texto_placar += f" *(Pênaltis: {pc}-{pv})*"
                        
                    st.write(texto_placar)
                    
        # Grupos Acordeão
        st.markdown("---")
        st.subheader("📋 Classificação dos Grupos")
        df_g = res['grupos'].copy()
        
        # Traduzindo colunas como mandatório na spec
        df_g['selecao'] = df_g['selecao'].apply(com_bandeira)
        cols_pt = ['grupo', 'posicao', 'selecao', 'jogos', 'vitorias', 'empates', 'derrotas', 'gols_pro', 'gols_contra', 'saldo_gols', 'pontos']
        df_g = df_g[cols_pt]
        
        for g, df_grupo in df_g.groupby('grupo'):
            with st.expander(f"Grupo {g}"):
                st.dataframe(df_grupo.drop('grupo', axis=1).style.highlight_max(subset=['pontos']), hide_index=True, use_container_width=True)

# ==========================================
# PÁGINA 3: EXPLORADOR DE PARTIDAS 1v1
# ==========================================
elif page == "Explorador de partidas":
    st.title("🔬 Explorador de xG (Expected Goals)")
    st.markdown("Escolha duas equipes para invocar o cérebro preditivo de Poisson puro.")
    
    todas = sorted(list(df_grupos['nation'].unique()))
    
    col1, col2 = st.columns(2)
    with col1:
        time1 = st.selectbox("Mandante (Casa)", options=todas, index=todas.index('Brazil') if 'Brazil' in todas else 0, format_func=com_bandeira)
    with col2:
        time2 = st.selectbox("Visitante (Fora)", options=todas, index=todas.index('France') if 'France' in todas else 1, format_func=com_bandeira)
        
    eh_neutro = st.checkbox("🏟️ Campo Neutro (Retira viés de casa/fora)")
    
    if st.button("🔮 Calcular Estimativa"):
        # Chamada pura da F07 sem PESO_TORNEIO
        resultado = prever_jogo(time1, time2, neutro=eh_neutro)
        
        st.markdown("---")
        st.markdown(f"### {com_bandeira(time1)} ⚔️ {com_bandeira(time2)}")
        
        c1, c2 = st.columns(2)
        c1.metric(f"xG (Gols Esperados) {time1}", f"{resultado['gols_esperados_casa']:.2f}")
        c2.metric(f"xG (Gols Esperados) {time2}", f"{resultado['gols_esperados_visitante']:.2f}")
        
        st.markdown("#### Chance de Resultado:")
        p_v = resultado['prob_vitoria']
        p_e = resultado['prob_empate']
        p_d = resultado['prob_derrota']
        
        # Gráfico de gauge simples (Barras horizontais)
        st.progress(p_v, text=f"Vitória {time1} ({p_v:.1%})")
        st.progress(p_e, text=f"Empate ({p_e:.1%})")
        st.progress(p_d, text=f"Vitória {time2} ({p_d:.1%})")
