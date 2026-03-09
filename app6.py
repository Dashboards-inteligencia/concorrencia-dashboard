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

# Configuração da Página (Deve ser o primeiro comando Streamlit)
st.set_page_config(
    page_title="Hub de Inteligência B2B",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# --- BLOCO 2: DICIONÁRIO DE CONFIGURAÇÃO DOS NICHOS ---
# Aqui mapeamos os caminhos, cores e regras de negócio exatas de cada setor
CONFIG_NICHOS = {
    "Concorrência (Seguros)": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_concorrencia\competitors_processed.parquet",
        "icon": "🎯",
        "title": "Inteligência Competitiva e Saturação",
        "theme_color": "#c0392b", # Vermelho Sangue
        "tiers": ['Big Player/Multinacional', 'Assessoria/Consolidadora', 'PME (Concorrente Direto)', 'Micro Corretor'],
        "key_accounts": ['Big Player/Multinacional', 'Big Player / Multinacional'], # Pega variações de espaçamento
        "color_map": {
            'Big Player/Multinacional': '#c0392b', 
            'Assessoria/Consolidadora': '#e67e22', 
            'PME (Concorrente Direto)': '#f39c12', 
            'Micro Corretor': '#bdc3c7'
        },
        "col_segmento_original": "tier_concorrente",
        "desc": "Mapeamento de saturação do mercado de Seguros. Identifique oceanos azuis, monitore os Big Players e encontre seus rivais diretos (PMEs)."
    },
    "Saúde Privada": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_saude\leads_saude_processed.parquet",
        "icon": "🩺",
        "title": "Inteligência em Saúde Privada",
        "theme_color": "#003f5c", # Azul
        "tiers": ['Hospital/Alta Complexidade', 'Clínica Premium', 'Medicina Diagnóstica', 'Consultório/Pequeno'],
        "key_accounts": ['Hospital/Alta Complexidade', 'Clínica Premium'],
        "color_map": {'Hospital/Alta Complexidade': '#003f5c', 'Clínica Premium': '#2f4b7c', 'Medicina Diagnóstica': '#a05195', 'Consultório/Pequeno': '#bdc3c7'},
        "col_segmento_original": "segmento_saude",
        "desc": "Mapeamento de Hospitais, Clínicas e Centros de Diagnóstico para prospecção de planos de saúde, insumos e seguros corporativos."
    },
    "Turismo & Hospitalidade": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_turismo\Leads_Turismo.parquet",
        "icon": "✈️",
        "title": "Inteligência em Turismo e Hospitalidade",
        "theme_color": "#D35400", # Terracota
        "tiers": ['Enterprise (Grandes Redes/Hotéis)', 'SMB (Restaurantes/Pousadas)', 'Micro (Pequenos Estabelecimentos)'],
        "key_accounts": ['Enterprise (Grandes Redes/Hotéis)'],
        "color_map": {'Enterprise (Grandes Redes/Hotéis)': '#D35400', 'SMB (Restaurantes/Pousadas)': '#F39C12', 'Micro (Pequenos Estabelecimentos)': '#BDC3C7'},
        "col_segmento_original": "segmento_turismo",
        "desc": "Localização de Redes Hoteleiras, grandes agências e polos gastronômicos com alta demanda de capital humano e retenção."
    },
    "Seguros & Financeiro": {
        "path": r"C:\Users\Aleffm\Desktop\Projetos\P_Receita_int_mercado\relatorio_seguradora\Leads_Seguros_Financeiro.parquet",
        "icon": "🛡️",
        "title": "Inteligência de Mercado: Seguradoras",
        "theme_color": "#1A2530", # Dark Blue
        "tiers": ['Enterprise (Grandes/Securitizadoras)', 'SMB (Assessorias Médias)', 'Micro (Corretores Individuais)'],
        "key_accounts": ['Enterprise (Grandes/Securitizadoras)'],
        "color_map": {'Enterprise (Grandes/Securitizadoras)': '#1A2530', 'SMB (Assessorias Médias)': '#D4AF37', 'Micro (Corretores Individuais)': '#95A5A6'},
        "col_segmento_original": "segmento_seguros",
        "desc": "Visão geral de expansão comercial buscando Assessorias, Securitizadoras e hubs financeiros para parcerias B2B."
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
    
    # 1. Padroniza a coluna de Segmento (Lida com o nome da coluna de cada projeto)
    col_orig = cfg["col_segmento_original"]
    if col_orig in df.columns:
        df['Segmento_Alvo'] = df[col_orig]
    elif nicho == "Seguros & Financeiro":
        df['Segmento_Alvo'] = np.where(df['capital_social'] >= 1000000, 'Enterprise (Grandes/Securitizadoras)',
                              np.where(df['capital_social'] >= 100000, 'SMB (Assessorias Médias)', 'Micro (Corretores Individuais)'))
    elif nicho == "Turismo & Hospitalidade":
        df['Segmento_Alvo'] = np.where(df['capital_social'] >= 1000000, 'Enterprise (Grandes Redes/Hotéis)',
                              np.where(df['capital_social'] >= 100000, 'SMB (Restaurantes/Pousadas)', 'Micro (Pequenos Estabelecimentos)'))

    # 2. Padroniza Flag de Key Accounts (Sharks)
    df['is_key_account'] = df['Segmento_Alvo'].isin(cfg['key_accounts']).astype(int)
    
    # 3. Limpezas Geográficas
    if 'bairro_norm' not in df.columns and 'bairro' in df.columns:
        df['bairro_norm'] = df['bairro'].astype(str).str.lower().str.strip()
    elif 'bairro_norm' not in df.columns:
        df['bairro_norm'] = 'nao_informado'
        
    if 'municipio_visual' not in df.columns and 'municipio_norm' in df.columns:
        df['municipio_visual'] = df['municipio_norm'].astype(str).str.title()
    elif 'municipio_visual' not in df.columns and 'municipio' in df.columns:
        df['municipio_visual'] = df['municipio'].astype(str).str.title()
        
    # 4. Padroniza Coluna de Idade
    if 'idade_empresa_anos' not in df.columns and 'idade' in df.columns:
        df['idade_empresa_anos'] = df['idade']
        
    return df

# --- BLOCO 4: SIDEBAR (FILTROS) ---
def sidebar_filters(df: pd.DataFrame, cfg: dict):
    st.sidebar.markdown("## 🎯 Radar de Prospecção")
    st.sidebar.markdown("Filtre o território de atuação:")
    
    lista_ufs = [str(x) for x in df['uf_norm'].dropna().unique().tolist()]
    opts_uf = ["Todos"] + sorted(lista_ufs)
    sel_uf = st.sidebar.selectbox("Estado (UF)", opts_uf, index=0)
    
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
    sel_tier = st.sidebar.multiselect("Segmento Alvo", opts_tier, default=opts_tier)
    
    if sel_tier:
        df_filtered = df_filtered[df_filtered['Segmento_Alvo'].isin(sel_tier)]
        
    return df_filtered, sel_uf, sel_cidade

# --- BLOCO 5: GERAÇÃO DE PDF ---
def generate_pdf(df_city: pd.DataFrame, cidade: str, estado: str, cfg: dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    def fix_text(text):
        if not isinstance(text, str): return str(text)
        try:
            return text.encode('latin-1', 'replace').decode('latin-1')
        except:
            return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')

    hex_color = cfg["theme_color"].lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(r, g, b) 
    pdf.cell(0, 10, fix_text(f"Dossiê Tático ({cfg['title']}): {cidade.upper()} - {estado.upper()}"), align="C", ln=1)
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, fix_text(f"Gerado em: {datetime.now().strftime('%d/%m/%Y')} | Leads mapeados: {len(df_city)}"), align="C", ln=1)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, fix_text("1. GOLDEN LEADS LOCAIS (Top Contas ou Rivais)"), ln=1)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(0, 5, fix_text("Listagem filtrada pelas empresas com maior estrutura de capital na região. Ideal para análise de concorrência ou expansão."))
    pdf.ln(5)
    
    col_w = [70, 40, 40, 30]
    headers = ["Razão Social", "Segmento", "Capital (R$)", "Idade (Anos)"]
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, fix_text(h), 1, align='C', fill=True, ln=(1 if i == 3 else 0))
    
    pdf.set_font("Arial", "", 7)
    df_top = df_city.sort_values(by=['capital_social', 'idade_empresa_anos'], ascending=[False, False]).head(20)
    
    if df_top.empty:
        pdf.cell(0, 10, "Nenhum lead relevante encontrado neste filtro.", 1, align='C', ln=1)
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

