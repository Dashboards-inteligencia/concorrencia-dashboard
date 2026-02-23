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

# Configuração da Página (Corporate Education Theme)
st.set_page_config(
    page_title="Market Mapping - Educação",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🎓"
)

# Paleta Semântica Educacional (Tons de Azul e Petróleo)
EDU_PRIMARY = "#173f5f" # Azul Escuro
EDU_SECONDARY = "#20639b" # Azul Médio
EDU_ACCENT = "#4da6c4" # Azul Claro
EDU_LIGHT = "#a8d5e2"

# Mapeamento do Tier de Riqueza para o Donut Chart
TIER_COLORS = {
    'Micro (Varejo)': EDU_LIGHT,
    'PME (Escola Estruturada)': EDU_ACCENT,
    'Corporate (Colégios/Faculdades)': EDU_SECONDARY,
    'Key Account (Grupos Educacionais)': EDU_PRIMARY
}

# --- BLOCO 2: CARGA DE DADOS ---
@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'education_market_processed.parquet')

    if not os.path.exists(file_path):
        st.error(f"Base de dados não encontrada em: {file_path}. Rode o script ETL primeiro.")
        st.stop()

    df = pd.read_parquet(file_path)
    return df

# --- BLOCO 3: SIDEBAR (FILTROS) ---
def sidebar_filters(df: pd.DataFrame):
    st.sidebar.markdown("## 🧭 Radar de Prospecção")
    st.sidebar.markdown("Filtre o mercado educacional:")
    
    lista_ufs = [str(x) for x in df['uf_norm'].dropna().unique().tolist()]
    opts_uf = ["Todos"] + sorted(lista_ufs)
    
    # Pré-seleciona 'SP' se existir
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

    # Filtro de Segmento Educacional
    if 'segmento_educacional' in df.columns:
        lista_seg = [str(x) for x in df['segmento_educacional'].dropna().unique().tolist()]
        sel_seg = st.sidebar.multiselect("Nicho de Ensino", lista_seg, default=lista_seg)
        if sel_seg:
            df_filtered = df_filtered[df_filtered['segmento_educacional'].isin(sel_seg)]
            
    # Filtro de Tier Financeiro
    if 'tier_cliente' in df.columns:
        lista_tier = [str(x) for x in df['tier_cliente'].dropna().unique().tolist()]
        sel_tier = st.sidebar.multiselect("Potencial Financeiro (Tier)", lista_tier, default=lista_tier)
        if sel_tier:
            df_filtered = df_filtered[df_filtered['tier_cliente'].isin(sel_tier)]
        
    return df_filtered, sel_uf, sel_cidade

# --- BLOCO 4: GERAÇÃO DE PDF (REPORTE EXECUTIVO) ---
def generate_pdf(df_city: pd.DataFrame, cidade: str, estado: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Cabeçalho
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(23, 63, 95) # EDU_PRIMARY RGB(23, 63, 95)
    pdf.cell(0, 10, f"Dossie Executivo de Educacao: {cidade.title()} - {estado.upper()}", align="C", ln=1)
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y')} | Escolas/Faculdades Qualificadas: {len(df_city)}", align="C", ln=1)
    pdf.ln(5)
    
    # Resumo
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, "1. GOLDEN LEADS (Top 15 Instituicoes)", ln=1)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(0, 5, "Foco estrategico: Contas de alto Capital Social (Maior capacidade de pagamento) e Maior Maturidade (Baixa sinistralidade administrativa). Abordagem consultiva recomendada para o nivel Diretoria/RH.")
    pdf.ln(5)
    
    # Tabela TOP Leads
    col_w = [30, 55, 30, 25, 12, 40]
    headers = ["CNPJ", "Instituicao", "Segmento", "Capital(R$)", "Anos", "Contato"]
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(230, 240, 245)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, 1, align='C', fill=True, ln=(1 if i == 5 else 0))
    
    pdf.set_font("Arial", "", 7)
    # Ordenação por Capital, Score de Contato e Idade
    if 'score_contato' in df_city.columns:
        df_leads = df_city.sort_values(by=['capital_social', 'score_contato', 'idade_empresa_anos'], ascending=[False, False, False]).head(15)
    else:
        df_leads = df_city.sort_values(by=['capital_social', 'idade_empresa_anos'], ascending=[False, False]).head(15)
    
    if df_leads.empty:
        pdf.cell(0, 10, "Nenhuma instituicao encontrada neste filtro.", 1, align='C', ln=1)
    else:
        for _, r in df_leads.iterrows():
            cnpj = str(r.get('cnpj_completo', 'N/D'))
            nome = str(r.get('razao_social', 'N/D'))[:30].encode('latin-1', 'replace').decode('latin-1')
            seg = str(r.get('segmento_educacional', 'N/D'))[:15].encode('latin-1', 'replace').decode('latin-1')
            cap = f"{r.get('capital_social', 0):,.0f}"
            idade = f"{r.get('idade_empresa_anos', 0):.1f}"
            
            # Monta contato 
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
            
    # Compatibilidade Universal (Funciona no FPDF antigo e no FPDF2 novo)
    pdf_out = pdf.output(dest='S')
    if isinstance(pdf_out, str):
        return pdf_out.encode('latin-1')
    return bytes(pdf_out)

