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
import unicodedata
import re

st.set_page_config(
    page_title="Hub B2B - Engenharia, TI & Varejo",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# --- BLOCO 2: DICIONÁRIO DE CONFIGURAÇÃO DOS NICHOS ---
CONFIG_NICHOS = {
    "Construção Civil": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_construcao\construction_market_processed.parquet",
        "icon": "🏗️",
        "title": "Inteligência em Engenharia & Construção",
        "theme_color": "#d35400", # Laranja Tijolo
        "heatmap_scale": "Oranges",
        "tiers": ['Infraestrutura / Obras Públicas (>10M)', 'Grande Porte (Incorporadora)', 'Construtora PME', 'Pequena Empreiteira (Até 100k)'],
        "key_accounts": ['Infraestrutura / Obras Públicas (>10M)', 'Grande Porte (Incorporadora)'],
        "color_map": {'Infraestrutura / Obras Públicas (>10M)': '#d35400', 'Grande Porte (Incorporadora)': '#e67e22', 'Construtora PME': '#7f8c8d', 'Pequena Empreiteira (Até 100k)': '#bdc3c7'},
        "col_segmento_original": "tier_cliente",
        "desc": "Priorize a força de vendas identificando regiões com alta concentração de <b>Obras Grandes/Incorporadoras</b>. Utilize a segmentação de risco (Canteiro Pesado) para vendas consultivas de Seguro Saúde Ocupacional."
    },
    "Educação & Ensino": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_educacao\education_market_processed.parquet",
        "icon": "🎓",
        "title": "Mapeamento Estratégico: Setor de Educação",
        "theme_color": "#173f5f", # Azul Escuro
        "heatmap_scale": "Blues",
        "tiers": ['Key Account (Grupos Educacionais)', 'Corporate (Colégios/Faculdades)', 'PME (Escola Estruturada)', 'Micro (Varejo)'],
        "key_accounts": ['Key Account (Grupos Educacionais)', 'Corporate (Colégios/Faculdades)'],
        "color_map": {'Key Account (Grupos Educacionais)': '#173f5f', 'Corporate (Colégios/Faculdades)': '#20639b', 'PME (Escola Estruturada)': '#4da6c4', 'Micro (Varejo)': '#a8d5e2'},
        "col_segmento_original": "tier_cliente",
        "desc": "Instituições de Ensino possuem dores específicas como retenção de professores e exigências sindicais. Identifique regiões de volume, mas priorize <b>Grandes Colégios/Universidades (High Ticket)</b>."
    },
    "Setor de TI (Tecnologia)": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_ti\it_market_processed.parquet",
        "icon": "💻",
        "title": "Inteligência de Mercado: TI & Seguros Saúde",
        "theme_color": "#005b96", # Azul Tech
        "heatmap_scale": "Teal",
        "tiers": ['Enterprise (Grandes Contas)', 'PME (Empresas Estruturadas)', 'Micro/Pequenas (Volume)'],
        "key_accounts": ['Enterprise (Grandes Contas)'],
        "color_map": {'Enterprise (Grandes Contas)': '#005b96', 'PME (Empresas Estruturadas)': '#00a896', 'Micro/Pequenas (Volume)': '#bdc3c7'},
        "col_segmento_original": "tier_ti", 
        "desc": "Mapeamento de empresas de tecnologia. Direcione a força de vendas cruzando <b>Densidade de Leads</b> com <b>Perfil de Risco (Mortalidade)</b>, focando em Oceanos Azuis de alta estabilidade."
    },
    "Varejo Nacional": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_assets_varejo\leads_varejo_SMEI.parquet",
        "icon": "🛒",
        "title": "Inteligência Varejista B2B",
        "theme_color": "#8e44ad", # Roxo
        "heatmap_scale": "Purples",
        "tiers": ['Medio/Grande Porte', 'Pequeno Porte', 'Micro Empresa'],
        "key_accounts": ['Medio/Grande Porte'],
        "color_map": {'Medio/Grande Porte': '#8e44ad', 'Pequeno Porte': '#9b59b6', 'Micro Empresa': '#bdc3c7'},
        "col_segmento_original": "porte_calc",
        "desc": "Análise de alto volume para o mercado varejista. Filtre redes de comércio e identifique as principais praças de consumo para vendas em escala."
    }
}

# --- BLOCO 3: CARGA DE DADOS UNIFICADA ---
@st.cache_data(ttl=3600)
def load_data(nicho: str) -> pd.DataFrame:
    cfg = CONFIG_NICHOS[nicho]
    file_path = cfg["path"]

    if not os.path.exists(file_path):
        st.error(f"Arquivo não encontrado: {file_path}. Rode o script de ETL deste nicho primeiro.")
        st.stop()

    df = pd.read_parquet(file_path)
    
    # 1. Ajuste Maiúsculo para as UFs
    if 'uf_norm' in df.columns:
        df['uf_norm'] = df['uf_norm'].astype(str).str.upper()
    if 'uf' in df.columns:
        df['uf'] = df['uf'].astype(str).str.upper()

    # 2. Padroniza a coluna de Segmento
    col_orig = cfg["col_segmento_original"]
    if col_orig in df.columns:
        df['Segmento_Alvo'] = df[col_orig]
    elif nicho == "Construção Civil":
        df['Segmento_Alvo'] = np.where(df['capital_social'] >= 10000000, 'Infraestrutura / Obras Públicas (>10M)',
                              np.where(df['capital_social'] >= 1000000, 'Grande Porte (Incorporadora)',
                              np.where(df['capital_social'] >= 100000, 'Construtora PME', 'Pequena Empreiteira (Até 100k)')))
    elif nicho == "Educação & Ensino":
        df['Segmento_Alvo'] = np.where(df['capital_social'] > 5000000, 'Key Account (Grupos Educacionais)',
                              np.where(df['capital_social'] > 500000, 'Corporate (Colégios/Faculdades)',
                              np.where(df['capital_social'] > 50000, 'PME (Escola Estruturada)', 'Micro (Varejo)')))
    elif nicho == "Setor de TI (Tecnologia)":
        df['Segmento_Alvo'] = np.where(df['capital_social'] >= 1000000, 'Enterprise (Grandes Contas)',
                              np.where(df['capital_social'] >= 100000, 'PME (Empresas Estruturadas)', 'Micro/Pequenas (Volume)'))
    elif nicho == "Varejo Nacional":
        df['Segmento_Alvo'] = np.where(df['capital_social'] >= 500000, 'Medio/Grande Porte',
                              np.where(df['capital_social'] >= 100000, 'Pequeno Porte', 'Micro Empresa'))

    # 3. Flag de Key Accounts e Limpezas
    df['is_key_account'] = df['Segmento_Alvo'].isin(cfg['key_accounts']).astype(int)
    
    if 'bairro_norm' not in df.columns and 'bairro' in df.columns:
        df['bairro_norm'] = df['bairro'].astype(str).str.lower().str.strip()
    elif 'bairro_norm' not in df.columns:
        df['bairro_norm'] = 'nao_informado'
        
    if 'municipio_visual' not in df.columns and 'municipio_norm' in df.columns:
        df['municipio_visual'] = df['municipio_norm'].astype(str).str.title()
    elif 'municipio_visual' not in df.columns and 'municipio' in df.columns:
        df['municipio_visual'] = df['municipio'].astype(str).str.title()
        
    if 'idade_empresa_anos' not in df.columns and 'idade' in df.columns:
        df['idade_empresa_anos'] = df['idade']
        
    return df

# --- BLOCO 4: SIDEBAR E PDF (Mantidos Padrões) ---
def sidebar_filters(df: pd.DataFrame, cfg: dict):
    st.sidebar.markdown("## 🧭 Navegação Tática")
    lista_ufs = [str(x) for x in df['uf_norm'].dropna().unique().tolist()]
    opts_uf = ["Todos"] + sorted(lista_ufs)
    
    default_uf_idx = opts_uf.index('SP') if 'SP' in opts_uf else 0
    sel_uf = st.sidebar.selectbox("Estado (UF)", opts_uf, index=default_uf_idx)
    
    df_filtered = df.copy()
    sel_cidade = "Todas"
    
    if sel_uf != "Todos":
        df_filtered = df_filtered[df_filtered['uf_norm'] == sel_uf]
        lista_cidades = [str(x) for x in df_filtered['municipio_visual'].dropna().unique().tolist()]
        opts_cidade = ["Todas"] + sorted(lista_cidades)
        sel_cidade = st.sidebar.selectbox("Cidade", opts_cidade, index=0)
        if sel_cidade != "Todas":
            df_filtered = df_filtered[df_filtered['municipio_visual'] == sel_cidade]

    opts_tier = cfg["tiers"]
    sel_tier = st.sidebar.multiselect("Segmento Alvo (Tier)", opts_tier, default=opts_tier)
    if sel_tier:
        df_filtered = df_filtered[df_filtered['Segmento_Alvo'].isin(sel_tier)]
        
    return df_filtered, sel_uf, sel_cidade