# --- BLOCO 6: ENGINE DE TELAS ---
def render_landing_page():
    """Renderiza a página inicial antes do usuário escolher o painel."""
    st.markdown("<h1 style='text-align: center; color: #2f4b7c;'>🏢 Bem-vindo ao Hub de Inteligência B2B</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 18px; color: #666;'>Selecione o módulo estratégico desejado no menu lateral esquerdo para carregar o Big Data.</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("### 🔍 Módulos Disponíveis neste App:")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.error(f"**{CONFIG_NICHOS['Concorrência (Seguros)']['icon']} Concorrência (Seguros)**\n\n{CONFIG_NICHOS['Concorrência (Seguros)']['desc']}")
        st.info(f"**{CONFIG_NICHOS['Saúde Privada']['icon']} Saúde Privada**\n\n{CONFIG_NICHOS['Saúde Privada']['desc']}")
        
    with c2:
        st.warning(f"**{CONFIG_NICHOS['Turismo & Hospitalidade']['icon']} Turismo & Hospitalidade**\n\n{CONFIG_NICHOS['Turismo & Hospitalidade']['desc']}")
        st.success(f"**{CONFIG_NICHOS['Seguros & Financeiro']['icon']} Seguros & Financeiro**\n\n{CONFIG_NICHOS['Seguros & Financeiro']['desc']}")

def render_dashboard(nicho_selecionado):
    """Renderiza o Painel Analítico após a seleção."""
    cfg = CONFIG_NICHOS[nicho_selecionado]
    
    st.markdown(f"<h1 style='text-align: center; color: {cfg['theme_color']};'>{cfg['icon']} Bússola dos Dados: {cfg['title']}</h1>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='background-color: #1E1E1E; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid {cfg['theme_color']};'>
        <p style='color: #E0E0E0; font-size: 16px; margin: 0;'>
            <b>Contexto Estratégico:</b> {cfg['desc']} 
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = load_data(nicho_selecionado)
    df_filtered, sel_uf, sel_cidade = sidebar_filters(df, cfg)
    
    if df_filtered.empty:
        st.warning("Sem dados para os filtros aplicados. Tente ampliar a busca.")
        return

    # --- KPIs RÁPIDOS ---
    total = len(df_filtered)
    sharks = df_filtered['is_key_account'].sum()
    mediana_cap = df_filtered['capital_social'].median()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Volume de Estabelecimentos", f"{total:,}")
    col2.metric("Key Accounts (Tubarões)", f"{sharks:,}")
    col3.metric("Capital Social Mediano", f"R$ {mediana_cap:,.0f}")
    col4.metric("Idade Média", f"{df_filtered['idade_empresa_anos'].mean():.1f} anos")
    
    st.markdown("---")
    st.info("💡 **Dica de Navegação:** Você pode **dar zoom** clicando e arrastando o mouse sobre a área desejada nos gráficos. Duplo clique para resetar.")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌍 Matriz de Expansão e Saturação", 
        "🏙️ Micro-Targeting (Bairros)", 
        "📊 Perfil de Mercado", 
        "📋 Exportação e Contatos"
    ])

    # ================= ABA 1 =================
    with tab1:
        if sel_uf == "Todos" and sel_cidade == "Todas":
            st.markdown("### 🔥 Densidade Nacional Estrutural")
            
            df_heat = df_filtered.groupby(['uf_norm', 'Segmento_Alvo']).size().unstack(fill_value=0)
            cols_avail = [c for c in cfg['tiers'] if c in df_heat.columns]
            df_heat = df_heat[cols_avail]
            
            df_heat['Total_Volume'] = df_heat.sum(axis=1)
            df_heat = df_heat.sort_values('Total_Volume', ascending=True).tail(15).drop(columns=['Total_Volume'])
            
            escala = "Reds" if nicho_selecionado == "Concorrência (Seguros)" else ("Oranges" if nicho_selecionado == "Turismo & Hospitalidade" else "Blues")
            
            fig_heat = px.imshow(
                df_heat,
                labels=dict(x="Segmento de Atuação", y="Estado (UF)", color="Qtd de Entidades"),
                x=df_heat.columns, y=df_heat.index,
                text_auto=True, color_continuous_scale=escala, aspect="auto"
            )
            fig_heat.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
            st.plotly_chart(fig_heat, use_container_width=True)

        elif sel_uf != "Todos" and sel_cidade == "Todas":
            st.markdown(f"### 📍 Matriz Tática Geográfica: {sel_uf}")
            
            city_matrix = df_filtered.groupby('municipio_visual').agg(
                total=('cnpj_completo', 'count'),
                idade_med=('idade_empresa_anos', 'mean'),
                key_accounts=('is_key_account', 'sum')
            ).reset_index()
            
            city_matrix = city_matrix[city_matrix['total'] > 5].sort_values('total', ascending=False).head(20)
            
            if not city_matrix.empty:
                escala = "Reds" if nicho_selecionado == "Concorrência (Seguros)" else ("Oranges" if nicho_selecionado == "Turismo & Hospitalidade" else "Blues")
                
                fig_scatter = px.scatter(
                    city_matrix, x='idade_med', y='total', size='total', color='key_accounts',
                    hover_name='municipio_visual', size_max=45, text='municipio_visual',
                    labels={'total': 'Quantidade Total', 'idade_med': 'Maturidade Média (Anos)', 'key_accounts': 'Qtd. Tubarões/Key Accounts'},
                    color_continuous_scale=escala
                )
                fig_scatter.update_traces(textposition='top center')
                fig_scatter.add_hline(y=city_matrix['total'].mean(), line_dash="dot", annotation_text="Média Volume")
                fig_scatter.add_vline(x=city_matrix['idade_med'].mean(), line_dash="dot", annotation_text="Maturidade Média")
                fig_scatter.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=600)
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("Municípios insuficientes no filtro.")

        elif sel_cidade != "Todas":
            st.markdown(f"### 🧬 Benchmarking Dinâmico: {sel_cidade}")
            
            df_state_baseline = df[df['uf_norm'] == sel_uf]
            city_matrix_full = df_state_baseline.groupby('municipio_visual').agg(
                total=('cnpj_completo', 'count'),
                key_accounts=('is_key_account', 'sum'),
                ticket=('capital_social', 'median')
            ).reset_index()
            
            sel_stats = city_matrix_full[city_matrix_full['municipio_visual'] == sel_cidade]
            
            if not sel_stats.empty:
                val_total = sel_stats['total'].values[0]
                val_ka = sel_stats['key_accounts'].values[0]
                
                city_matrix_full['dist_euclidiana'] = np.sqrt(((city_matrix_full['total'] - val_total) ** 2) + (((city_matrix_full['key_accounts'] - val_ka) * 5) ** 2))
                peer_cluster = city_matrix_full.sort_values('dist_euclidiana').head(6).copy()
                peer_cluster['Classificação'] = peer_cluster['municipio_visual'].apply(lambda x: 'Alvo Principal' if x == sel_cidade else 'Comparativo Regional')
                
                fig_peers = px.scatter(
                    peer_cluster, x='total', y='key_accounts', size='ticket', color='Classificação',
                    hover_name='municipio_visual', size_max=45, text='municipio_visual',
                    labels={'total': 'Volume Total', 'key_accounts': 'Qtd. Tubarões', 'ticket': 'Capital Mediano'},
                    color_discrete_map={'Alvo Principal': cfg['theme_color'], 'Comparativo Regional': '#95A5A6'}
                )
                fig_peers.update_traces(textposition='top center', textfont=dict(size=14, color='white'))
                fig_peers.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
                st.plotly_chart(fig_peers, use_container_width=True)

    # ================= ABA 2 =================
    with tab2:
        st.markdown("### 🏘️ Micro-Targeting de Bairros")
        if sel_cidade != "Todas":
            bairros_data = df_filtered[df_filtered['bairro_norm'] != 'nao_informado']
            top_bairros = bairros_data['bairro_norm'].value_counts().head(15).index.tolist()
            bairros_top = bairros_data[bairros_data['bairro_norm'].isin(top_bairros)]
            
            if not bairros_top.empty:
                bairros_tier = bairros_top.groupby(['bairro_norm', 'Segmento_Alvo']).size().reset_index(name='count')
                
                fig_bairros = px.bar(
                    bairros_tier, x='count', y='bairro_norm', color='Segmento_Alvo',
                    orientation='h', color_discrete_map=cfg['color_map'],
                    labels={'count': 'Quantidade', 'bairro_norm': 'Bairro', 'Segmento_Alvo': 'Segmento'},
                    category_orders={"bairro_norm": top_bairros}
                )
                fig_bairros.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=600)
                st.plotly_chart(fig_bairros, use_container_width=True)
            else:
                st.info("Resolução geográfica de bairros insuficiente para esta cidade.")
        else:
            st.warning("⚠️ Selecione uma cidade específica no menu lateral para visualizar a densidade dos bairros.")

    # ================= ABA 3 =================
    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🍩 Estrutura do Mercado")
            df_tier = df_filtered['Segmento_Alvo'].value_counts().reset_index()
            df_tier.columns = ['Segmento_Alvo', 'count']
            
            fig_donut = px.pie(
                df_tier, values='count', names='Segmento_Alvo', hole=0.5,
                color='Segmento_Alvo', color_discrete_map=cfg['color_map']
            )
            fig_donut.update_traces(textposition='inside', textinfo='percent+label')
            fig_donut.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_donut, use_container_width=True)

        with c2:
            st.markdown("### ⏳ Curva de Sobrevivência")
            data_plot = df_filtered[df_filtered['idade_empresa_anos'] <= 50]
            if not data_plot.empty:
                fig_hist, ax = plt.subplots(figsize=(8, 5))
                fig_hist.patch.set_facecolor('#1E1E1E')
                ax.set_facecolor('#1E1E1E')
                
                sns.histplot(data=data_plot, x='idade_empresa_anos', bins=30, kde=True, color=cfg['theme_color'], ax=ax)
                ax.axvline(5, color='orange', linestyle='--', linewidth=2, label="Recentes (<5 anos)")
                ax.axvline(20, color='green', linestyle='--', linewidth=2, label="Tradicionais (>20 anos)")
                
                ax.tick_params(colors='white')
                ax.set_xlabel("Tempo de Atividade (Anos)", color='white')
                ax.set_ylabel("Qtd. de Empresas", color='white')
                ax.legend()
                st.pyplot(fig_hist)
            else:
                st.info("Dispersão temporal insuficiente.")

    # ================= ABA 4 =================
    with tab4:
        st.markdown("### 🎯 Contas Estratégicas (Agrupadas por Matriz)")
        
        def safe_format_phone(row):
            ddd = str(row.get('ddd_1', '')).replace('.0', '').replace('nan', '').strip()
            tel = str(row.get('telefone_1', '')).replace('.0', '').replace('nan', '').strip()
            if ddd and tel:
                digits = re.sub(r'\D', '', tel)
                if len(digits) == 8: return f"({ddd}) {digits[:4]}-{digits[4:]}"
                elif len(digits) == 9: return f"({ddd}) {digits[:5]}-{digits[5:]}"
                return f"({ddd}) {tel}"
            elif tel: return tel
            return "-"

        df_leads = df_filtered.copy()
        df_leads['Contato'] = df_leads.apply(safe_format_phone, axis=1)
        df_leads['Email'] = df_leads.get('email_contato', pd.Series(["-"]*len(df_leads))).astype(str).str.lower().replace('nan', '-')
            
        df_leads['Empresa_Raiz'] = df_leads['razao_social']
        df_grouped = df_leads.groupby('Empresa_Raiz').agg(
            Qtd_Unidades=('Empresa_Raiz', 'count'),
            Segmento=('Segmento_Alvo', 'first'),
            Capital_Social=('capital_social', 'first'),
            Cidade_Principal=('municipio_visual', 'first'),
            Contato=('Contato', 'first'),
            Email=('Email', 'first')
        ).reset_index().sort_values('Capital_Social', ascending=False)
        
        st.dataframe(df_grouped.head(100), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🏢 Explorador de Unidades")
        with st.expander("👉 Clique aqui para detalhar as filiais de uma rede ou corretora específica"):
            selected_rede = st.selectbox("Selecione a Empresa:", df_grouped['Empresa_Raiz'].head(100).tolist())
            if selected_rede:
                filiais = df_leads[df_leads['Empresa_Raiz'] == selected_rede]
                cols_filiais = ['razao_social', 'cnpj_completo', 'municipio_visual', 'bairro_norm', 'Contato', 'Email']
                cols_avail = [c for c in cols_filiais if c in filiais.columns]
                st.dataframe(filiais[cols_avail], use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📥 Output Executivo")
        c_dl1, c_dl2 = st.columns(2)
        
        with c_dl1:
            st.download_button(
                f"💾 Exportar Base {nicho_selecionado} (CSV)", 
                df_filtered.to_csv(index=False).encode('utf-8-sig'), 
                f"leads_{nicho_selecionado.lower().replace(' ', '_')}_{sel_uf}.csv", 
                "text/csv", use_container_width=True
            )
            
        with c_dl2:
            if sel_cidade != "Todas":
                try:
                    pdf_bytes = generate_pdf(df_filtered, sel_cidade, sel_uf, cfg)
                    st.download_button(
                        "📄 Emissão de Dossiê Local (PDF)", 
                        data=pdf_bytes, file_name=f"dossie_{sel_cidade}.pdf", 
                        mime="application/pdf", use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro no PDF: {e}")
            else:
                st.button("🔒 Fixe uma Cidade para liberar o PDF", disabled=True, use_container_width=True)

# --- INICIALIZAÇÃO E NAVEGAÇÃO ---
def main():
    st.sidebar.markdown("### 🌐 Navegação Principal")
    
    # Adicionamos a opção da página inicial no topo
    opcoes_menu = ["🏠 Início - Hub B2B"] + list(CONFIG_NICHOS.keys())
    
    selecao = st.sidebar.selectbox("Selecione o Painel:", opcoes_menu)
    st.sidebar.markdown("---")
    
    if selecao == "🏠 Início - Hub B2B":
        render_landing_page()
    else:
        render_dashboard(selecao)

if __name__ == "__main__":
    main()
