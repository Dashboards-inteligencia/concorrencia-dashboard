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

# Configuração da Página (Construction Theme)
st.set_page_config(
    page_title="Market Mapping - Construção Civil",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🏗️"
)

# Paleta Semântica (Engenharia: Laranja e Chumbo)
CONST_PRIMARY = "#d35400"   # Laranja Escuro / Tijolo
CONST_SECONDARY = "#e67e22" # Laranja Vivo / Segurança
CONST_DARK = "#2c3e50"      # Chumbo / Concreto
CONST_LIGHT = "#95a5a6"     # Cinza Claro

# Mapeamento do Tier de Obras
TIER_COLORS = {
    'Pequena Empreiteira (Até 100k)': '#bdc3c7',
    'Construtora PME': '#7f8c8d',
    'Grande Porte (Incorporadora)': CONST_SECONDARY,
    'Infraestrutura / Obras Públicas (>10M)': CONST_PRIMARY
}

# --- BLOCO 2: CARGA DE DADOS ---
@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'construction_market_processed.parquet')

    if not os.path.exists(file_path):
        st.error(f"Base de dados não encontrada em: {file_path}. Rode o script ETL primeiro.")
        st.stop()

    df = pd.read_parquet(file_path)
    return df

# --- BLOCO 3: SIDEBAR (FILTROS) ---
def sidebar_filters(df: pd.DataFrame):
    st.sidebar.markdown("## 🧭 Radar de Obras")
    st.sidebar.markdown("Filtre o mercado:")
    
    lista_ufs = [str(x) for x in df['uf_norm'].dropna().unique().tolist()]
    opts_uf = ["Todos"] + sorted(lista_ufs)
    
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

    # Filtro de Segmento/Cadeia Produtiva
    if 'segmento_construcao' in df.columns:
        lista_seg = [str(x) for x in df['segmento_construcao'].dropna().unique().tolist()]
        sel_seg = st.sidebar.multiselect("Cadeia Produtiva", lista_seg, default=lista_seg)
        if sel_seg:
            df_filtered = df_filtered[df_filtered['segmento_construcao'].isin(sel_seg)]
            
    return df_filtered, sel_uf, sel_cidade

# --- BLOCO 4: GERAÇÃO DE PDF (REPORTE EXECUTIVO) ---
def generate_pdf(df_city: pd.DataFrame, cidade: str, estado: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Cabeçalho
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(211, 84, 0) # Laranja CONST_PRIMARY
    pdf.cell(0, 10, f"Target List B2B (Engenharia): {cidade.title()} - {estado.upper()}", align="C", ln=1)
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y')} | Construtoras Qualificadas: {len(df_city)}", align="C", ln=1)
    pdf.ln(5)
    
    # Resumo
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, "1. GOLDEN LEADS (Top 15 Obras/Sedes Administrativas)", ln=1)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(0, 5, "Foco estrategico: Contas com alto Capital Social (Sedes Financeiras e Incorporadoras). Avalie a coluna 'Atividade' para definir se o pitch de vendas sera Seguro Garantia, Saude Ocupacional ou Seguros para Frota/Equipamentos.")
    pdf.ln(5)
    
    # Tabela TOP Leads
    col_w = [25, 55, 35, 25, 10, 40]
    headers = ["CNPJ", "Empresa", "Atividade", "Capital(R$)", "Anos", "Contato"]
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, 1, align='C', fill=True, ln=(1 if i == 5 else 0))
    
    pdf.set_font("Arial", "", 7)
    # Ordenação Inteligente: Capital Social -> Contatabilidade -> Idade
    if 'score_contato' in df_city.columns:
        df_leads = df_city.sort_values(by=['capital_social', 'score_contato', 'idade_empresa_anos'], ascending=[False, False, False]).head(15)
    else:
        df_leads = df_city.sort_values(by=['capital_social', 'idade_empresa_anos'], ascending=[False, False]).head(15)
    
    if df_leads.empty:
        pdf.cell(0, 10, "Nenhuma construtora encontrada neste filtro.", 1, align='C', ln=1)
    else:
        for _, r in df_leads.iterrows():
            cnpj = str(r.get('cnpj_completo', 'N/D'))
            nome = str(r.get('nome_fantasia_final', 'N/D'))[:30].encode('latin-1', 'replace').decode('latin-1')
            seg = str(r.get('segmento_construcao', 'N/D'))[:18].encode('latin-1', 'replace').decode('latin-1')
            cap = f"{r.get('capital_social', 0):,.0f}"
            idade = f"{r.get('idade_empresa_anos', 0):.0f}"
            
            # Formatação de Contato
            ddd = str(int(r['ddd_1'])) if pd.notnull(r.get('ddd_1')) else ""
            tel = str(int(r['telefone_1'])) if pd.notnull(r.get('telefone_1')) else ""
            telefone = f"({ddd}){tel}" if ddd and tel else ""
            email = str(r.get('email_contato', '')).split(',')[0][:20] if pd.notnull(r.get('email_contato')) else ""
            contato = f"{telefone} {email}".strip()
            if len(contato) < 2: contato = "N/D"
            
            pdf.cell(col_w[0], 7, cnpj, 1, align='C')
            pdf.cell(col_w[1], 7, nome, 1)
            pdf.cell(col_w[2], 7, seg, 1, align='C')
            pdf.cell(col_w[3], 7, cap, 1, align='R')
            pdf.cell(col_w[4], 7, idade, 1, align='C')
            pdf.cell(col_w[5], 7, contato, 1, align='C', ln=1)
            
    # Compatibilidade Universal para FPDF
    pdf_out = pdf.output(dest='S')
    if isinstance(pdf_out, str):
        return pdf_out.encode('latin-1')
    return bytes(pdf_out)

