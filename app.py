import streamlit as st
from streamlit_gsheets_connection import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="CHECKLIST DE PIs / AITs - E-REDES",
    page_icon="⚡",
    layout="wide"
)

# Conexão com o Google Sheets utilizando os teus secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# Configuração da Checklist Estrutura
CHECKLIST_ESTRUTURA = {
    "1. Construção Civil e Infraestrutura": [
        {"id": "croqui", "texto": "Acesso direto e desimpedido a partir da via pública (Croqui)."},
        {"id": "rc", "texto": "Responsável de Cobrança / Contacto em Obra."},
        {"id": "obra_dm", "texto": "Número / Registo Obra DM."}
    ],
    "2. Processos e Licenciamento": [
        {"id": "pi", "texto": "Processo de Instalação (PI) Feito e Aprovado."},
        {"id": "pit", "texto": "Processo de Infraestruturas de Telecomunicações (PIT) Feito e Aprovado."}
    ],
    "3. Clientes e Equipamentos Auxiliares": [
        {"id": "clientes", "texto": "Clientes já foram contactados / Notificados."},
        {"id": "geradores", "texto": "Necessidade / Utilização de Geradores."},
        {"id": "croqui_celas", "texto": "Croqui de Celas Feito e Enviado."}
    ]
}

# Funções de Leitura e Escrita
def carregar_dados_sheets():
    df_obras = conn.read(worksheet="Obras", ttl=0)
    df_respostas = conn.read(worksheet="Respostas", ttl=0)
    return df_obras.fillna(""), df_respostas.fillna("")

def guardar_obras_sheets(df_obras):
    conn.update(worksheet="Obras", data=df_obras)

def guardar_respostas_sheets(df_respostas):
    conn.update(worksheet="Respostas", data=df_respostas)

# Função para Gerar Relatório Resumido para E-mail
def gerar_relatorio_email(ref_obra, df_obras, df_respostas):
    obra_row = df_obras[df_obras["nome_ptd"] == ref_obra]
    data_corte = obra_row["data_corte"].values[0] if not obra_row.empty else datetime.now().strftime("%Y-%m-%d")
    
    resp_obra = df_respostas[df_respostas["nome_ptd"] == ref_obra]
    
    total_itens = len(resp_obra)
    feitos = sum(resp_obra["valor"].str.startswith("Feito"))
    prog = int((feitos / total_itens) * 100) if total_itens > 0 else 0

    relatorio = f"""Assunto: [Acompanhamento PIs/PITs] Estado do PTD - {ref_obra}

Viva,

Segue o ponto de situação do PTD {ref_obra} (Data de Corte: {data_corte}).

--- RESUMO DA AVALIAÇÃO ---
• Instalação / PTD: {ref_obra}
• Progresso Geral: {prog}%
"""

    relatorio += f"\n--- DETALHE DOS CAMPOS ---\n"
    for idx, row in resp_obra.iterrows():
        c_id = row["campo_id"]
        val = row["valor"] if row["valor"] else "Pendente"
        obs = f" ({row['observacoes']})" if row["observacoes"] and str(row["observacoes"]) != "nan" else ""
        relatorio += f"• {c_id}: {val}{obs}\n"

    relatorio += f"""

Com os melhores cumprimentos,
Joel Machado Rocha
E-REDES
"""
    return relatorio

# Carga inicial dos dados
df_obras, df_respostas = carregar_dados_sheets()

if "obra_selecionada" not in st.session_state:
    st.session_state.obra_selecionada = None

# --- SIDEBAR ---
st.sidebar.title("⚡ PIs & PITs - E-REDES")
st.sidebar.caption("Gestão de Processos")
st.sidebar.markdown("---")

if st.session_state.obra_selecionada:
    if st.sidebar.button("⬅️ Voltar ao Dashboard", use_container_width=True):
        st.session_state.obra_selecionada = None
        st.rerun()

with st.sidebar.expander("📦 Obras em Arquivo", expanded=False):
    df_arq = df_obras[df_obras["arquivado"] == "Sim"]
    
    if df_arq.empty:
        st.caption("Nenhuma obra no arquivo.")
    else:
        for idx, row in df_arq.iterrows():
            ref_arq = row["nome_ptd"]
            c_txt, c_btn = st.columns([1.8, 1.2])
            c_txt.caption(f"📁 {ref_arq}")
            
            if c_btn.button("Desarq.", key=f"desarq_side_{ref_arq}", use_container_width=True):
                df_obras.loc[df_obras["nome_ptd"] == ref_arq, "arquivado"] = "Não"
                guardar_obras_sheets(df_obras)
                st.rerun()

