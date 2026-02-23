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

# Configuração da Página (Corporate Tech Theme)
st.set_page_config(
    page_title="Market Mapping - Setor de TI",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="💻"
)

# Paleta Semântica Tech
TECH_BLUE = "#005b96"
TECH_TEAL = "#00a896"

# --- BLOCO 2: CARGA DE DADOS ---
@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'it_market_processed.parquet')

    if not os.path.exists(file_path):
        st.error(f"Base de dados não encontrada em: {file_path}. Rode o script ETL primeiro.")
        st.stop()

    df = pd.read_parquet(file_path)
    return df

# --- BLOCO 3: SIDEBAR (FILTROS) ---
def sidebar_filters(df: pd.DataFrame):
    st.sidebar.markdown("## 🧭 Navegação Tática")
    st.sidebar.markdown("Filtre sua área de prospecção:")
    
    lista_ufs = [str(x) for x in df['uf_norm'].dropna().unique().tolist()]
    opts_uf = ["Todos"] + sorted(lista_ufs)
    
    # Pré-seleciona 'SP' se existir, pois é o foco do estudo
    default_uf_idx = opts_uf.index('sp') if 'sp' in opts_uf else 0
    sel_uf = st.sidebar.selectbox("Estado (UF)", opts_uf, index=default_uf_idx)
    
    df_filtered = df.copy()
    sel_cidade = "Todas"
    
    if sel_uf != "Todos":
        df_filtered = df_filtered[df_filtered['uf_norm'] == sel_uf]
        
        lista_cidades = [str(x) for x in df_filtered['municipio_norm'].dropna().unique().tolist()]
        opts_cidade = ["Todas"] + sorted(lista_cidades)
        sel_cidade = st.sidebar.selectbox("Cidade", opts_cidade, index=0)
        
        if sel_cidade != "Todas":
            df_filtered = df_filtered[df_filtered['municipio_norm'] == sel_cidade]

    # Filtro de Porte Jurídico
    if 'porte_descricao_norm' in df.columns:
        lista_porte = [str(x) for x in df['porte_descricao_norm'].unique().tolist()]
        sel_porte = st.sidebar.multiselect("Porte da Empresa (Target)", lista_porte, default=lista_porte)
        
        if sel_porte:
            df_filtered = df_filtered[df_filtered['porte_descricao_norm'].isin(sel_porte)]
        
    return df_filtered, sel_uf, sel_cidade

# --- BLOCO 4: GERAÇÃO DE PDF (REPORTE EXECUTIVO) ---
def generate_pdf(df_city: pd.DataFrame, cidade: str, estado: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Cabeçalho
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0, 91, 150) # Azul Tech
    pdf.cell(0, 10, f"Lista de Prospeccao B2B: {cidade.upper()} - {estado.upper()}", align="C", ln=1)
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y')} | Leads qualificados: {len(df_city)}", align="C", ln=1)
    pdf.ln(5)
    
    # Resumo
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, "1. GOLDEN LEADS (Top 15 Contas de TI)", ln=1)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(0, 5, "Empresas selecionadas com base em Alto Capital Social (Maior capacidade de pagamento) e Maior Maturidade (Menor risco de quebra nos 2 primeiros anos).")
    pdf.ln(5)
    
    # Tabela TOP Leads (CNPJ, Razao, Capital, Idade, Contato)
    col_w = [30, 65, 30, 15, 50]
    headers = ["CNPJ", "Razao Social", "Capital (R$)", "Anos", "Contato/Email"]
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(220, 230, 240) # Fundo Azul claro
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, 1, align='C', fill=True, ln=(1 if i == 4 else 0))
    
    pdf.set_font("Arial", "", 8)
    # Ordena pelo Capital e Idade
    df_leads = df_city.sort_values(by=['capital_social', 'idade_empresa_anos'], ascending=[False, False]).head(15)
    
    if df_leads.empty:
        pdf.cell(0, 10, "Nenhum lead encontrado neste filtro.", 1, align='C', ln=1)
    else:
        for _, r in df_leads.iterrows():
            cnpj = str(r.get('cnpj_completo', 'N/D'))
            nome = str(r.get('razao_social', 'N/D'))[:35].encode('latin-1', 'replace').decode('latin-1')
            cap = f"{r.get('capital_social', 0):,.0f}"
            idade = f"{r.get('idade_empresa_anos', 0):.1f}"
            
            # Monta contato 
            ddd = str(int(r['ddd_1'])) if pd.notnull(r.get('ddd_1')) else ""
            tel = str(int(r['telefone_1'])) if pd.notnull(r.get('telefone_1')) else ""
            telefone = f"({ddd}){tel}" if ddd and tel else ""
            email = str(r.get('email_contato', '')).split(',')[0][:25] if pd.notnull(r.get('email_contato')) else ""
            contato = f"{telefone} {email}".strip()
            if not contato: contato = "N/D"
            
            pdf.cell(col_w[0], 7, cnpj, 1, align='C')
            pdf.cell(col_w[1], 7, nome, 1)
            pdf.cell(col_w[2], 7, cap, 1, align='R')
            pdf.cell(col_w[3], 7, idade, 1, align='C')
            pdf.cell(col_w[4], 7, contato, 1, align='C', ln=1)
            
    # CORREÇÃO APLICADA: Retorna bytes puros nativos da nova FPDF2
