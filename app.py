# --- BLOCO 1: IMPORTS E CONFIGURAÇÃO ---
import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from fpdf import FPDF
from datetime import datetime

# Configuração da Página (War Room Theme)
st.set_page_config(
    page_title="Market Mapping - Concorrência",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🎯"
)

# Paleta Semântica e Ordem
WAR_PALETTE = ["#bdc3c7", "#f39c12", "#e67e22", "#c0392b"]
ORDER_TIER = ['Micro Corretor', 'PME (Concorrente Direto)', 'Assessoria/Consolidadora', 'Big Player/Multinacional']
COLOR_MAP = {k: v for k, v in zip(ORDER_TIER, WAR_PALETTE)}

# --- BLOCO 2: CARGA DE DADOS ---
@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'competitors_processed.parquet')

    if not os.path.exists(file_path):
        st.error(f"Base de dados não encontrada em: {file_path}. Rode o script de ETL primeiro.")
        st.stop()

    df = pd.read_parquet(file_path)
    
    # Tratamentos de segurança caso as colunas não tenham sido criadas no ETL base
    if 'is_shark' not in df.columns:
        df['is_shark'] = df['tier_concorrente'].isin(['Big Player/Multinacional', 'Big Player / Multinacional']).astype(int)
    if 'bairro_norm' not in df.columns and 'bairro' in df.columns:
        df['bairro_norm'] = df['bairro'].astype(str).str.lower().str.strip()
    else:
        df['bairro_norm'] = 'nao_informado'
        
    return df

# --- BLOCO 3: SIDEBAR (FILTROS) ---
def sidebar_filters(df: pd.DataFrame):
    st.sidebar.markdown("## 🎯 Radar Tático")
    st.sidebar.markdown("Filtre sua área de atuação:")
    
    # Filtro de Estado
    lista_ufs = [str(x) for x in df['uf_norm'].dropna().unique().tolist()]
    opts_uf = ["Todos"] + sorted(lista_ufs)
    sel_uf = st.sidebar.selectbox("Estado (UF)", opts_uf, index=0)
    
    df_filtered = df.copy()
    sel_cidade = "Todas"
    
    if sel_uf != "Todos":
        df_filtered = df_filtered[df_filtered['uf_norm'] == sel_uf]
        
        # Filtro de Cidade
        lista_cidades = [str(x) for x in df_filtered['municipio_norm'].dropna().unique().tolist()]
        opts_cidade = ["Todas"] + sorted(lista_cidades)
        sel_cidade = st.sidebar.selectbox("Cidade", opts_cidade, index=0)
        
        if sel_cidade != "Todas":
            df_filtered = df_filtered[df_filtered['municipio_norm'] == sel_cidade]

    # Filtro de Porte (Tier)
    opts_tier = ORDER_TIER
    sel_tier = st.sidebar.multiselect("Porte do Concorrente", opts_tier, default=opts_tier)
    
    if sel_tier:
        df_filtered = df_filtered[df_filtered['tier_concorrente'].isin(sel_tier)]
        
    return df_filtered, sel_uf, sel_cidade

# --- BLOCO 4: GERAÇÃO DE PDF (REPORTE EXECUTIVO) ---
def generate_pdf(df_city: pd.DataFrame, cidade: str, estado: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Cabeçalho
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(192, 57, 43)
    pdf.cell(0, 10, f"Dossie de Concorrencia: {cidade.upper()} - {estado.upper()}", align="C", ln=1)
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y')} | Alvos mapeados: {len(df_city)}", align="C", ln=1)
    pdf.ln(5)
    
    # Resumo do Mercado Local
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, "1. TOP RIVAIS DIRETOS (Tier PME - Concorrencia Frontal)", ln=1)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(0, 5, "As empresas listadas abaixo representam a sua concorrencia direta. Elas possuem porte semelhante (PME) e atuam no mesmo municipio. Utilize esta lista para benchmarking de produtos e estrategias comerciais.")
    pdf.ln(5)
    
    # Tabela TOP PMEs
    col_w = [70, 40, 40, 30]
    headers = ["Corretora (Nome)", "Bairro", "Capital (R$)", "Idade (Anos)"]
    
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, 1, align='C', fill=True, ln=(1 if i == 3 else 0))
    
    pdf.set_font("Arial", "", 8)
    # Filtra as PMEs da cidade
    df_pmes = df_city[df_city['tier_concorrente'].str.contains('PME', na=False)]
    df_pmes = df_pmes.sort_values('capital_social', ascending=False).head(15)
    
    if df_pmes.empty:
        pdf.cell(0, 10, "Nenhuma Corretora PME relevante encontrada neste filtro.", 1, align='C', ln=1)
    else:
        for _, r in df_pmes.iterrows():
            nome = str(r.get('razao_social', 'N/D'))[:35].encode('latin-1', 'replace').decode('latin-1')
            bairro = str(r.get('bairro_norm', 'N/D')).title()[:20].encode('latin-1', 'replace').decode('latin-1')
            cap = f"{r.get('capital_social', 0):,.0f}"
            idade = f"{r.get('idade_empresa_anos', 0):.1f}"
            
            pdf.cell(col_w[0], 7, nome, 1)
            pdf.cell(col_w[1], 7, bairro, 1, align='C')
            pdf.cell(col_w[2], 7, cap, 1, align='R')
            pdf.cell(col_w[3], 7, idade, 1, align='C', ln=1)
            
    return bytes(pdf.output())