# --- BLOCO 5: APP MAIN ---
def main():
    st.markdown(f"<h1 style='text-align: center; color: {CONST_PRIMARY};'>🏗️ Inteligência de Mercado: Engenharia & Construção</h1>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid {CONST_PRIMARY};'>
        <p style='color: #2c3e50; font-size: 16px; margin: 0;'>
            <b>Contexto Estratégico:</b> Mapeamento do setor de Engenharia. 
            Priorize a força de vendas identificando regiões com alta concentração de <b>Obras Grandes/Incorporadoras</b>. Utilize a segmentação de risco (Canteiro Pesado) para vendas consultivas de Seguro Saúde Ocupacional e Acidentes de Trabalho.
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
    
    # % de Alto Risco (Canteiro)
    if 'risco_operacional' in df_filtered.columns:
        alto_risco_vol = df_filtered[df_filtered['risco_operacional'].str.contains('Alto Risco', na=False)].shape[0]
        alto_risco_perc = (alto_risco_vol / total * 100) if total > 0 else 0
    else:
        alto_risco_perc = 0
        
    # % de High Ticket
    if 'is_high_ticket' in df_filtered.columns:
        high_ticket_vol = df_filtered['is_high_ticket'].sum()
        high_ticket_perc = (high_ticket_vol / total * 100) if total > 0 else 0
    else:
        high_ticket_perc = 0
    
    col1, col2, col3, col4 = st.columns(4)
    kpi_style = f"""
    <div style='background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; border-left: 5px solid {CONST_PRIMARY};'>
        <p style='color: #888; font-size: 14px; margin:0;'>{{}}</p>
        <h3 style='color: {CONST_DARK}; font-size: 24px; margin:0;'>{{}}</h3>
    </div>
    """
    
    col1.markdown(kpi_style.format("CNPJs Mapeados", f"{total:,}"), unsafe_allow_html=True)
    col2.markdown(kpi_style.format("Incorporadoras/Infraestrutura", f"{high_ticket_perc:.1f}%"), unsafe_allow_html=True)
    col3.markdown(kpi_style.format("Capital Mediano", f"R$ {mediana_cap:,.0f}"), unsafe_allow_html=True)
    col4.markdown(kpi_style.format("Canteiro Pesado (Alto Risco)", f"{alto_risco_perc:.1f}%"), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- ORGANIZAÇÃO EM ABAS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌍 Matriz Geográfica (Hubs)", 
        "🏙️ Vocação dos Bairros", 
        "📊 Perfil de Risco e Porte", 
        "📋 Dossiê PME & Enterprise"
    ])

    # ==========================================
    # ABA 1: VISÃO MACRO (MATRIZES)
    # ==========================================
    with tab1:
        if sel_uf == "Todos" and sel_cidade == "Todas":
            st.markdown("### 🗺️ Estratégia de Expansão (Mapeamento Nacional)")
            st.markdown("*Localize estados fora do eixo principal que possuem forte concentração financeira (Baleias da Engenharia).*")
            
            df_expansion = df[df['uf_norm'] != 'sp'].copy() if 'sp' in df['uf_norm'].values else df.copy()
            if 'is_high_ticket' not in df_expansion.columns:
                df_expansion['is_high_ticket'] = df_expansion.get('tier_cliente', '').isin(['Grande Porte (Incorporadora)', 'Infraestrutura / Obras Públicas (>10M)']).astype(int)

            expansion_data = df_expansion.groupby('uf_norm').agg(
                total_empresas=('cnpj_completo', 'count'),
                leads_high_ticket=('is_high_ticket', 'sum')
            ).reset_index().sort_values(by='total_empresas', ascending=False).head(10)
            
            fig_exp = px.bar(
                expansion_data, x='uf_norm', y='total_empresas', color='leads_high_ticket',
                title='Volume Total vs Densidade de Grandes Incorporadoras (Cor Escura)',
                labels={'uf_norm': 'Estado', 'total_empresas': 'Volume de Empresas', 'leads_high_ticket': 'Qtd. Grandes Obras'},
                color_continuous_scale='Oranges', text_auto='.2s'
            )
            fig_exp.update_layout(template="plotly_white", height=500)
            st.plotly_chart(fig_exp, use_container_width=True)

        elif sel_uf != "Todos" and sel_cidade == "Todas":
            st.markdown(f"### 📍 Matriz de Oportunidades em {sel_uf.upper()}")
            st.markdown("*Identifique Polos Industriais: Cidades isoladas no canto superior direito são Oásis para corretagem B2B.*")
            
            city_matrix = df_filtered.groupby('municipio_norm').agg(
                total_empresas=('cnpj_completo', 'count'),
                leads_high_ticket=('is_high_ticket', 'sum'),
                idade_media_anos=('idade_empresa_anos', 'mean')
            ).reset_index()
            
            city_matrix = city_matrix.sort_values(by='total_empresas', ascending=False).head(20)
            
            if not city_matrix.empty:
                fig_scatter = px.scatter(
                    city_matrix, x='total_empresas', y='leads_high_ticket', size='leads_high_ticket', 
                    color='idade_media_anos', hover_name='municipio_norm', size_max=45, text='municipio_norm',
                    title=f'Batalha de Hubs Regionais: Volume vs Ticket Médio ({sel_uf.upper()})',
                    labels={'leads_high_ticket': 'Grandes Incorporadoras (>1M)', 'total_empresas': 'Pequenas/Médias (Volume)', 'idade_media_anos': 'Maturidade (Anos)'},
                    color_continuous_scale='Oranges'
                )
                fig_scatter.update_traces(textposition='top center')
                fig_scatter.add_vline(x=city_matrix['total_empresas'].mean(), line_dash="dash", line_color="grey")
                fig_scatter.add_hline(y=city_matrix['leads_high_ticket'].mean(), line_dash="dash", line_color="grey")
                fig_scatter.update_layout(template="plotly_white", showlegend=False, height=550)
                st.plotly_chart(fig_scatter, use_container_width=True)

        elif sel_cidade != "Todas":
            st.markdown(f"### 🧬 Expansão Tática via Clustering K-NN: {sel_cidade.title()}")
            st.markdown(f"*O algoritmo identifica quais as 5 cidades em {sel_uf.upper()} têm exatamente o mesmo perfil econômico e de densidade para você clonar sua estratégia comercial.*")
            
            df_state_baseline = df[df['uf_norm'] == sel_uf]
            city_matrix_full = df_state_baseline.groupby('municipio_norm').agg(
                total=('cnpj_completo', 'count'),
                high_ticket=('is_high_ticket', 'sum')
            ).reset_index()
            
            sel_stats = city_matrix_full[city_matrix_full['municipio_norm'] == sel_cidade]
            
            if not sel_stats.empty:
                val_total = sel_stats['total'].values[0]
                val_ht = sel_stats['high_ticket'].values[0]
                
                max_total = city_matrix_full['total'].max() if city_matrix_full['total'].max() > 0 else 1
                max_ht = city_matrix_full['high_ticket'].max() if city_matrix_full['high_ticket'].max() > 0 else 1
                
                # Distância Euclidiana Bivariada
                city_matrix_full['dist_euclidiana'] = np.sqrt(
                    (((city_matrix_full['total'] - val_total)/max_total) ** 2) + 
                    (((city_matrix_full['high_ticket'] - val_ht)/max_ht) ** 2) 
                )
                
                peer_cluster = city_matrix_full.sort_values('dist_euclidiana').head(6).copy()
                peer_cluster['Cluster'] = peer_cluster['municipio_norm'].apply(
                    lambda x: 'Alvo Atual' if x == sel_cidade else 'Clone Comercial'
                )
                
                fig_peers = px.scatter(
                    peer_cluster, x='total', y='high_ticket', size='total', color='Cluster',
                    hover_name='municipio_norm', size_max=45, text='municipio_norm',
                    title=f'Gêmeos Mercadológicos de {sel_cidade.title()}',
                    labels={'total': 'Volume Total', 'high_ticket': 'Qtd. Incorporadoras/Obras Públicas'},
                    color_discrete_map={'Alvo Atual': CONST_PRIMARY, 'Clone Comercial': CONST_DARK}
                )
                fig_peers.update_traces(textposition='top center')
                fig_peers.update_layout(template="plotly_white", height=500)
                st.plotly_chart(fig_peers, use_container_width=True)

    # ==========================================
    # ABA 2: VISÃO MICRO (Bairros por Segmento)
    # ==========================================
    with tab2:
        st.markdown("### 🏘️ Vocação Geográfica (Sede Administrativa vs Canteiro de Obras)")
        st.markdown("Bairros com alta concentração de 'Instalações/Terraplenagem' indicam bases operacionais. Áreas de 'Construtora/Administração' indicam sedes financeiras.")
        
        if sel_cidade != "Todas":
            bairros_data = df_filtered[df_filtered['bairro_norm'] != 'nao_informado']
            if not bairros_data.empty and 'segmento_construcao' in bairros_data.columns:
                
                top_bairros_list = bairros_data['bairro_norm'].value_counts().head(15).index.tolist()
                df_bairros_top = bairros_data[bairros_data['bairro_norm'].isin(top_bairros_list)]
                
                bairros_segmento = df_bairros_top.groupby(['bairro_norm', 'segmento_construcao']).size().reset_index(name='count')
                
                fig_bairros = px.bar(
                    bairros_segmento, x='count', y='bairro_norm', color='segmento_construcao',
                    orientation='h', title=f'Perfil Produtivo dos Bairros em {sel_cidade.title()}',
                    labels={'count': 'Qtd. CNPJs', 'bairro_norm': 'Bairro', 'segmento_construcao': 'Atividade'},
                    category_orders={"bairro_norm": top_bairros_list},
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_bairros.update_layout(template="plotly_white", height=600, legend=dict(orientation="h", y=1.05))
                st.plotly_chart(fig_bairros, use_container_width=True)
            else:
                st.info("Dados insuficientes de Bairro ou Segmento para esta localidade.")
        else:
            st.warning("⚠️ Selecione uma Cidade ESPECÍFICA no menu lateral para visualizar o raio-x de bairros.")

    # ==========================================
    # ABA 3: PERFIL DE RISCO E PORTE
    # ==========================================
    with tab3:
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("### 🍩 O Tamanho da Obra (Tier)")
            st.markdown("Mais de 50% são Empreiteiras Pequenas. Para estas, utilize processos digitais de Venda PME.")
            
            if 'tier_cliente' in df_filtered.columns:
                tier_counts = df_filtered['tier_cliente'].value_counts().reset_index()
                tier_counts.columns = ['Tier', 'Quantidade']
                
                fig_tier = px.pie(
                    tier_counts, values='Quantidade', names='Tier', hole=0.5,
                    color='Tier', color_discrete_map=TIER_COLORS
                )
                fig_tier.update_traces(textposition='inside', textinfo='percent+label')
                fig_tier.update_layout(template="plotly_white", showlegend=False)
                st.plotly_chart(fig_tier, use_container_width=True)

        with c2:
            st.markdown("### ⏳ Estabilidade Financeira e Risco (Idade)")
            st.markdown("SPEs (Sociedade de Propósito Específico) morrem em 3 anos. Foco em Seguros de prazo determinado (Zona Vermelha).")
            
            data_plot = df_filtered[df_filtered['idade_empresa_anos'] <= 50]
            if not data_plot.empty:
                fig_hist, ax = plt.subplots(figsize=(8, 5))
                sns.histplot(data=data_plot, x='idade_empresa_anos', bins=35, kde=True, color=CONST_SECONDARY, ax=ax)
                
                ax.axvline(3, color='red', linestyle='--', linewidth=2, label="Risco Operacional/SPE (<3 anos)")
                ax.axvline(10, color='green', linestyle='--', linewidth=2, label="Sólido/Sede Própria (>10 anos)")
                ax.set_xlabel('Anos de Atividade')
                ax.set_ylabel('Frequência')
                
                sns.despine()
                ax.legend()
                st.pyplot(fig_hist)
            else:
                st.info("Dispersão insuficiente para compilar o histograma.")

    # ==========================================
    # ABA 4: EXPORTAÇÃO E GOLDEN LEADS
    # ==========================================
    with tab4:
        st.markdown("### 🎯 Lista de Atacado (Golden Leads)")
        st.markdown("Contas priorizadas via Inteligência de Máquina: **Capital Financeiro > Acessibilidade de Contato > Maturidade**.")
        
        if 'score_contato' in df_filtered.columns:
            df_leads = df_filtered.sort_values(by=['capital_social', 'score_contato', 'idade_empresa_anos'], ascending=[False, False, False])
        else:
            df_leads = df_filtered.sort_values(by=['capital_social', 'idade_empresa_anos'], ascending=[False, False])
            
        cols_to_show = ['cnpj_completo', 'nome_fantasia_final', 'segmento_construcao', 'tier_cliente', 'idade_empresa_anos', 'capital_social']
        cols_available = [c for c in cols_to_show if c in df_leads.columns]
        
        st.dataframe(df_leads[cols_available].head(50), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📥 Dossiê de Engenharia (PDF) e CSV")
        
        c_dl1, c_dl2 = st.columns(2)
        
        with c_dl1:
            st.download_button(
                "💾 Exportar Base Raw (PMEs + Varejo)", 
                df_filtered.to_csv(index=False).encode('utf-8'), 
                f"obras_{sel_uf}_{sel_cidade}.csv", 
                "text/csv", 
                use_container_width=True
            )
            
        with c_dl2:
            if sel_cidade != "Todas":
                try:
                    pdf_bytes = generate_pdf(df_filtered, sel_cidade, sel_uf)
                    st.download_button(
                        "📄 Dossiê de Prospecção Corporativo (PDF)", 
                        data=pdf_bytes, 
                        file_name=f"dossie_engenharia_{sel_cidade}.pdf", 
                        mime="application/pdf", 
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro ao processar o arquivo PDF: {e}")
            else:
                st.button("🔒 Selecione uma Cidade Específica na Lateral para baixar o PDF", disabled=True, use_container_width=True)

if __name__ == "__main__":
    main()