def generate_pdf(df_city: pd.DataFrame, cidade: str, estado: str, cfg: dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    def fix_text(text):
        if not isinstance(text, str): return str(text)
        try: return text.encode('latin-1', 'replace').decode('latin-1')
        except: return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')

    hex_color = cfg["theme_color"].lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(r, g, b) 
    pdf.cell(0, 10, fix_text(f"Dossiê Executivo B2B: {cidade.upper()} - {estado.upper()}"), align="C", ln=1)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, fix_text(f"Gerado em: {datetime.now().strftime('%d/%m/%Y')} | Leads: {len(df_city)}"), align="C", ln=1)
    pdf.ln(5)
    
    col_w = [70, 40, 40, 30]
    headers = ["Razão Social", "Segmento", "Capital (R$)", "Idade (Anos)"]
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, fix_text(h), 1, align='C', fill=True, ln=(1 if i == 3 else 0))
    
    pdf.set_font("Arial", "", 7)
    df_top = df_city.sort_values(by=['capital_social', 'idade_empresa_anos'], ascending=[False, False]).head(20)
    
    if df_top.empty:
        pdf.cell(0, 10, "Nenhum lead encontrado.", 1, align='C', ln=1)
    else:
        for _, r_row in df_top.iterrows():
            nome = str(r_row.get('razao_social', 'N/D'))[:35]
            seg = str(r_row.get('Segmento_Alvo', 'N/D'))[:20]
            cap = f"{r_row.get('capital_social', 0):,.0f}"
            idade = f"{r_row.get('idade_empresa_anos', 0):.1f}"
            pdf.cell(col_w[0], 7, fix_text(nome), 1)
            pdf.cell(col_w[1], 7, fix_text(seg), 1, align='C')
            pdf.cell(col_w[2], 7, cap, 1, align='R')
            pdf.cell(col_w[3], 7, idade, 1, align='C', ln=1)
            
    try:
        pdf_out = pdf.output(dest='S')
        if type(pdf_out) == bytearray: return bytes(pdf_out)
        elif type(pdf_out) == str: return pdf_out.encode('latin-1')
        else: return bytes(pdf_out)
    except Exception:
        return bytes(pdf.output())

# --- BLOCO 5: ENGINE DE TELAS E STORYTELLING CUSTOMIZADO ---
def render_landing_page():
    st.markdown("<h1 style='text-align: center; color: #2f4b7c;'>🏢 Hub B2B: Módulo Corporativo</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 18px; color: #666;'>Modelos de inteligência aplicados aos setores de Engenharia, Educação, Tecnologia e Varejo.</p>", unsafe_allow_html=True)
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.warning(f"**{CONFIG_NICHOS['Construção Civil']['icon']} Construção Civil**\n\n{CONFIG_NICHOS['Construção Civil']['desc']}")
        st.info(f"**{CONFIG_NICHOS['Setor de TI (Tecnologia)']['icon']} Tecnologia da Informação**\n\n{CONFIG_NICHOS['Setor de TI (Tecnologia)']['desc']}")
    with c2:
        st.success(f"**{CONFIG_NICHOS['Educação & Ensino']['icon']} Educação & Ensino**\n\n{CONFIG_NICHOS['Educação & Ensino']['desc']}")
        st.error(f"**{CONFIG_NICHOS['Varejo Nacional']['icon']} Varejo**\n\n{CONFIG_NICHOS['Varejo Nacional']['desc']}")