# --- BLOCO 5: APP MAIN ---
def main():
    st.markdown(f"<h1 style='text-align: center; color: {EDU_PRIMARY};'>🎓 Mapeamento Estratégico: Setor de Educação</h1>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='background-color: #f4f8fb; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid {EDU_PRIMARY};'>
        <p style='color: #333333; font-size: 16px; margin: 0;'>
            <b>Contexto B2B Saúde:</b> Instituições de Ensino possuem dores específicas como retenção de professores e exigências sindicais.
            Identifique regiões com volume de escolas, mas priorize os clusters de <b>High Ticket (Grandes Colégios/Universidades)</b>.
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
    
    if 'is_high_ticket' in df_filtered.columns:
        high_ticket_vol = df_filtered['is_high_ticket'].sum()
        high_ticket_perc = (high_ticket_vol / total * 100) if total > 0 else 0
    else:
        high_ticket_vol, high_ticket_perc = 0, 0
        
    if 'qualidade_contato' in df_filtered.columns:
        ouro = df_filtered[df_filtered['qualidade_contato'] == 'Ouro (Tel+Email)'].shape[0]
        ouro_perc = (ouro / total * 100) if total > 0 else 0
    else:
        ouro, ouro_perc = 0, 0
    
    col1, col2, col3, col4 = st.columns(4)
    kpi_style = f"""
    <div style='background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; border-left: 5px solid {EDU_ACCENT};'>
        <p style='color: #888; font-size: 14px; margin:0;'>{{}}</p>
        <h3 style='color: {EDU_PRIMARY}; font-size: 24px; margin:0;'>{{}}</h3>
    </div>
    """
    
    col1.markdown(kpi_style.format("Total de Instituições", f"{total:,}"), unsafe_allow_html=True)
    col2.markdown(kpi_style.format("Contas 'High Ticket'", f"{high_ticket_vol:,} ({high_ticket_perc:.1f}%)"), unsafe_allow_html=True)
    col3.markdown(kpi_style.format("Maturidade Média", f"{idade_media:.1f} anos"), unsafe_allow_html=True)
    col4.markdown(kpi_style.format("Contatos 'Ouro'", f"{ouro_perc:.1f}% base"), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- ORGANIZAÇÃO EM ABAS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌍 Matriz Geográfica (Valor x Volume)", 
        "🏙️ Raio-X de Bairros", 
        "📊 Perfil de Risco & Ticket", 
        "📋 Golden Leads e PDF"
    ])

    # ==========================================
    # ABA 1: VISÃO MACRO E LÓGICA CONDICIONAL
    # ==========================================
    with tab1:
        if sel_uf == "Todos" and sel_cidade == "Todas":
            st.markdown("### 🗺️ Oportunidade Nacional (Expansão)")
            st.markdown("*Estados com alta concentração de 'Key Accounts' (Grupos Educacionais).*")
            
            df_expansion = df[df['uf_norm'] != 'sp'].copy() if 'sp' in df['uf_norm'].values else df.copy()
            
            # Garante que is_high_ticket exista
            if 'is_high_ticket' not in df_expansion.columns:
                df_expansion['is_high_ticket'] = df_expansion.get('tier_cliente', '').isin(['Corporate (Colégios/Faculdades)', 'Key Account (Grupos Educacionais)']).astype(int)

            expansion_data = df_expansion.groupby('uf_norm').agg(
                total_empresas=('cnpj_completo', 'count'),
                leads_high_ticket=('is_high_ticket', 'sum'),
                idade_media_anos=('idade_empresa_anos', 'mean')
            ).reset_index().sort_values(by='leads_high_ticket', ascending=False).head(10)
            
            fig_exp = px.bar(
                expansion_data, x='uf_norm', y='total_empresas', color='leads_high_ticket',
                title='Estados Alvo: Volume de Escolas vs Quantidade de Grandes Contas (Cor)',
                labels={'uf_norm': 'Estado', 'total_empresas': 'Volume Total', 'leads_high_ticket': 'Qtd. High Ticket'},
                color_continuous_scale='Blues', text_auto='.2s'
            )
            fig_exp.update_layout(template="plotly_white", height=500)
            st.plotly_chart(fig_exp, use_container_width=True)

        elif sel_uf != "Todos" and sel_cidade == "Todas":
            st.markdown(f"### 📍 Matriz de Polos Regionais em {sel_uf.upper()}")
            st.markdown("*Buscamos Cidades-Oásis: Alto Volume de Instituições e Elevada Densidade de Grandes Contas.*")
            
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
                    title=f'Batalha de Hubs Regionais: {sel_uf.upper()}',
                    labels={'leads_high_ticket': 'Qtd High Ticket (>500k)', 'total_empresas': 'Volume de Escolas', 'idade_media_anos': 'Maturidade (Anos)'},
                    color_continuous_scale='Blues'
                )
                fig_scatter.update_traces(textposition='top center')
                fig_scatter.add_vline(x=city_matrix['total_empresas'].mean(), line_dash="dash", line_color="grey")
                fig_scatter.add_hline(y=city_matrix['leads_high_ticket'].mean(), line_dash="dash", line_color="grey")
                fig_scatter.update_layout(template="plotly_white", showlegend=False, height=550)
                st.plotly_chart(fig_scatter, use_container_width=True)

        elif sel_cidade != "Todas":
            st.markdown(f"### 🧬 Cidades Gêmeas (K-NN Clustering): {sel_cidade.title()}")
            st.markdown(f"*Encontramos cidades em {sel_uf.upper()} com proporção semelhante entre Volume de Varejo e Presença de Grandes Contas para replicar estratégias.*")
            
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
                
                # Distância euclidiana focada em Volume e Valor
                city_matrix_full['dist_euclidiana'] = np.sqrt(
                    (((city_matrix_full['total'] - val_total)/max_total) ** 2) + 
                    (((city_matrix_full['high_ticket'] - val_ht)/max_ht) ** 2) 
                )
                
                peer_cluster = city_matrix_full.sort_values('dist_euclidiana').head(6).copy()
                peer_cluster['Classificação'] = peer_cluster['municipio_norm'].apply(
                    lambda x: 'Alvo Atual' if x == sel_cidade else 'Oportunidade Similar'
                )
                
                fig_peers = px.scatter(
                    peer_cluster, x='total', y='high_ticket', size='total', color='Classificação',
                    hover_name='municipio_norm', size_max=45, text='municipio_norm',
                    title=f'Recomendação de Expansão: Onde aplicar a mesma tática de {sel_cidade.title()}?',
                    labels={'total': 'Volume Total', 'high_ticket': 'Qtd. High Ticket'},
                    color_discrete_map={'Alvo Atual': EDU_PRIMARY, 'Oportunidade Similar': EDU_ACCENT}
                )
                fig_peers.update_traces(textposition='top center')
                fig_peers.update_layout(template="plotly_white", height=500)
                st.plotly_chart(fig_peers, use_container_width=True)

    # ==========================================
    # ABA 2: VISÃO MICRO (Bairros por Segmento)
    # ==========================================
    with tab2:
        st.markdown("### 🏘️ Raio-X dos Bairros: Dominância de Nicho")
        st.markdown("Veja não apenas *quantas* escolas tem o bairro, mas se o foco é Universitário, Ensino Básico ou Infantil.")
        
        if sel_cidade != "Todas":
            bairros_data = df_filtered[df_filtered['bairro_norm'] != 'nao_informado']
            if not bairros_data.empty and 'segmento_educacional' in bairros_data.columns:
                
                # Identifica os top bairros primeiro
                top_bairros_list = bairros_data['bairro_norm'].value_counts().head(15).index.tolist()
                df_bairros_top = bairros_data[bairros_data['bairro_norm'].isin(top_bairros_list)]
                
                # Agrupa bairro e segmento para barra empilhada
                bairros_segmento = df_bairros_top.groupby(['bairro_norm', 'segmento_educacional']).size().reset_index(name='count')
                
                fig_bairros = px.bar(
                    bairros_segmento, x='count', y='bairro_norm', color='segmento_educacional',
                    orientation='h', title=f'Perfil de Atuação por Bairro em {sel_cidade.title()}',
                    labels={'count': 'Qtd. Instituições', 'bairro_norm': 'Bairro', 'segmento_educacional': 'Nicho'},
                    category_orders={"bairro_norm": top_bairros_list},
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                
                # --- CORREÇÃO APLICADA AQUI: Ajuste da margem (margin) e âncora (yanchor/xanchor) ---
                fig_bairros.update_layout(
                    template="plotly_white", 
                    height=650, 
                    margin=dict(t=120), # Aumenta o espaço livre no topo do gráfico
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="center", 
                        x=0.5
                    )
                )
                
                st.plotly_chart(fig_bairros, use_container_width=True)
            else:
                st.info("Dados insuficientes de Bairro ou Segmento para esta localidade.")
        else:
            st.warning("⚠️ Selecione uma Cidade ESPECÍFICA no menu lateral para visualizar os micro-mercados.")
    # ==========================================
    # ABA 3: PERFIL DE MATURIDADE E TIER
    # ==========================================
    with tab3:
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("### 🍩 Share de Carteira (Potencial)")
            st.markdown("As contas escuras justificam visita presencial; as claras, Marketing Digital.")
            
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
            st.markdown("### ⏳ Curva de Retenção (Idade)")
            st.markdown("Alerta vermelho <3 anos (Alta Sinistralidade RH). Escolas verdes >15 anos buscam Seguro Premium.")
            
            data_plot = df_filtered[df_filtered['idade_empresa_anos'] <= 60]
            if not data_plot.empty:
                fig_hist, ax = plt.subplots(figsize=(8, 5))
                sns.histplot(data=data_plot, x='idade_empresa_anos', bins=35, kde=True, color=EDU_PRIMARY, ax=ax)
                
                ax.axvline(3, color='red', linestyle='--', linewidth=2, label="Tração (0-3 anos)")
                ax.axvline(15, color='green', linestyle='--', linewidth=2, label="Tradição (>15 anos)")
                ax.set_xlabel('Idade (Anos)')
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
        st.markdown("### 🎯 Lista Ouro: Key Accounts e PMEs")
        st.markdown("Ordenado via Algoritmo: **Capital Financeiro > Score de Contato (Tel/Email) > Idade Institucional**.")
        
        if 'score_contato' in df_filtered.columns:
            df_leads = df_filtered.sort_values(by=['capital_social', 'score_contato', 'idade_empresa_anos'], ascending=[False, False, False])
        else:
            df_leads = df_filtered.sort_values(by=['capital_social', 'idade_empresa_anos'], ascending=[False, False])
            
        cols_to_show = ['cnpj_completo', 'razao_social', 'segmento_educacional', 'tier_cliente', 'idade_empresa_anos', 'capital_social']
        cols_available = [c for c in cols_to_show if c in df_leads.columns]
        
        st.dataframe(df_leads[cols_available].head(50), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📥 Dossiê PDF e Datalake")
        
        c_dl1, c_dl2 = st.columns(2)
        
        with c_dl1:
            st.download_button(
                "💾 Exportar Base Completa Filtrada (CSV)", 
                df_filtered.to_csv(index=False).encode('utf-8'), 
                f"base_educacao_{sel_uf}_{sel_cidade}.csv", 
                "text/csv", 
                use_container_width=True
            )
            
        with c_dl2:
            if sel_cidade != "Todas":
                try:
                    pdf_bytes = generate_pdf(df_filtered, sel_cidade, sel_uf)
                    st.download_button(
                        "📄 Gerar Dossiê de Prospecção Regional (PDF)", 
                        data=pdf_bytes, 
                        file_name=f"dossie_educacao_{sel_cidade}.pdf", 
                        mime="application/pdf", 
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro ao processar o arquivo PDF: {e}")
            else:
                st.button("🔒 Selecione uma Cidade no Radar Lateral para liberar o Dossiê PDF", disabled=True, use_container_width=True)

if __name__ == "__main__":
    main()