# Compatibilidade Universal (Funciona no FPDF antigo e no FPDF2 novo)
    pdf_out = pdf.output(dest='S')
    if isinstance(pdf_out, str):
        return pdf_out.encode('latin-1') # Se for versão antiga (String)
    return bytes(pdf_out)                # Se for versão nova (Bytearray)
# --- BLOCO 5: APP MAIN ---
def main():
    st.markdown(f"<h1 style='text-align: center; color: {TECH_BLUE};'>💻 Inteligência de Mercado: TI & Seguros Saúde</h1>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='background-color: #f0f8ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid {TECH_BLUE};'>
        <p style='color: #333333; font-size: 16px; margin: 0;'>
            <b>Contexto Estratégico:</b> Mapeamento de empresas do setor de TI. 
            Direcione a força de vendas cruzando <b>Densidade de Leads</b> com <b>Perfil de Risco (Mortalidade)</b>, focando em Oceanos Azuis de alta estabilidade.
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
    idade_media = df_filtered['idade_empresa_anos'].mean()
    mediana_cap = df_filtered['capital_social'].median()
    
    # Identifica % de LTDA/S.A (empresas mais maduras estruturalmente = código 200+) vs MEI/EI
    if 'natureza_juridica' in df_filtered.columns:
        ltda_mask = df_filtered['natureza_juridica'].astype(str).str.startswith('2') 
        perc_ltda = (df_filtered[ltda_mask].shape[0] / total * 100) if total > 0 else 0
    else:
        perc_ltda = 0.0
    
    col1, col2, col3, col4 = st.columns(4)
    kpi_style = f"""
    <div style='background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; border-left: 5px solid {TECH_TEAL};'>
        <p style='color: #888; font-size: 14px; margin:0;'>{{}}</p>
        <h3 style='color: {TECH_BLUE}; font-size: 24px; margin:0;'>{{}}</h3>
    </div>
    """
    
    col1.markdown(kpi_style.format("Volume de Leads (TI)", f"{total:,}"), unsafe_allow_html=True)
    col2.markdown(kpi_style.format("Maturidade Média", f"{idade_media:.1f} anos"), unsafe_allow_html=True)
    col3.markdown(kpi_style.format("Capital Mediano", f"R$ {mediana_cap:,.0f}"), unsafe_allow_html=True)
    col4.markdown(kpi_style.format("PJ Estruturadas (S.A/LTDA)", f"{perc_ltda:.1f}%"), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- ORGANIZAÇÃO EM ABAS (STORYTELLING) ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌍 Matriz Geográfica e Expansão", 
        "🏙️ Hotspots (Bairros)", 
        "📊 Curva de Mortalidade & Porte", 
        "📋 Golden Leads e PDF"
    ])

    # ==========================================
    # ABA 1: VISÃO MACRO E LÓGICA CONDICIONAL DE VISUALIZAÇÃO
    # ==========================================
    with tab1:
        if sel_uf == "Todos" and sel_cidade == "Todas":
            st.markdown("### 🗺️ Estratégia de Expansão Nacional (Fora de SP)")
            st.markdown("*Identificamos estados (excluindo SP para focar em novos mercados) que combinam alto volume de empresas com uma maturidade elevada.*")
            
            df_expansion = df[df['uf_norm'] != 'sp'].copy() if 'sp' in df['uf_norm'].values else df.copy()
            expansion_data = df_expansion.groupby('uf_norm').agg(
                total_empresas=('cnpj_completo', 'count'),
                idade_media_anos=('idade_empresa_anos', 'mean')
            ).reset_index().sort_values(by='total_empresas', ascending=False).head(10)
            
            fig_exp = px.bar(
                expansion_data, x='uf_norm', y='total_empresas', color='idade_media_anos',
                title='Top Estados por Volume de Leads vs Idade Média',
                labels={'uf_norm': 'Estado', 'total_empresas': 'Volume de Empresas', 'idade_media_anos': 'Maturidade (Anos)'},
                color_continuous_scale='Blues', text_auto='.2s'
            )
            fig_exp.update_layout(template="plotly_white")
            st.plotly_chart(fig_exp, use_container_width=True)

        elif sel_uf != "Todos" and sel_cidade == "Todas":
            st.markdown(f"### 📍 Matriz de Volume vs. Estabilidade em {sel_uf.upper()}")
            st.markdown("*Buscamos o quadrante Superior Direito: Cidades com Alto Volume de prospecção e empresas mais velhas (menor risco de quebra).*")
            
            city_matrix = df_filtered.groupby('municipio_norm').agg(
                total_empresas=('cnpj_completo', 'count'),
                idade_media_anos=('idade_empresa_anos', 'mean')
            ).reset_index()
            
            city_matrix = city_matrix.sort_values(by='total_empresas', ascending=False).head(20)
            
            if not city_matrix.empty:
                fig_scatter = px.scatter(
                    city_matrix, x='idade_media_anos', y='total_empresas', size='total_empresas', 
                    color='municipio_norm', hover_name='municipio_norm', size_max=40, text='municipio_norm',
                    title=f'Priorização Tática: Municípios de {sel_uf.upper()}',
                    labels={'idade_media_anos': 'Maturidade Média (Anos)', 'total_empresas': 'Total de Leads', 'municipio_norm': 'Município'}
                )
                fig_scatter.update_traces(textposition='top center')
                fig_scatter.add_vline(x=city_matrix['idade_media_anos'].mean(), line_dash="dash", line_color="grey")
                fig_scatter.add_hline(y=city_matrix['total_empresas'].mean(), line_dash="dash", line_color="grey")
                fig_scatter.update_layout(template="plotly_white", showlegend=False, height=550)
                st.plotly_chart(fig_scatter, use_container_width=True)

        elif sel_cidade != "Todas":
            st.markdown(f"### 🧬 Benchmarking Tático: {sel_cidade.title()} vs Cidades Similares")
            st.markdown(f"*Identificamos municípios dentro de {sel_uf.upper()} com comportamento mercadológico semelhante (Volume e Idade Média) usando cálculo Euclidiano (K-NN).*")
            
            df_state_baseline = df[df['uf_norm'] == sel_uf]
            city_matrix_full = df_state_baseline.groupby('municipio_norm').agg(
                total=('cnpj_completo', 'count'),
                idade=('idade_empresa_anos', 'mean')
            ).reset_index()
            
            sel_stats = city_matrix_full[city_matrix_full['municipio_norm'] == sel_cidade]
            
            if not sel_stats.empty:
                val_total = sel_stats['total'].values[0]
                val_idade = sel_stats['idade'].values[0]
                
                # Normaliza para o cálculo de distância não pesar apenas no volume
                max_total = city_matrix_full['total'].max() if city_matrix_full['total'].max() > 0 else 1
                max_idade = city_matrix_full['idade'].max() if city_matrix_full['idade'].max() > 0 else 1
                
                city_matrix_full['dist_euclidiana'] = np.sqrt(
                    (((city_matrix_full['total'] - val_total)/max_total) ** 2) + 
                    (((city_matrix_full['idade'] - val_idade)/max_idade) ** 2) 
                )
                
                peer_cluster = city_matrix_full.sort_values('dist_euclidiana').head(6).copy()
                peer_cluster['Classificação'] = peer_cluster['municipio_norm'].apply(
                    lambda x: 'Alvo Atual' if x == sel_cidade else 'Cidade Similar'
                )
                
                fig_peers = px.scatter(
                    peer_cluster, x='idade', y='total', size='total', color='Classificação',
                    hover_name='municipio_norm', size_max=45, text='municipio_norm',
                    title=f'Clusters de Similaridade B2B para Seguros de Saúde',
                    labels={'total': 'Volume de Players', 'idade': 'Maturidade Média (Anos)'},
                    color_discrete_map={'Alvo Atual': TECH_BLUE, 'Cidade Similar': TECH_TEAL}
                )
                fig_peers.update_traces(textposition='top center')
                fig_peers.update_layout(template="plotly_white", height=500)
                st.plotly_chart(fig_peers, use_container_width=True)

    # ==========================================
    # ABA 2: VISÃO MICRO (Bairros)
    # ==========================================
    with tab2:
        st.markdown("### 🏘️ Prospecção de Precisão: Top Bairros")
        st.markdown("Direcione campanhas de marketing digital geolocalizado ou equipes de rua estritamente para esses hotspots.")
        
        if sel_cidade != "Todas":
            bairros_data = df_filtered[df_filtered['bairro_norm'] != 'nao_informado']
            bairros_top = bairros_data['bairro_norm'].value_counts().head(15).reset_index()
            bairros_top.columns = ['bairro', 'count']
            
            if not bairros_top.empty:
                fig_bairros = px.bar(
                    bairros_top, x='count', y='bairro', orientation='h',
                    title=f'Densidade de TI por Bairro em {sel_cidade.title()}',
                    color='count', color_continuous_scale='Blues',
                    labels={'count': 'Número de Empresas', 'bairro': 'Bairro'}
                )
                fig_bairros.update_layout(yaxis={'categoryorder':'total ascending'}, template="plotly_white", height=600)
                st.plotly_chart(fig_bairros, use_container_width=True)
            else:
                st.info("Resolução geográfica de bairros insuficiente nesta cidade.")
        else:
            st.warning("⚠️ Selecione uma Cidade ESPECÍFICA no menu lateral para visualizar os Hotspots de Bairros.")

    # ==========================================
    # ABA 3: PERFIL DE RISCO E PORTE
    # ==========================================
    with tab3:
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("### 🍩 Segmentação Jurídica (Porte)")
            st.markdown("O porte define a abordagem: MEI/Micro (Adesão Digital) vs Médio/Grande (Venda Consultiva).")
            
            if 'porte_descricao_norm' in df_filtered.columns:
                porte_counts = df_filtered['porte_descricao_norm'].value_counts().reset_index()
                porte_counts.columns = ['Porte', 'Quantidade']
                
                fig_porte = px.pie(
                    porte_counts, values='Quantidade', names='Porte',
                    hole=0.5, color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_porte.update_traces(textposition='inside', textinfo='percent+label')
                fig_porte.update_layout(template="plotly_white", showlegend=False)
                st.plotly_chart(fig_porte, use_container_width=True)
            else:
                st.info("Coluna de porte não disponível na base processada.")

        with c2:
            st.markdown("### ⏳ A Curva do 'Vale da Morte'")
            st.markdown("Empresas na **Zona Vermelha (< 2 anos)** possuem alto risco de churn na corretora.")
            
            data_plot = df_filtered[df_filtered['idade_empresa_anos'] <= 50]
            
            if not data_plot.empty:
                fig_hist, ax = plt.subplots(figsize=(8, 5))
                
                sns.histplot(data=data_plot, x='idade_empresa_anos', bins=30, kde=True, color=TECH_TEAL, ax=ax)
                ax.axvline(2, color='red', linestyle='--', linewidth=2, label="Risco Crítico (0-2 anos)")
                ax.axvline(5, color='orange', linestyle='--', linewidth=2, label="Consolidação (2-5 anos)")
                ax.axvline(10, color='green', linestyle='--', linewidth=2, label="Estabilidade (>10 anos)")
                
                ax.set_xlabel('Idade da Empresa (Anos)')
                ax.set_ylabel('Frequência de Empresas')
                
                # Desativa bordas do matplotlib para ficar clean no streamlit
                sns.despine()
                ax.legend()
                
                st.pyplot(fig_hist)
            else:
                st.info("Dispersão temporal insuficiente para compilação do histograma.")

    # ==========================================
    # ABA 4: EXPORTAÇÃO E GOLDEN LEADS
    # ==========================================
    with tab4:
        st.markdown("### 🎯 Lista Ouro: Prospecção Imediata")
        st.markdown("Esta é a lista priorizada pelas contas com **maior volume de capital** e **estabilidade corporativa** na região selecionada.")
        
        df_leads = df_filtered.sort_values(by=['capital_social', 'idade_empresa_anos'], ascending=[False, False])
        
        cols_to_show = ['cnpj_completo', 'razao_social', 'porte_descricao_norm', 'bairro_norm', 'idade_empresa_anos', 'capital_social']
        cols_available = [c for c in cols_to_show if c in df_leads.columns]
        
        st.dataframe(df_leads[cols_available].head(50), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📥 Engine de Relatórios Executivos")
        
        c_dl1, c_dl2 = st.columns(2)
        
        with c_dl1:
            st.download_button(
                "💾 Extrair Datalake (CSV Filtrado)", 
                df_filtered.to_csv(index=False).encode('utf-8'), 
                f"base_ti_{sel_uf}_{sel_cidade}.csv", 
                "text/csv", 
                use_container_width=True
            )
            
        with c_dl2:
            if sel_cidade != "Todas":
                try:
                    pdf_bytes = generate_pdf(df_filtered, sel_cidade, sel_uf)
                    st.download_button(
                        "📄 Emitir Dossiê de Prospecção (PDF)", 
                        data=pdf_bytes, 
                        file_name=f"prospeccao_ti_{sel_cidade}.pdf", 
                        mime="application/pdf", 
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro ao compilar o engine de renderização PDF: {e}")
            else:
                st.button("🔒 Fixe um Município no Radar para habilitar o PDF", disabled=True, use_container_width=True)

if __name__ == "__main__":
    main()