def render_dashboard(nicho):
    cfg = CONFIG_NICHOS[nicho]
    df = load_data(nicho)
    df_filtered, sel_uf, sel_cidade = sidebar_filters(df, cfg)
    
    st.markdown(f"<h1 style='text-align: center; color: {cfg['theme_color']};'>{cfg['icon']} {cfg['title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid {cfg['theme_color']};'>
        <p style='color: #2c3e50; font-size: 16px; margin: 0;'><b>Contexto Estratégico:</b> {cfg['desc']}</p>
    </div>
    """, unsafe_allow_html=True)

    if df_filtered.empty:
        st.warning("Sem dados para os filtros aplicados.")
        return

    # --- KPIs CUSTOMIZADOS POR NICHO ---
    total = len(df_filtered)
    mediana_cap = df_filtered['capital_social'].median()
    sharks = df_filtered['is_key_account'].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    kpi_style = f"<div style='background-color: #fff; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; border-left: 5px solid {cfg['theme_color']};'><p style='color: #888; font-size: 13px; margin:0;'>{{}}</p><h3 style='color: #2c3e50; font-size: 22px; margin:0;'>{{}}</h3></div>"
    
    if nicho == "Construção Civil":
        alto_risco = df_filtered[df_filtered.get('risco_operacional', pd.Series([''])).str.contains('Alto Risco', na=False)].shape[0] if 'risco_operacional' in df_filtered.columns else 0
        perc_risco = (alto_risco / total * 100) if total > 0 else 0
        col1.markdown(kpi_style.format("CNPJs Mapeados (Obras)", f"{total:,}"), unsafe_allow_html=True)
        col2.markdown(kpi_style.format("Grandes Incorporadoras", f"{sharks:,}"), unsafe_allow_html=True)
        col3.markdown(kpi_style.format("Capital Mediano", f"R$ {mediana_cap:,.0f}"), unsafe_allow_html=True)
        col4.markdown(kpi_style.format("Canteiro Pesado (Alto Risco)", f"{perc_risco:.1f}%"), unsafe_allow_html=True)
        
    elif nicho == "Educação & Ensino":
        ouro = df_filtered[df_filtered.get('qualidade_contato', '') == 'Ouro (Tel+Email)'].shape[0] if 'qualidade_contato' in df_filtered.columns else 0
        perc_ouro = (ouro / total * 100) if total > 0 else 0
        col1.markdown(kpi_style.format("Total de Instituições", f"{total:,}"), unsafe_allow_html=True)
        col2.markdown(kpi_style.format("Contas 'High Ticket'", f"{sharks:,}"), unsafe_allow_html=True)
        col3.markdown(kpi_style.format("Maturidade Média", f"{df_filtered['idade_empresa_anos'].mean():.1f} anos"), unsafe_allow_html=True)
        col4.markdown(kpi_style.format("Contatos 'Ouro' (Tel+Email)", f"{perc_ouro:.1f}%"), unsafe_allow_html=True)
        
    elif nicho == "Setor de TI (Tecnologia)":
        ltda_mask = df_filtered.get('natureza_juridica', pd.Series(['0'])).astype(str).str.startswith('2')
        perc_ltda = (df_filtered[ltda_mask].shape[0] / total * 100) if total > 0 else 0
        col1.markdown(kpi_style.format("Volume de Leads (TI)", f"{total:,}"), unsafe_allow_html=True)
        col2.markdown(kpi_style.format("Contas Chave (Enterprise)", f"{sharks:,}"), unsafe_allow_html=True)
        col3.markdown(kpi_style.format("Capital Mediano", f"R$ {mediana_cap:,.0f}"), unsafe_allow_html=True)
        col4.markdown(kpi_style.format("PJ Estruturadas (SA/LTDA)", f"{perc_ltda:.1f}%"), unsafe_allow_html=True)
        
    else: # Varejo
        col1.markdown(kpi_style.format("Volume de Varejistas", f"{total:,}"), unsafe_allow_html=True)
        col2.markdown(kpi_style.format("Grandes Redes", f"{sharks:,}"), unsafe_allow_html=True)
        col3.markdown(kpi_style.format("Capital Mediano", f"R$ {mediana_cap:,.0f}"), unsafe_allow_html=True)
        col4.markdown(kpi_style.format("Maturidade Média", f"{df_filtered['idade_empresa_anos'].mean():.1f} anos"), unsafe_allow_html=True)

    st.markdown("---")
    st.info("💡 **Dica de Navegação:** Você pode **dar zoom** clicando e arrastando o mouse sobre a área desejada nos gráficos. Duplo clique para resetar.")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌍 Matriz Geográfica e Expansão", 
        "🏙️ Vocação Geográfica (Bairros)", 
        "📊 Curva de Risco e Perfil", 
        "📋 Exportação B2B (Leads)"
    ])

    # ================= ABA 1: GEO E MATRIZ =================
    with tab1:
        if sel_uf == "Todos" and sel_cidade == "Todas":
            if nicho == "Construção Civil":
                st.markdown("### 🗺️ Onde estão as Grandes Obras? (Expansão Nacional)")
                st.markdown("Volume não é sinônimo de valor na construção. O gráfico destaca os estados com a maior densidade de **Incorporadoras e Infraestrutura Pesada** (Cor Escura). Foco nestas regiões para Seguro Garantia e Saúde Ocupacional (SST).")
            elif nicho == "Educação & Ensino":
                st.markdown("### 🗺️ Onde estão as 'Baleias' da Educação?")
                st.markdown("Embora SP lidere em volume de escolas de bairro, observe pela cor do gráfico estados com densidade desproporcional de **Grandes Contas (High Ticket)**, ideais para venda de Seguro Saúde com Reembolso.")
            elif nicho == "Setor de TI (Tecnologia)":
                st.markdown("### 🗺️ Estratégia de Expansão Nacional (TI)")
                st.markdown("Identificamos estados que combinam alto volume de empresas de tecnologia com uma maturidade elevada (menos risco de churn financeiro).")
            else:
                st.markdown("### 🔥 Densidade Nacional (Mass Market)")
            
            df_heat = df_filtered.groupby(['uf_norm', 'Segmento_Alvo']).size().unstack(fill_value=0)
            cols_avail = [c for c in cfg['tiers'] if c in df_heat.columns]
            df_heat = df_heat[cols_avail]
            df_heat['Total_Volume'] = df_heat.sum(axis=1)
            df_heat = df_heat.sort_values('Total_Volume', ascending=True).tail(15).drop(columns=['Total_Volume'])
            
            fig_heat = px.imshow(
                df_heat, labels=dict(x="Tier", y="Estado (UF)", color="Qtd"), x=df_heat.columns, y=df_heat.index,
                text_auto=True, color_continuous_scale=cfg['heatmap_scale'], aspect="auto"
            )
            fig_heat.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
            st.plotly_chart(fig_heat, use_container_width=True)

        elif sel_uf != "Todos" and sel_cidade == "Todas":
            st.markdown(f"### 📍 Batalha de Hubs Regionais: {sel_uf}")
            if nicho == "Construção Civil":
                st.markdown("Comparativo entre Sedes Corporativas e o Interior. Cidades no quadrante superior direito concentram alto poder econômico (Baleias da Engenharia).")
            elif nicho == "Educação & Ensino":
                st.markdown("Buscamos Cidades-Oásis: Cidades altas no eixo (High Ticket) mas moderadas em volume representam oceanos azuis com menor concorrência.")
            elif nicho == "Setor de TI (Tecnologia)":
                st.markdown("Buscamos o quadrante Superior Direito: Cidades com Alto Volume de prospecção e empresas de TI mais velhas (menor risco de quebrar).")
                
            city_matrix = df_filtered.groupby('municipio_visual').agg(
                total=('cnpj_completo', 'count'),
                idade_med=('idade_empresa_anos', 'mean'),
                key_accounts=('is_key_account', 'sum')
            ).reset_index().sort_values('total', ascending=False).head(20)
            
            if not city_matrix.empty:
                fig_scatter = px.scatter(
                    city_matrix, x='idade_med' if nicho != "Educação & Ensino" else 'total', 
                    y='total' if nicho != "Educação & Ensino" else 'key_accounts', 
                    size='key_accounts' if nicho != "Educação & Ensino" else 'key_accounts', 
                    color='key_accounts' if nicho != "Construção Civil" else 'idade_med', 
                    hover_name='municipio_visual', size_max=45, text='municipio_visual',
                    color_continuous_scale=cfg['heatmap_scale']
                )
                fig_scatter.update_traces(textposition='top center', textfont=dict(color='white', size=14))
                fig_scatter.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=600)
                st.plotly_chart(fig_scatter, use_container_width=True)

        elif sel_cidade != "Todas":
            st.markdown(f"### 🧬 Cidades Gêmeas (KNN Clustering): {sel_cidade}")
            st.markdown(f"Encontramos cidades em {sel_uf} com proporção mercadológica semelhante ao seu alvo para clonagem de estratégias.")
            
            df_state_baseline = df[df['uf_norm'] == sel_uf]
            city_matrix_full = df_state_baseline.groupby('municipio_visual').agg(
                total=('cnpj_completo', 'count'),
                key_accounts=('is_key_account', 'sum'),
                ticket=('capital_social', 'median')
            ).reset_index()
            
            sel_stats = city_matrix_full[city_matrix_full['municipio_visual'] == sel_cidade]
            if not sel_stats.empty:
                val_t, val_ka = sel_stats['total'].values[0], sel_stats['key_accounts'].values[0]
                m_t, m_ka = city_matrix_full['total'].max() or 1, city_matrix_full['key_accounts'].max() or 1
                
                city_matrix_full['dist'] = np.sqrt((((city_matrix_full['total'] - val_t)/m_t)**2) + (((city_matrix_full['key_accounts'] - val_ka)/m_ka)**2))
                peer_cluster = city_matrix_full.sort_values('dist').head(6).copy()
                peer_cluster['Classificação'] = peer_cluster['municipio_visual'].apply(lambda x: 'Alvo Principal' if x == sel_cidade else 'Clone Regional')
                
                fig_peers = px.scatter(
                    peer_cluster, x='total', y='key_accounts', size='total', color='Classificação',
                    hover_name='municipio_visual', size_max=45, text='municipio_visual',
                    color_discrete_map={'Alvo Principal': cfg['theme_color'], 'Clone Regional': '#95A5A6'}
                )
                fig_peers.update_traces(textposition='top center', textfont=dict(color='white', size=14))
                fig_peers.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
                st.plotly_chart(fig_peers, use_container_width=True)

    # ================= ABA 2: BAIRROS (CORRIGIDA) =================
    with tab2:
        if nicho == "Construção Civil":
            st.markdown("### 🏘️ Sedes vs Canteiros de Obras")
            st.markdown("Bairros com alta concentração de 'Instalações' indicam bases operacionais (Seguro Acidentes). Áreas de 'Construtora' indicam sedes financeiras (Seguro Vida/Garantia).")
            col_agg = "segmento_construcao"
        elif nicho == "Educação & Ensino":
            st.markdown("### 🏘️ Raio-X dos Bairros: Dominância de Nicho")
            st.markdown("Vila Mariana pode concentrar Ensino Infantil (foco em pediatria), enquanto áreas centrais concentram Faculdades (foco em alunos/professores). Setorize a venda.")
            col_agg = "segmento_educacional"
        else:
            st.markdown("### 🏘️ Prospecção de Precisão: Top Bairros")
            st.markdown("Direcione campanhas de marketing digital ou equipes de rua estritamente para os hotspots abaixo.")
            col_agg = "Segmento_Alvo"

        if sel_cidade != "Todas":
            bairros_data = df_filtered[df_filtered['bairro_norm'] != 'nao_informado'].copy()
            col_uso = col_agg if col_agg in bairros_data.columns else 'Segmento_Alvo'
            
            top_bairros = bairros_data['bairro_norm'].value_counts().head(15).index.tolist()
            bairros_top = bairros_data[bairros_data['bairro_norm'].isin(top_bairros)]
            
            if not bairros_top.empty:
                bairros_tier = bairros_top.groupby(['bairro_norm', col_uso]).size().reset_index(name='count')
                
                # --- MODIFICAÇÕES APLICADAS AQUI ---
                # 1. Transformar os nomes dos bairros em maiúsculo (como na imagem)
                bairros_tier['bairro_norm'] = bairros_tier['bairro_norm'].str.upper()
                top_bairros_upper = [b.upper() for b in top_bairros]
                
                fig_bairros = px.bar(
                    bairros_tier, x='count', y='bairro_norm', color=col_uso,
                    orientation='h', color_discrete_sequence=px.colors.qualitative.Safe,
                    category_orders={"bairro_norm": top_bairros_upper}
                )
                
                # 2. Layout ajustado: Fundo escuro transparente e Legenda vertical à direita
                fig_bairros.update_layout(
                    template="plotly_dark", 
                    paper_bgcolor="rgba(0,0,0,0)", 
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=600, 
                    margin=dict(l=150, t=50, r=50), # Margem 'l=150' dá espaço para os nomes dos bairros
                    yaxis_title="Bairro",
                    xaxis_title="Quantidade",
                    legend=dict(
                        orientation="v",     # Legenda na vertical
                        yanchor="top", 
                        y=1, 
                        xanchor="left", 
                        x=1.02,              # Posicionada no lado direito, fora do gráfico
                        title="Segmento"
                    )
                )
                # -----------------------------------
                
                st.plotly_chart(fig_bairros, use_container_width=True)
            else:
                st.info("Resolução geográfica insuficiente.")
        else:
            st.warning("⚠️ Selecione uma cidade específica para visualizar o mapeamento de bairros.")

    # ================= ABA 3: PERFIL E RISCO =================
    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🍩 Share de Carteira (Potencial)")
            if nicho == "Educação & Ensino" or nicho == "Construção Civil":
                st.markdown("As fatias mais escuras representam as 'Baleias' (High Ticket). Embora menores em volume, possuem potencial de receita superior a milhares de contratos de varejo.")
            elif nicho == "Setor de TI (Tecnologia)":
                st.markdown("A grande fatia dita a abordagem: Micro (Adesão Digital Automática) vs Enterprise (Venda Consultiva Presencial).")
                
            df_tier = df_filtered['Segmento_Alvo'].value_counts().reset_index()
            df_tier.columns = ['Segmento_Alvo', 'count']
            
            fig_donut = px.pie(df_tier, values='count', names='Segmento_Alvo', hole=0.5, color='Segmento_Alvo', color_discrete_map=cfg['color_map'])
            fig_donut.update_traces(textposition='inside', textinfo='percent+label')
            fig_donut.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_donut, use_container_width=True)

        with c2:
            st.markdown("### ⏳ Curva de Mortalidade e Retenção")
            data_plot = df_filtered[df_filtered['idade_empresa_anos'] <= 50]
            if not data_plot.empty:
                fig_hist, ax = plt.subplots(figsize=(8, 5))
                fig_hist.patch.set_facecolor('#1E1E1E')
                ax.set_facecolor('#1E1E1E')
                
                sns.histplot(data=data_plot, x='idade_empresa_anos', bins=30, kde=True, color=cfg['theme_color'], ax=ax)
                
                # Regras de Negócio Customizadas para as Linhas de Risco
                if nicho == "Construção Civil":
                    st.markdown("O pico nos primeiros 3 anos revela as SPEs (Sociedades de Propósito Específico). Foco em **Seguro de Obra e Prazo Determinado**.")
                    ax.axvline(3, color='red', linestyle='--', linewidth=2, label="Risco SPE (<3 anos)")
                    ax.axvline(10, color='green', linestyle='--', linewidth=2, label="Sólido (>10 anos)")
                elif nicho == "Educação & Ensino":
                    st.markdown("Instituições novas (<3 anos) exigem planos de **Coparticipação** devido ao turnover. Escolas >15 anos buscam **Seguro Premium** para professores antigos.")
                    ax.axvline(3, color='red', linestyle='--', linewidth=2, label="Tração (<3 anos)")
                    ax.axvline(15, color='green', linestyle='--', linewidth=2, label="Tradição (>15 anos)")
                else: # TI e Varejo
                    st.markdown("Empresas na Zona Vermelha possuem alto risco de quebra/churn. Planos pré-pagos recomendados.")
                    ax.axvline(2, color='red', linestyle='--', linewidth=2, label="Risco Crítico (<2 anos)")
                    ax.axvline(5, color='orange', linestyle='--', linewidth=2, label="Consolidação")
                    ax.axvline(10, color='green', linestyle='--', linewidth=2, label="Vitalícios (>10 anos)")
                
                ax.tick_params(colors='white')
                ax.set_xlabel("Anos de Atividade", color='white')
                ax.set_ylabel("Volume de Empresas", color='white')
                sns.despine()
                ax.legend()
                st.pyplot(fig_hist)

    # ================= ABA 4: CRM =================
    with tab4:
        st.markdown("### 🎯 Lista de Atacado (Golden Leads)")
        if nicho in ["Educação & Ensino", "Construção Civil"]:
            st.markdown("Contas priorizadas via Inteligência de Máquina: **Capital Financeiro > Acessibilidade de Contato > Maturidade**.")
        else:
            st.markdown("Contas priorizadas rigorosamente por **Maior Capital Social** e estabilidade corporativa na região.")
            
        def safe_format_phone(row):
            ddd = str(row.get('ddd_1', '')).replace('.0', '').replace('nan', '').strip()
            tel = str(row.get('telefone_1', '')).replace('.0', '').replace('nan', '').strip()
            if ddd and tel:
                digits = re.sub(r'\D', '', tel)
                if len(digits) == 8: return f"({ddd}) {digits[:4]}-{digits[4:]}"
                elif len(digits) == 9: return f"({ddd}) {digits[:5]}-{digits[5:]}"
                return f"({ddd}) {tel}"
            return tel if tel else "-"

        df_leads = df_filtered.copy()
        df_leads['Contato'] = df_leads.apply(safe_format_phone, axis=1)
        df_leads['Email'] = df_leads.get('email_contato', pd.Series(["-"]*len(df_leads))).astype(str).str.lower().replace('nan', '-')
            
        df_leads['Empresa_Raiz'] = df_leads['razao_social']
        df_grouped = df_leads.groupby('Empresa_Raiz').agg(
            Qtd_Unidades=('Empresa_Raiz', 'count'), Segmento=('Segmento_Alvo', 'first'),
            Capital_Social=('capital_social', 'first'), Cidade_Principal=('municipio_visual', 'first'),
            Contato=('Contato', 'first'), Email=('Email', 'first')
        ).reset_index().sort_values('Capital_Social', ascending=False)
        
        st.dataframe(df_grouped.head(100), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🏢 Explorador de Unidades de Negócio")
        with st.expander("👉 Expanda as filiais e contatos específicos de um grupo"):
            selected_rede = st.selectbox("Selecione o Grupo Empresarial:", df_grouped['Empresa_Raiz'].head(100).tolist())
            if selected_rede:
                filiais = df_leads[df_leads['Empresa_Raiz'] == selected_rede]
                cols_f = ['razao_social', 'cnpj_completo', 'municipio_visual', 'bairro_norm', 'Contato', 'Email']
                st.dataframe(filiais[[c for c in cols_f if c in filiais.columns]], use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📥 Motor de Relatórios Executivos")
        c_dl1, c_dl2 = st.columns(2)
        with c_dl1:
            st.download_button(
                f"💾 Exportar Base Tratada {nicho} (CSV)", 
                df_filtered.to_csv(index=False).encode('utf-8-sig'), 
                f"leads_{nicho.lower()}_{sel_uf}.csv", "text/csv", use_container_width=True
            )
        with c_dl2:
            if sel_cidade != "Todas":
                try:
                    pdf_bytes = generate_pdf(df_filtered, sel_cidade, sel_uf, cfg)
                    st.download_button(
                        "📄 Emitir Dossiê B2B Local (PDF)", 
                        data=pdf_bytes, file_name=f"dossie_{nicho.lower()}_{sel_cidade}.pdf", 
                        mime="application/pdf", use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro no PDF: {e}")
            else:
                st.button("🔒 Fixe uma Cidade para liberar a impressão do Dossiê", disabled=True, use_container_width=True)

def main():
    st.sidebar.markdown("### 🌐 Menu Estratégico")
    opcoes_menu = ["🏠 Início - Hub B2B"] + list(CONFIG_NICHOS.keys())
    selecao = st.sidebar.selectbox("Módulo Ativo:", opcoes_menu)
    st.sidebar.markdown("---")
    
    if selecao == "🏠 Início - Hub B2B":
        render_landing_page()
    else:
        render_dashboard(selecao)

if __name__ == "__main__":
=======
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
import unicodedata
import re

st.set_page_config(
    page_title="Hub B2B - Engenharia, TI & Varejo",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# --- BLOCO 2: DICIONÁRIO DE CONFIGURAÇÃO DOS NICHOS ---
CONFIG_NICHOS = {
    "Construção Civil": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_construcao\construction_market_processed.parquet",
        "icon": "🏗️",
        "title": "Inteligência em Engenharia & Construção",
        "theme_color": "#d35400", # Laranja Tijolo
        "heatmap_scale": "Oranges",
        "tiers": ['Infraestrutura / Obras Públicas (>10M)', 'Grande Porte (Incorporadora)', 'Construtora PME', 'Pequena Empreiteira (Até 100k)'],
        "key_accounts": ['Infraestrutura / Obras Públicas (>10M)', 'Grande Porte (Incorporadora)'],
        "color_map": {'Infraestrutura / Obras Públicas (>10M)': '#d35400', 'Grande Porte (Incorporadora)': '#e67e22', 'Construtora PME': '#7f8c8d', 'Pequena Empreiteira (Até 100k)': '#bdc3c7'},
        "col_segmento_original": "tier_cliente",
        "desc": "Priorize a força de vendas identificando regiões com alta concentração de <b>Obras Grandes/Incorporadoras</b>. Utilize a segmentação de risco (Canteiro Pesado) para vendas consultivas de Seguro Saúde Ocupacional."
    },
    "Educação & Ensino": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_educacao\education_market_processed.parquet",
        "icon": "🎓",
        "title": "Mapeamento Estratégico: Setor de Educação",
        "theme_color": "#173f5f", # Azul Escuro
        "heatmap_scale": "Blues",
        "tiers": ['Key Account (Grupos Educacionais)', 'Corporate (Colégios/Faculdades)', 'PME (Escola Estruturada)', 'Micro (Varejo)'],
        "key_accounts": ['Key Account (Grupos Educacionais)', 'Corporate (Colégios/Faculdades)'],
        "color_map": {'Key Account (Grupos Educacionais)': '#173f5f', 'Corporate (Colégios/Faculdades)': '#20639b', 'PME (Escola Estruturada)': '#4da6c4', 'Micro (Varejo)': '#a8d5e2'},
        "col_segmento_original": "tier_cliente",
        "desc": "Instituições de Ensino possuem dores específicas como retenção de professores e exigências sindicais. Identifique regiões de volume, mas priorize <b>Grandes Colégios/Universidades (High Ticket)</b>."
    },
    "Setor de TI (Tecnologia)": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_ti\it_market_processed.parquet",
        "icon": "💻",
        "title": "Inteligência de Mercado: TI & Seguros Saúde",
        "theme_color": "#005b96", # Azul Tech
        "heatmap_scale": "Teal",
        "tiers": ['Enterprise (Grandes Contas)', 'PME (Empresas Estruturadas)', 'Micro/Pequenas (Volume)'],
        "key_accounts": ['Enterprise (Grandes Contas)'],
        "color_map": {'Enterprise (Grandes Contas)': '#005b96', 'PME (Empresas Estruturadas)': '#00a896', 'Micro/Pequenas (Volume)': '#bdc3c7'},
        "col_segmento_original": "tier_ti", 
        "desc": "Mapeamento de empresas de tecnologia. Direcione a força de vendas cruzando <b>Densidade de Leads</b> com <b>Perfil de Risco (Mortalidade)</b>, focando em Oceanos Azuis de alta estabilidade."
    },
    "Varejo Nacional": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_assets_varejo\leads_varejo_SMEI.parquet",
        "icon": "🛒",
        "title": "Inteligência Varejista B2B",
        "theme_color": "#8e44ad", # Roxo
        "heatmap_scale": "Purples",
        "tiers": ['Medio/Grande Porte', 'Pequeno Porte', 'Micro Empresa'],
        "key_accounts": ['Medio/Grande Porte'],
        "color_map": {'Medio/Grande Porte': '#8e44ad', 'Pequeno Porte': '#9b59b6', 'Micro Empresa': '#bdc3c7'},
        "col_segmento_original": "porte_calc",
        "desc": "Análise de alto volume para o mercado varejista. Filtre redes de comércio e identifique as principais praças de consumo para vendas em escala."
    }
}

# --- BLOCO 3: CARGA DE DADOS UNIFICADA ---
@st.cache_data(ttl=3600)
def load_data(nicho: str) -> pd.DataFrame:
    cfg = CONFIG_NICHOS[nicho]
    file_path = cfg["path"]

    if not os.path.exists(file_path):
        st.error(f"Arquivo não encontrado: {file_path}. Rode o script de ETL deste nicho primeiro.")
        st.stop()

    df = pd.read_parquet(file_path)
    
    # 1. Ajuste Maiúsculo para as UFs
    if 'uf_norm' in df.columns:
        df['uf_norm'] = df['uf_norm'].astype(str).str.upper()
    if 'uf' in df.columns:
        df['uf'] = df['uf'].astype(str).str.upper()

    # 2. Padroniza a coluna de Segmento
    col_orig = cfg["col_segmento_original"]
    if col_orig in df.columns:
        df['Segmento_Alvo'] = df[col_orig]
    elif nicho == "Construção Civil":
        df['Segmento_Alvo'] = np.where(df['capital_social'] >= 10000000, 'Infraestrutura / Obras Públicas (>10M)',
                              np.where(df['capital_social'] >= 1000000, 'Grande Porte (Incorporadora)',
                              np.where(df['capital_social'] >= 100000, 'Construtora PME', 'Pequena Empreiteira (Até 100k)')))
    elif nicho == "Educação & Ensino":
        df['Segmento_Alvo'] = np.where(df['capital_social'] > 5000000, 'Key Account (Grupos Educacionais)',
                              np.where(df['capital_social'] > 500000, 'Corporate (Colégios/Faculdades)',
                              np.where(df['capital_social'] > 50000, 'PME (Escola Estruturada)', 'Micro (Varejo)')))
    elif nicho == "Setor de TI (Tecnologia)":
        df['Segmento_Alvo'] = np.where(df['capital_social'] >= 1000000, 'Enterprise (Grandes Contas)',
                              np.where(df['capital_social'] >= 100000, 'PME (Empresas Estruturadas)', 'Micro/Pequenas (Volume)'))
    elif nicho == "Varejo Nacional":
        df['Segmento_Alvo'] = np.where(df['capital_social'] >= 500000, 'Medio/Grande Porte',
                              np.where(df['capital_social'] >= 100000, 'Pequeno Porte', 'Micro Empresa'))

    # 3. Flag de Key Accounts e Limpezas
    df['is_key_account'] = df['Segmento_Alvo'].isin(cfg['key_accounts']).astype(int)
    
    if 'bairro_norm' not in df.columns and 'bairro' in df.columns:
        df['bairro_norm'] = df['bairro'].astype(str).str.lower().str.strip()
    elif 'bairro_norm' not in df.columns:
        df['bairro_norm'] = 'nao_informado'
        
    if 'municipio_visual' not in df.columns and 'municipio_norm' in df.columns:
        df['municipio_visual'] = df['municipio_norm'].astype(str).str.title()
    elif 'municipio_visual' not in df.columns and 'municipio' in df.columns:
        df['municipio_visual'] = df['municipio'].astype(str).str.title()
        
    if 'idade_empresa_anos' not in df.columns and 'idade' in df.columns:
        df['idade_empresa_anos'] = df['idade']
        
    return df

# --- BLOCO 4: SIDEBAR E PDF (Mantidos Padrões) ---
def sidebar_filters(df: pd.DataFrame, cfg: dict):
    st.sidebar.markdown("## 🧭 Navegação Tática")
    lista_ufs = [str(x) for x in df['uf_norm'].dropna().unique().tolist()]
    opts_uf = ["Todos"] + sorted(lista_ufs)
    
    default_uf_idx = opts_uf.index('SP') if 'SP' in opts_uf else 0
    sel_uf = st.sidebar.selectbox("Estado (UF)", opts_uf, index=default_uf_idx)
    
    df_filtered = df.copy()
    sel_cidade = "Todas"
    
    if sel_uf != "Todos":
        df_filtered = df_filtered[df_filtered['uf_norm'] == sel_uf]
        lista_cidades = [str(x) for x in df_filtered['municipio_visual'].dropna().unique().tolist()]
        opts_cidade = ["Todas"] + sorted(lista_cidades)
        sel_cidade = st.sidebar.selectbox("Cidade", opts_cidade, index=0)
        if sel_cidade != "Todas":
            df_filtered = df_filtered[df_filtered['municipio_visual'] == sel_cidade]

    opts_tier = cfg["tiers"]
    sel_tier = st.sidebar.multiselect("Segmento Alvo (Tier)", opts_tier, default=opts_tier)
    if sel_tier:
        df_filtered = df_filtered[df_filtered['Segmento_Alvo'].isin(sel_tier)]
        
    return df_filtered, sel_uf, sel_cidade

def generate_pdf(df_city: pd.DataFrame, cidade: str, estado: str, cfg: dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    def fix_text(text):
        if not isinstance(text, str): return str(text)
        try: return text.encode('latin-1', 'replace').decode('latin-1')
        except: return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')

    hex_color = cfg["theme_color"].lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(r, g, b) 
    pdf.cell(0, 10, fix_text(f"Dossiê Executivo B2B: {cidade.upper()} - {estado.upper()}"), align="C", ln=1)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, fix_text(f"Gerado em: {datetime.now().strftime('%d/%m/%Y')} | Leads: {len(df_city)}"), align="C", ln=1)
    pdf.ln(5)
    
    col_w = [70, 40, 40, 30]
    headers = ["Razão Social", "Segmento", "Capital (R$)", "Idade (Anos)"]
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, fix_text(h), 1, align='C', fill=True, ln=(1 if i == 3 else 0))
    
    pdf.set_font("Arial", "", 7)
    df_top = df_city.sort_values(by=['capital_social', 'idade_empresa_anos'], ascending=[False, False]).head(20)
    
    if df_top.empty:
        pdf.cell(0, 10, "Nenhum lead encontrado.", 1, align='C', ln=1)
    else:
        for _, r_row in df_top.iterrows():
            nome = str(r_row.get('razao_social', 'N/D'))[:35]
            seg = str(r_row.get('Segmento_Alvo', 'N/D'))[:20]
            cap = f"{r_row.get('capital_social', 0):,.0f}"
            idade = f"{r_row.get('idade_empresa_anos', 0):.1f}"
            pdf.cell(col_w[0], 7, fix_text(nome), 1)
            pdf.cell(col_w[1], 7, fix_text(seg), 1, align='C')
            pdf.cell(col_w[2], 7, cap, 1, align='R')
            pdf.cell(col_w[3], 7, idade, 1, align='C', ln=1)
            
    try:
        pdf_out = pdf.output(dest='S')
        if type(pdf_out) == bytearray: return bytes(pdf_out)
        elif type(pdf_out) == str: return pdf_out.encode('latin-1')
        else: return bytes(pdf_out)
    except Exception:
        return bytes(pdf.output())

# --- BLOCO 5: ENGINE DE TELAS E STORYTELLING CUSTOMIZADO ---
def render_landing_page():
    st.markdown("<h1 style='text-align: center; color: #2f4b7c;'>🏢 Hub B2B: Módulo Corporativo</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 18px; color: #666;'>Modelos de inteligência aplicados aos setores de Engenharia, Educação, Tecnologia e Varejo.</p>", unsafe_allow_html=True)
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.warning(f"**{CONFIG_NICHOS['Construção Civil']['icon']} Construção Civil**\n\n{CONFIG_NICHOS['Construção Civil']['desc']}")
        st.info(f"**{CONFIG_NICHOS['Setor de TI (Tecnologia)']['icon']} Tecnologia da Informação**\n\n{CONFIG_NICHOS['Setor de TI (Tecnologia)']['desc']}")
    with c2:
        st.success(f"**{CONFIG_NICHOS['Educação & Ensino']['icon']} Educação & Ensino**\n\n{CONFIG_NICHOS['Educação & Ensino']['desc']}")
        st.error(f"**{CONFIG_NICHOS['Varejo Nacional']['icon']} Varejo**\n\n{CONFIG_NICHOS['Varejo Nacional']['desc']}")

def render_dashboard(nicho):
    cfg = CONFIG_NICHOS[nicho]
    df = load_data(nicho)
    df_filtered, sel_uf, sel_cidade = sidebar_filters(df, cfg)
    
    st.markdown(f"<h1 style='text-align: center; color: {cfg['theme_color']};'>{cfg['icon']} {cfg['title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid {cfg['theme_color']};'>
        <p style='color: #2c3e50; font-size: 16px; margin: 0;'><b>Contexto Estratégico:</b> {cfg['desc']}</p>
    </div>
    """, unsafe_allow_html=True)

    if df_filtered.empty:
        st.warning("Sem dados para os filtros aplicados.")
        return

    # --- KPIs CUSTOMIZADOS POR NICHO ---
    total = len(df_filtered)
    mediana_cap = df_filtered['capital_social'].median()
    sharks = df_filtered['is_key_account'].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    kpi_style = f"<div style='background-color: #fff; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; border-left: 5px solid {cfg['theme_color']};'><p style='color: #888; font-size: 13px; margin:0;'>{{}}</p><h3 style='color: #2c3e50; font-size: 22px; margin:0;'>{{}}</h3></div>"
    
    if nicho == "Construção Civil":
        alto_risco = df_filtered[df_filtered.get('risco_operacional', pd.Series([''])).str.contains('Alto Risco', na=False)].shape[0] if 'risco_operacional' in df_filtered.columns else 0
        perc_risco = (alto_risco / total * 100) if total > 0 else 0
        col1.markdown(kpi_style.format("CNPJs Mapeados (Obras)", f"{total:,}"), unsafe_allow_html=True)
        col2.markdown(kpi_style.format("Grandes Incorporadoras", f"{sharks:,}"), unsafe_allow_html=True)
        col3.markdown(kpi_style.format("Capital Mediano", f"R$ {mediana_cap:,.0f}"), unsafe_allow_html=True)
        col4.markdown(kpi_style.format("Canteiro Pesado (Alto Risco)", f"{perc_risco:.1f}%"), unsafe_allow_html=True)
        
    elif nicho == "Educação & Ensino":
        ouro = df_filtered[df_filtered.get('qualidade_contato', '') == 'Ouro (Tel+Email)'].shape[0] if 'qualidade_contato' in df_filtered.columns else 0
        perc_ouro = (ouro / total * 100) if total > 0 else 0
        col1.markdown(kpi_style.format("Total de Instituições", f"{total:,}"), unsafe_allow_html=True)
        col2.markdown(kpi_style.format("Contas 'High Ticket'", f"{sharks:,}"), unsafe_allow_html=True)
        col3.markdown(kpi_style.format("Maturidade Média", f"{df_filtered['idade_empresa_anos'].mean():.1f} anos"), unsafe_allow_html=True)
        col4.markdown(kpi_style.format("Contatos 'Ouro' (Tel+Email)", f"{perc_ouro:.1f}%"), unsafe_allow_html=True)
        
    elif nicho == "Setor de TI (Tecnologia)":
        ltda_mask = df_filtered.get('natureza_juridica', pd.Series(['0'])).astype(str).str.startswith('2')
        perc_ltda = (df_filtered[ltda_mask].shape[0] / total * 100) if total > 0 else 0
        col1.markdown(kpi_style.format("Volume de Leads (TI)", f"{total:,}"), unsafe_allow_html=True)
        col2.markdown(kpi_style.format("Contas Chave (Enterprise)", f"{sharks:,}"), unsafe_allow_html=True)
        col3.markdown(kpi_style.format("Capital Mediano", f"R$ {mediana_cap:,.0f}"), unsafe_allow_html=True)
        col4.markdown(kpi_style.format("PJ Estruturadas (SA/LTDA)", f"{perc_ltda:.1f}%"), unsafe_allow_html=True)
        
    else: # Varejo
        col1.markdown(kpi_style.format("Volume de Varejistas", f"{total:,}"), unsafe_allow_html=True)
        col2.markdown(kpi_style.format("Grandes Redes", f"{sharks:,}"), unsafe_allow_html=True)
        col3.markdown(kpi_style.format("Capital Mediano", f"R$ {mediana_cap:,.0f}"), unsafe_allow_html=True)
        col4.markdown(kpi_style.format("Maturidade Média", f"{df_filtered['idade_empresa_anos'].mean():.1f} anos"), unsafe_allow_html=True)

    st.markdown("---")
    st.info("💡 **Dica de Navegação:** Você pode **dar zoom** clicando e arrastando o mouse sobre a área desejada nos gráficos. Duplo clique para resetar.")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌍 Matriz Geográfica e Expansão", 
        "🏙️ Vocação Geográfica (Bairros)", 
        "📊 Curva de Risco e Perfil", 
        "📋 Exportação B2B (Leads)"
    ])

    # ================= ABA 1: GEO E MATRIZ =================
    with tab1:
        if sel_uf == "Todos" and sel_cidade == "Todas":
            if nicho == "Construção Civil":
                st.markdown("### 🗺️ Onde estão as Grandes Obras? (Expansão Nacional)")
                st.markdown("Volume não é sinônimo de valor na construção. O gráfico destaca os estados com a maior densidade de **Incorporadoras e Infraestrutura Pesada** (Cor Escura). Foco nestas regiões para Seguro Garantia e Saúde Ocupacional (SST).")
            elif nicho == "Educação & Ensino":
                st.markdown("### 🗺️ Onde estão as 'Baleias' da Educação?")
                st.markdown("Embora SP lidere em volume de escolas de bairro, observe pela cor do gráfico estados com densidade desproporcional de **Grandes Contas (High Ticket)**, ideais para venda de Seguro Saúde com Reembolso.")
            elif nicho == "Setor de TI (Tecnologia)":
                st.markdown("### 🗺️ Estratégia de Expansão Nacional (TI)")
                st.markdown("Identificamos estados que combinam alto volume de empresas de tecnologia com uma maturidade elevada (menos risco de churn financeiro).")
            else:
                st.markdown("### 🔥 Densidade Nacional (Mass Market)")
            
            df_heat = df_filtered.groupby(['uf_norm', 'Segmento_Alvo']).size().unstack(fill_value=0)
            cols_avail = [c for c in cfg['tiers'] if c in df_heat.columns]
            df_heat = df_heat[cols_avail]
            df_heat['Total_Volume'] = df_heat.sum(axis=1)
            df_heat = df_heat.sort_values('Total_Volume', ascending=True).tail(15).drop(columns=['Total_Volume'])
            
            fig_heat = px.imshow(
                df_heat, labels=dict(x="Tier", y="Estado (UF)", color="Qtd"), x=df_heat.columns, y=df_heat.index,
                text_auto=True, color_continuous_scale=cfg['heatmap_scale'], aspect="auto"
            )
            fig_heat.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
            st.plotly_chart(fig_heat, use_container_width=True)

        elif sel_uf != "Todos" and sel_cidade == "Todas":
            st.markdown(f"### 📍 Batalha de Hubs Regionais: {sel_uf}")
            if nicho == "Construção Civil":
                st.markdown("Comparativo entre Sedes Corporativas e o Interior. Cidades no quadrante superior direito concentram alto poder econômico (Baleias da Engenharia).")
            elif nicho == "Educação & Ensino":
                st.markdown("Buscamos Cidades-Oásis: Cidades altas no eixo (High Ticket) mas moderadas em volume representam oceanos azuis com menor concorrência.")
            elif nicho == "Setor de TI (Tecnologia)":
                st.markdown("Buscamos o quadrante Superior Direito: Cidades com Alto Volume de prospecção e empresas de TI mais velhas (menor risco de quebrar).")
                
            city_matrix = df_filtered.groupby('municipio_visual').agg(
                total=('cnpj_completo', 'count'),
                idade_med=('idade_empresa_anos', 'mean'),
                key_accounts=('is_key_account', 'sum')
            ).reset_index().sort_values('total', ascending=False).head(20)
            
            if not city_matrix.empty:
                fig_scatter = px.scatter(
                    city_matrix, x='idade_med' if nicho != "Educação & Ensino" else 'total', 
                    y='total' if nicho != "Educação & Ensino" else 'key_accounts', 
                    size='key_accounts' if nicho != "Educação & Ensino" else 'key_accounts', 
                    color='key_accounts' if nicho != "Construção Civil" else 'idade_med', 
                    hover_name='municipio_visual', size_max=45, text='municipio_visual',
                    color_continuous_scale=cfg['heatmap_scale']
                )
                fig_scatter.update_traces(textposition='top center', textfont=dict(color='white', size=14))
                fig_scatter.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=600)
                st.plotly_chart(fig_scatter, use_container_width=True)

        elif sel_cidade != "Todas":
            st.markdown(f"### 🧬 Cidades Gêmeas (KNN Clustering): {sel_cidade}")
            st.markdown(f"Encontramos cidades em {sel_uf} com proporção mercadológica semelhante ao seu alvo para clonagem de estratégias.")
            
            df_state_baseline = df[df['uf_norm'] == sel_uf]
            city_matrix_full = df_state_baseline.groupby('municipio_visual').agg(
                total=('cnpj_completo', 'count'),
                key_accounts=('is_key_account', 'sum'),
                ticket=('capital_social', 'median')
            ).reset_index()
            
            sel_stats = city_matrix_full[city_matrix_full['municipio_visual'] == sel_cidade]
            if not sel_stats.empty:
                val_t, val_ka = sel_stats['total'].values[0], sel_stats['key_accounts'].values[0]
                m_t, m_ka = city_matrix_full['total'].max() or 1, city_matrix_full['key_accounts'].max() or 1
                
                city_matrix_full['dist'] = np.sqrt((((city_matrix_full['total'] - val_t)/m_t)**2) + (((city_matrix_full['key_accounts'] - val_ka)/m_ka)**2))
                peer_cluster = city_matrix_full.sort_values('dist').head(6).copy()
                peer_cluster['Classificação'] = peer_cluster['municipio_visual'].apply(lambda x: 'Alvo Principal' if x == sel_cidade else 'Clone Regional')
                
                fig_peers = px.scatter(
                    peer_cluster, x='total', y='key_accounts', size='total', color='Classificação',
                    hover_name='municipio_visual', size_max=45, text='municipio_visual',
                    color_discrete_map={'Alvo Principal': cfg['theme_color'], 'Clone Regional': '#95A5A6'}
                )
                fig_peers.update_traces(textposition='top center', textfont=dict(color='white', size=14))
                fig_peers.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
                st.plotly_chart(fig_peers, use_container_width=True)

    # ================= ABA 2: BAIRROS (CORRIGIDA) =================
    with tab2:
        if nicho == "Construção Civil":
            st.markdown("### 🏘️ Sedes vs Canteiros de Obras")
            st.markdown("Bairros com alta concentração de 'Instalações' indicam bases operacionais (Seguro Acidentes). Áreas de 'Construtora' indicam sedes financeiras (Seguro Vida/Garantia).")
            col_agg = "segmento_construcao"
        elif nicho == "Educação & Ensino":
            st.markdown("### 🏘️ Raio-X dos Bairros: Dominância de Nicho")
            st.markdown("Vila Mariana pode concentrar Ensino Infantil (foco em pediatria), enquanto áreas centrais concentram Faculdades (foco em alunos/professores). Setorize a venda.")
            col_agg = "segmento_educacional"
        else:
            st.markdown("### 🏘️ Prospecção de Precisão: Top Bairros")
            st.markdown("Direcione campanhas de marketing digital ou equipes de rua estritamente para os hotspots abaixo.")
            col_agg = "Segmento_Alvo"

        if sel_cidade != "Todas":
            bairros_data = df_filtered[df_filtered['bairro_norm'] != 'nao_informado'].copy()
            col_uso = col_agg if col_agg in bairros_data.columns else 'Segmento_Alvo'
            
            top_bairros = bairros_data['bairro_norm'].value_counts().head(15).index.tolist()
            bairros_top = bairros_data[bairros_data['bairro_norm'].isin(top_bairros)]
            
            if not bairros_top.empty:
                bairros_tier = bairros_top.groupby(['bairro_norm', col_uso]).size().reset_index(name='count')
                
                # --- MODIFICAÇÕES APLICADAS AQUI ---
                # 1. Transformar os nomes dos bairros em maiúsculo (como na imagem)
                bairros_tier['bairro_norm'] = bairros_tier['bairro_norm'].str.upper()
                top_bairros_upper = [b.upper() for b in top_bairros]
                
                fig_bairros = px.bar(
                    bairros_tier, x='count', y='bairro_norm', color=col_uso,
                    orientation='h', color_discrete_sequence=px.colors.qualitative.Safe,
                    category_orders={"bairro_norm": top_bairros_upper}
                )
                
                # 2. Layout ajustado: Fundo escuro transparente e Legenda vertical à direita
                fig_bairros.update_layout(
                    template="plotly_dark", 
                    paper_bgcolor="rgba(0,0,0,0)", 
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=600, 
                    margin=dict(l=150, t=50, r=50), # Margem 'l=150' dá espaço para os nomes dos bairros
                    yaxis_title="Bairro",
                    xaxis_title="Quantidade",
                    legend=dict(
                        orientation="v",     # Legenda na vertical
                        yanchor="top", 
                        y=1, 
                        xanchor="left", 
                        x=1.02,              # Posicionada no lado direito, fora do gráfico
                        title="Segmento"
                    )
                )
                # -----------------------------------
                
                st.plotly_chart(fig_bairros, use_container_width=True)
            else:
                st.info("Resolução geográfica insuficiente.")
        else:
            st.warning("⚠️ Selecione uma cidade específica para visualizar o mapeamento de bairros.")

    # ================= ABA 3: PERFIL E RISCO =================
    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🍩 Share de Carteira (Potencial)")
            if nicho == "Educação & Ensino" or nicho == "Construção Civil":
                st.markdown("As fatias mais escuras representam as 'Baleias' (High Ticket). Embora menores em volume, possuem potencial de receita superior a milhares de contratos de varejo.")
            elif nicho == "Setor de TI (Tecnologia)":
                st.markdown("A grande fatia dita a abordagem: Micro (Adesão Digital Automática) vs Enterprise (Venda Consultiva Presencial).")
                
            df_tier = df_filtered['Segmento_Alvo'].value_counts().reset_index()
            df_tier.columns = ['Segmento_Alvo', 'count']
            
            fig_donut = px.pie(df_tier, values='count', names='Segmento_Alvo', hole=0.5, color='Segmento_Alvo', color_discrete_map=cfg['color_map'])
            fig_donut.update_traces(textposition='inside', textinfo='percent+label')
            fig_donut.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_donut, use_container_width=True)

        with c2:
            st.markdown("### ⏳ Curva de Mortalidade e Retenção")
            data_plot = df_filtered[df_filtered['idade_empresa_anos'] <= 50]
            if not data_plot.empty:
                fig_hist, ax = plt.subplots(figsize=(8, 5))
                fig_hist.patch.set_facecolor('#1E1E1E')
                ax.set_facecolor('#1E1E1E')
                
                sns.histplot(data=data_plot, x='idade_empresa_anos', bins=30, kde=True, color=cfg['theme_color'], ax=ax)
                
                # Regras de Negócio Customizadas para as Linhas de Risco
                if nicho == "Construção Civil":
                    st.markdown("O pico nos primeiros 3 anos revela as SPEs (Sociedades de Propósito Específico). Foco em **Seguro de Obra e Prazo Determinado**.")
                    ax.axvline(3, color='red', linestyle='--', linewidth=2, label="Risco SPE (<3 anos)")
                    ax.axvline(10, color='green', linestyle='--', linewidth=2, label="Sólido (>10 anos)")
                elif nicho == "Educação & Ensino":
                    st.markdown("Instituições novas (<3 anos) exigem planos de **Coparticipação** devido ao turnover. Escolas >15 anos buscam **Seguro Premium** para professores antigos.")
                    ax.axvline(3, color='red', linestyle='--', linewidth=2, label="Tração (<3 anos)")
                    ax.axvline(15, color='green', linestyle='--', linewidth=2, label="Tradição (>15 anos)")
                else: # TI e Varejo
                    st.markdown("Empresas na Zona Vermelha possuem alto risco de quebra/churn. Planos pré-pagos recomendados.")
                    ax.axvline(2, color='red', linestyle='--', linewidth=2, label="Risco Crítico (<2 anos)")
                    ax.axvline(5, color='orange', linestyle='--', linewidth=2, label="Consolidação")
                    ax.axvline(10, color='green', linestyle='--', linewidth=2, label="Vitalícios (>10 anos)")
                
                ax.tick_params(colors='white')
                ax.set_xlabel("Anos de Atividade", color='white')
                ax.set_ylabel("Volume de Empresas", color='white')
                sns.despine()
                ax.legend()
                st.pyplot(fig_hist)

    # ================= ABA 4: CRM =================
    with tab4:
        st.markdown("### 🎯 Lista de Atacado (Golden Leads)")
        if nicho in ["Educação & Ensino", "Construção Civil"]:
            st.markdown("Contas priorizadas via Inteligência de Máquina: **Capital Financeiro > Acessibilidade de Contato > Maturidade**.")
        else:
            st.markdown("Contas priorizadas rigorosamente por **Maior Capital Social** e estabilidade corporativa na região.")
            
        def safe_format_phone(row):
            ddd = str(row.get('ddd_1', '')).replace('.0', '').replace('nan', '').strip()
            tel = str(row.get('telefone_1', '')).replace('.0', '').replace('nan', '').strip()
            if ddd and tel:
                digits = re.sub(r'\D', '', tel)
                if len(digits) == 8: return f"({ddd}) {digits[:4]}-{digits[4:]}"
                elif len(digits) == 9: return f"({ddd}) {digits[:5]}-{digits[5:]}"
                return f"({ddd}) {tel}"
            return tel if tel else "-"

        df_leads = df_filtered.copy()
        df_leads['Contato'] = df_leads.apply(safe_format_phone, axis=1)
        df_leads['Email'] = df_leads.get('email_contato', pd.Series(["-"]*len(df_leads))).astype(str).str.lower().replace('nan', '-')
            
        df_leads['Empresa_Raiz'] = df_leads['razao_social']
        df_grouped = df_leads.groupby('Empresa_Raiz').agg(
            Qtd_Unidades=('Empresa_Raiz', 'count'), Segmento=('Segmento_Alvo', 'first'),
            Capital_Social=('capital_social', 'first'), Cidade_Principal=('municipio_visual', 'first'),
            Contato=('Contato', 'first'), Email=('Email', 'first')
        ).reset_index().sort_values('Capital_Social', ascending=False)
        
        st.dataframe(df_grouped.head(100), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🏢 Explorador de Unidades de Negócio")
        with st.expander("👉 Expanda as filiais e contatos específicos de um grupo"):
            selected_rede = st.selectbox("Selecione o Grupo Empresarial:", df_grouped['Empresa_Raiz'].head(100).tolist())
            if selected_rede:
                filiais = df_leads[df_leads['Empresa_Raiz'] == selected_rede]
                cols_f = ['razao_social', 'cnpj_completo', 'municipio_visual', 'bairro_norm', 'Contato', 'Email']
                st.dataframe(filiais[[c for c in cols_f if c in filiais.columns]], use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📥 Motor de Relatórios Executivos")
        c_dl1, c_dl2 = st.columns(2)
        with c_dl1:
            st.download_button(
                f"💾 Exportar Base Tratada {nicho} (CSV)", 
                df_filtered.to_csv(index=False).encode('utf-8-sig'), 
                f"leads_{nicho.lower()}_{sel_uf}.csv", "text/csv", use_container_width=True
            )
        with c_dl2:
            if sel_cidade != "Todas":
                try:
                    pdf_bytes = generate_pdf(df_filtered, sel_cidade, sel_uf, cfg)
                    st.download_button(
                        "📄 Emitir Dossiê B2B Local (PDF)", 
                        data=pdf_bytes, file_name=f"dossie_{nicho.lower()}_{sel_cidade}.pdf", 
                        mime="application/pdf", use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro no PDF: {e}")
            else:
                st.button("🔒 Fixe uma Cidade para liberar a impressão do Dossiê", disabled=True, use_container_width=True)

def main():
    st.sidebar.markdown("### 🌐 Menu Estratégico")
    opcoes_menu = ["🏠 Início - Hub B2B"] + list(CONFIG_NICHOS.keys())
    selecao = st.sidebar.selectbox("Módulo Ativo:", opcoes_menu)
    st.sidebar.markdown("---")
    
    if selecao == "🏠 Início - Hub B2B":
        render_landing_page()
    else:
        render_dashboard(selecao)

if __name__ == "__main__":

>>>>>>> 716277610b41debe318477376cee0cdbfa6b0380
    main()