# --- DASHBOARD PRINCIPAL ---
if st.session_state.obra_selecionada is None:
    st.title("📁 Gestão de PIs / AITs / PTDs")
    st.subheader("Base de Dados do Google Sheets")
    st.markdown("---")
    
    # Criar Nova Obra
    with st.expander("➕ REGISTAR NOVO PTD", expanded=False):
        col_n1, col_n2 = st.columns([3, 1])
        nova_ref = col_n1.text_input("Nome do PTD", placeholder="Ex: PTD 0158 PFR - TP1")
        nova_data = col_n2.date_input("Data de Corte", value=datetime.now().date())
        
        if st.button("Registar PTD", type="primary"):
            nova_ref_clean = nova_ref.strip()
            
            if nova_ref_clean == "":
                st.error("Insira um nome válido.")
            elif nova_ref_clean in df_obras["nome_ptd"].values:
                st.error("Este PTD já se encontra registado.")
            else:
                nova_obra_df = pd.DataFrame([{
                    "nome_ptd": nova_ref_clean,
                    "data_corte": str(nova_data),
                    "dp_aplicavel": "Não Aplicável",
                    "data_descargas_parciais": "",
                    "arquivado": "Não"
                }])
                
                df_obras = pd.concat([df_obras, nova_obra_df], ignore_index=True)
                guardar_obras_sheets(df_obras)
                
                campos_padrao = ["croqui", "rc", "obra_dm", "pi", "pit", "clientes", "geradores", "croqui_celas"]
                novas_respostas = []
                for campo in campos_padrao:
                    novas_respostas.append({
                        "nome_ptd": nova_ref_clean,
                        "campo_id": campo,
                        "valor": "",
                        "observacoes": ""
                    })
                
                df_respostas = pd.concat([df_respostas, pd.DataFrame(novas_respostas)], ignore_index=True)
                guardar_respostas_sheets(df_respostas)
                
                st.success("PTD adicionado ao Google Sheets com sucesso!")
                st.rerun()

    # Lista de Obras Ativas
    st.markdown("### 🏬 PTDs em Acompanhamento")
    df_ativas = df_obras[df_obras["arquivado"] != "Sim"]
    
    if df_ativas.empty:
        st.info("Nenhum PTD ativo no momento.")
    else:
        for idx, row in df_ativas.iterrows():
            ref = row["nome_ptd"]
            dt = row["data_corte"]
            dp = row["dp_aplicavel"]
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 2.5, 1, 1])
                c1.markdown(f"#### ⚡ {ref}")
                c2.markdown(f"📅 **Corte:** {dt}")
                c3.markdown(f"⚙️ **DP Aplicável:** {dp}")
                    
                if c4.button("Abrir 📂", key=f"btn_open_{ref}", use_container_width=True):
                    st.session_state.obra_selecionada = ref
                    st.rerun()
                    
                if c5.button("Arquivar 📦", key=f"btn_arq_{ref}", use_container_width=True):
                    df_obras.loc[df_obras["nome_ptd"] == ref, "arquivado"] = "Sim"
                    guardar_obras_sheets(df_obras)
                    st.rerun()

# --- ECRÃ DE EDIÇÃO DO PTD ---
else:
    ref_atual = st.session_state.obra_selecionada
    st.title(f"⚡ PTD: {ref_atual}")
    st.markdown("---")

    with st.expander("✉️ GERAR RESUMO PARA E-MAIL", expanded=False):
        txt_email = gerar_relatorio_email(ref_atual, df_obras, df_respostas)
        st.code(txt_email, language="text")

    resp_obra = df_respostas[df_respostas["nome_ptd"] == ref_atual]
    modificado = False

    for categoria, itens in CHECKLIST_ESTRUTURA.items():
        with st.expander(f"📂 {categoria.upper()}", expanded=True):
            for item in itens:
                i_id = item["id"]
                match_idx = df_respostas[(df_respostas["nome_ptd"] == ref_atual) & (df_respostas["campo_id"] == i_id)].index
                
                if not match_idx.empty:
                    idx = match_idx[0]
                    c_txt, c_est, c_obs = st.columns([4, 3, 4])
                    
                    c_txt.markdown(f"**{i_id}** - {item['texto']}")
                    
                    val_atual = str(df_respostas.loc[idx, "valor"])
                    v_est = c_est.text_input(f"Valor_{i_id}", value="" if val_atual == "nan" else val_atual, label_visibility="collapsed")
                    
                    obs_atual = str(df_respostas.loc[idx, "observacoes"])
                    v_obs = c_obs.text_input(f"Obs_{i_id}", value="" if obs_atual == "nan" else obs_atual, placeholder="Observações...", label_visibility="collapsed")
                    
                    if v_est != val_atual or v_obs != obs_atual:
                        df_respostas.loc[idx, "valor"] = v_est
                        df_respostas.loc[idx, "observacoes"] = v_obs
                        modificado = True

    if modificado:
        guardar_respostas_sheets(df_respostas)
        st.rerun()