# --- BLOCO 5: APP MAIN ---
def main():
    st.markdown("<h1 style='text-align: center; color: #c0392b;'>🎯 Dossiê de Inteligência Competitiva</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background-color: #1E1E1E; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid #c0392b;'>
        <p style='color: #E0E0E0; font-size: 16px; margin: 0;'>
            <b>Contexto Estratégico:</b> Mapeamento de saturação do mercado de Seguros B2B. 
            Identifique oceanos azuis (baixa concorrência), monitore os <i>Big Players</i> e encontre seus rivais diretos através de análises de vizinhança geomercadológica.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = load_data()
    df_filtered, sel_uf, sel_cidade = sidebar_filters(df)
    
    if df_filtered.empty:
        st.warning("Sem dados para os filtros aplicados. Tente ampliar a busca.")
        return

    # --- KPIs RÁPIDOS ---
    total = len(df_filtered)
    sharks = df_filtered['is_shark'].sum()
    mediana_cap = df_filtered['capital_social'].median()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Volume de Corretores", f"{total:,}")
    col2.metric("Big Players (Tubarões)", f"{sharks:,}")
    col3.metric("Capital Social Mediano", f"R$ {mediana_cap:,.0f}")
    col4.metric("Idade Média", f"{df_filtered['idade_empresa_anos'].mean():.1f} anos")
    
    st.markdown("---")
    
    # --- ORGANIZAÇÃO EM ABAS (STORYTELLING) ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌍 Matriz de Competitividade", 
        "🏙️ Visão Micro (Bairros)", 
        "📊 Perfil de Mercado", 
        "📋 Rivais e Exportação"
    ])

    # ==========================================
    # ABA 1: VISÃO MACRO E LÓGICA CONDICIONAL DE VISUALIZAÇÃO
    # ==========================================
    with tab1:
        # LÓGICA 1: VISÃO NACIONAL TOTAL (MAPA DE CALOR)
        if sel_uf == "Todos" and sel_cidade == "Todas":
            st.markdown("### 🔥 Densidade Estrutural do Mercado Nacional")
            st.markdown("*Matriz cruzando Volume Geográfico e Estrutura de Porte Organizacional.*")
            
            # Prepara dados para o Heatmap Pivotado
            df_heat = df_filtered.groupby(['uf_norm', 'tier_concorrente']).size().unstack(fill_value=0)
            
            # Ordenação de colunas pela semântica de risco
            cols_avail = [c for c in ORDER_TIER if c in df_heat.columns]
            df_heat = df_heat[cols_avail]
            
            # Seleciona os top 15 estados por volume total para evitar poluição visual
            df_heat['Total_Volume'] = df_heat.sum(axis=1)
            df_heat = df_heat.sort_values('Total_Volume', ascending=True).tail(15).drop(columns=['Total_Volume'])
            
            fig_heat = px.imshow(
                df_heat,
                labels=dict(x="Hierarquia de Porte", y="Estado (UF)", color="Volume Absoluto"),
                x=df_heat.columns,
                y=df_heat.index,
                text_auto=True,
                color_continuous_scale="Reds",
                aspect="auto",
                title="Heatmap de Saturação Institucional: Top 15 Estados"
            )
            fig_heat.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
            st.plotly_chart(fig_heat, use_container_width=True)

        # LÓGICA 2: VISÃO ESTADUAL (DISPERSÃO DE MUNICÍPIOS)
        elif sel_uf != "Todos" and sel_cidade == "Todas":
            st.markdown(f"### 📍 Matriz Geográfica: Oceanos Azuis vs Vermelhos em {sel_uf}")
            st.markdown("*Dispersão de municípios avaliando Volume Bruto vs Ameaça de Tubarões.*")
            
            city_matrix = df_filtered.groupby('municipio_norm').agg(
                total=('cnpj_completo', 'count'),
                sharks=('is_shark', 'sum'),
                ticket=('capital_social', 'median')
            ).reset_index()
            
            city_matrix = city_matrix[city_matrix['total'] > 5].sort_values('total', ascending=False).head(20)
            
            if not city_matrix.empty:
                fig_scatter = px.scatter(
                    city_matrix, x='total', y='sharks', size='sharks', color='ticket',
                    hover_name='municipio_norm', size_max=40, text='municipio_norm',
                    title=f'Saturação Local vs Concentração de Big Players',
                    labels={'total': 'Total de Corretores (Pulverização)', 'sharks': 'Qtd Big Players (Consolidação)', 'ticket': 'Capital Mediano Estrutural'},
                    color_continuous_scale='Reds'
                )
                fig_scatter.update_traces(textposition='top center')
                fig_scatter.add_hline(y=city_matrix['sharks'].mean(), line_dash="dot", annotation_text="Média de Tubarões")
                fig_scatter.add_vline(x=city_matrix['total'].mean(), line_dash="dot", annotation_text="Média de Pulverização")
                fig_scatter.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=550)
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("Municípios insuficientes no filtro para gerar a matriz de dispersão robusta.")

        # LÓGICA 3: VISÃO MUNICIPAL (KNN CLUSTERING E BENCHMARKING DE PEERS)
        elif sel_cidade != "Todas":
            st.markdown(f"### 🧬 Benchmarking Dinâmico de Similaridade: {sel_cidade}")
            st.markdown(f"*Identificamos 5 municípios dentro de {sel_uf} com assinatura mercadológica matematicamente semelhante para mapeamento de estratégias.*")
            
            # Puxa o dataset inteiro do Estado alvo (sem o filtro local) para avaliar distâncias
            df_state_baseline = df[df['uf_norm'] == sel_uf]
            city_matrix_full = df_state_baseline.groupby('municipio_norm').agg(
                total=('cnpj_completo', 'count'),
                sharks=('is_shark', 'sum'),
                ticket=('capital_social', 'median')
            ).reset_index()
            
            # Isola os indicadores do alvo para o cálculo euclidiano
            sel_stats = city_matrix_full[city_matrix_full['municipio_norm'] == sel_cidade]
            
            if not sel_stats.empty:
                val_total = sel_stats['total'].values[0]
                val_sharks = sel_stats['sharks'].values[0]
                
                # Cálculo de Distância Euclidiana Simplificada 
                # Pondera-se as anomalias numéricas entre volume bruto e tubarões raros
                city_matrix_full['dist_euclidiana'] = np.sqrt(
                    ((city_matrix_full['total'] - val_total) ** 2) + 
                    (((city_matrix_full['sharks'] - val_sharks) * 5) ** 2) 
                )
                
                # Isola a cidade alvo e seus 5 vizinhos estatísticos mais próximos
                peer_cluster = city_matrix_full.sort_values('dist_euclidiana').head(6).copy()
                peer_cluster['Classificação de Peer'] = peer_cluster['municipio_norm'].apply(
                    lambda x: 'Alvo Estratégico' if x == sel_cidade else 'Peer Regional (Similar)'
                )
                
                fig_peers = px.scatter(
                    peer_cluster, x='total', y='sharks', size='ticket', color='Classificação de Peer',
                    hover_name='municipio_norm', size_max=45, text='municipio_norm',
                    title=f'Comportamento do Ecossistema: {sel_cidade} vs Peers Competitivos',
                    labels={'total': 'Volume de Players', 'sharks': 'Presença de Big Players', 'ticket': 'Capitalização Mediana'},
                    color_discrete_map={'Alvo Estratégico': '#c0392b', 'Peer Regional (Similar)': '#f39c12'}
                )
                fig_peers.update_traces(textposition='top center', textfont=dict(size=14, color='white'))
                fig_peers.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
                st.plotly_chart(fig_peers, use_container_width=True)
            else:
                st.info("Volume amostral subcrítico para cálculo de vizinhança geomercadológica.")

    # ==========================================
    # ABA 2: VISÃO MICRO (Bairros e Território)
    # ==========================================
    with tab2:
        st.markdown("### 🏘️ Ecossistema de Bairros (Stacked Bar)")
        st.markdown("Descubra a predominância estrutural: Identifique zonas de alta concentração PME versus clusters de multinacionais.")
        
        if sel_cidade != "Todas":
            bairros_data = df_filtered[df_filtered['bairro_norm'] != 'nao_informado']
            top_bairros = bairros_data['bairro_norm'].value_counts().head(15).index.tolist()
            bairros_top = bairros_data[bairros_data['bairro_norm'].isin(top_bairros)]
            
            if not bairros_top.empty:
                bairros_tier = bairros_top.groupby(['bairro_norm', 'tier_concorrente']).size().reset_index(name='count')
                
                fig_bairros = px.bar(
                    bairros_tier, x='count', y='bairro_norm', color='tier_concorrente',
                    title=f'Perfil de Ocupação da Concorrência por Bairro em {sel_cidade}',
                    orientation='h', color_discrete_map=COLOR_MAP,
                    category_orders={"bairro_norm": top_bairros}
                )
                fig_bairros.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=600)
                st.plotly_chart(fig_bairros, use_container_width=True)
            else:
                st.info("Resolução geográfica de bairros insuficiente na base de dados desta cidade.")
        else:
            st.warning("⚠️ O Raio-X de Bairros exige a seleção de uma cidade específica no menu lateral de comando.")

    # ==========================================
    # ABA 3: PERFIL DE MERCADO (Donut e Sobrevivência)
    # ==========================================
    with tab3:
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("### 🍩 Proporção Hierárquica (Market Share)")
            df_tier = df_filtered['tier_concorrente'].value_counts().reset_index()
            df_tier.columns = ['tier', 'count']
            
            fig_donut = px.pie(
                df_tier, values='count', names='tier',
                hole=0.5, color='tier', color_discrete_map=COLOR_MAP,
                category_orders={'tier': ORDER_TIER}
            )
            fig_donut.update_traces(textposition='inside', textinfo='percent+label')
            fig_donut.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_donut, use_container_width=True)

        with c2:
            st.markdown("### ⏳ Modelo de Sobrevivência Curva de Maturidade")
            data_plot = df_filtered[df_filtered['idade_empresa_anos'] <= 50]
            
            if not data_plot.empty:
                fig_hist, ax = plt.subplots(figsize=(8, 5))
                fig_hist.patch.set_facecolor('#1E1E1E')
                ax.set_facecolor('#1E1E1E')
                
                sns.histplot(data=data_plot, x='idade_empresa_anos', bins=30, kde=True, color='#c0392b', ax=ax)
                ax.axvline(5, color='orange', linestyle='--', linewidth=2, label="Early Stage (Novos)")
                ax.axvline(20, color='green', linestyle='--', linewidth=2, label="Legacy (Tradicionais)")
                
                ax.tick_params(colors='white')
                ax.xaxis.label.set_color('white')
                ax.yaxis.label.set_color('white')
                ax.title.set_color('white')
                ax.legend()
                
                st.pyplot(fig_hist)
            else:
                st.info("Dispersão temporal insuficiente para compilação do histograma de maturidade.")

    # ==========================================
    # ABA 4: EXPORTAÇÃO E RIVAIS DIRETOS
    # ==========================================
    with tab4:
        st.markdown("### 🎯 Lista Ouro: Rivais Diretos (PME Target Filter)")
        st.markdown("Ruído operacional removido. Listagem focada no segmento de Corretoras Estabelecidas que disputam a mesma base clientelar corporativa PME.")
        
        df_rivals = df_filtered[df_filtered['tier_concorrente'].str.contains('PME', na=False)]
        df_rivals = df_rivals.sort_values(by=['capital_social', 'idade_empresa_anos'], ascending=[False, False])
        
        cols_to_show = ['razao_social', 'municipio_norm', 'bairro_norm', 'perfil_ameaca', 'idade_empresa_anos', 'capital_social']
        cols_available = [c for c in cols_to_show if c in df_rivals.columns]
        
        st.dataframe(df_rivals[cols_available].head(50), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📥 Datalake & Output Executivo")
        
        c_dl1, c_dl2 = st.columns(2)
        
        with c_dl1:
            st.download_button(
                "💾 Extração Raw Data (CSV Filtrado)", 
                df_filtered.to_csv(index=False).encode('utf-8'), 
                f"base_concorrencia_{sel_uf}.csv", 
                "text/csv", 
                use_container_width=True
            )
            
        with c_dl2:
            if sel_cidade != "Todas":
                try:
                    pdf_bytes = generate_pdf(df_filtered, sel_cidade, sel_uf)
                    st.download_button(
                        "📄 Emissão de Dossiê Tático PME (PDF)", 
                        data=pdf_bytes, 
                        file_name=f"dossie_concorrencia_{sel_cidade}.pdf", 
                        mime="application/pdf", 
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro ao compilar o engine de renderização PDF: {e}")
            else:
                st.button("🔒 Requisito: Fixe um Município no Radar para desbloquear emissão de Dossiê PDF", disabled=True, use_container_width=True)

if __name__ == "__main__":

    main()
