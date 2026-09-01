import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials

# Configuração da página
st.set_page_config(
    page_title="CHECKLIST DE PIs / AITs - E-REDES",
    page_icon="⚡",
    layout="wide"
)

# Conexão com Google Sheets
@st.cache_resource(ttl=3600)
def conectar_gsheets():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        sheet_url = creds_dict.pop("spreadsheet", None)
        creds_dict.pop("type", None)
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        if not sheet_url:
            st.error("URL da folha de cálculo não encontrado nos secrets.")
            st.stop()
            
        return client.open_by_url(sheet_url)
    except Exception as e:
        st.error(f"Erro ao ligar ao Google Sheets: {e}")
        st.stop()

doc_sheets = conectar_gsheets()

# Opções para os menus Dropdown (selectbox)
OPCOES_CAMPOS = {
    "croqui": ["Pendente", "Feito", "Não Feito", "Não Aplicável"],
    "rc": ["Pendente", "Luis", "Outro", "Não Aplicável"],
    "obra_dm": ["Pendente", "086071/2026", "Inserido", "Não Aplicável"],
    "pi": ["Pendente", "Não Feito", "Feito e Guardado", "Feito e Submetido", "Feito e Aprovado", "Não Aplicável"],
    "pit": ["Pendente", "Não Feito", "Feito e Guardado", "Feito e Submetido", "Feito e Aprovado", "Não Aplicável"],
    "clientes": ["Pendente", "Sim", "Não", "Não Aplicável"],
    "geradores": ["Pendente", "Sim", "Não", "Não Aplicável"],
    "croqui_celas": ["Pendente", "Feito", "Não Feito", "Não Aplicável"]
}

OPCOES_PADRAO = ["Pendente", "Feito", "Não Feito", "Sim", "Não", "Feito e Aprovado", "Não Aplicável"]

# Estrutura Completa da Checklist
CHECKLIST_ESTRUTURA = {
    "1. CONSTRUÇÃO CIVIL E INFRAESTRUTURA": [
        {"id": "croqui", "texto": "croqui - Acesso direto e desimpedido a partir da via pública (Croqui)."},
        {"id": "rc", "texto": "rc - Responsável de Cobrança / Contacto em Obra."},
        {"id": "obra_dm", "texto": "obra_dm - Número / Registo Obra DM."}
    ],
    "2. PROCESSOS E LICENCIAMENTO": [
        {"id": "pi", "texto": "pi - Processo de Instalação (PI) Feito e Aprovado."},
        {"id": "pit", "texto": "pit - Processo de Infraestruturas de Telecomunicações (PIT) Feito e Aprovado."}
    ],
    "3. CLIENTES E EQUIPAMENTOS AUXILIARES": [
        {"id": "clientes", "texto": "clientes - Clientes já foram contactados / Notificados."},
        {"id": "geradores", "texto": "geradores - Necessidade / Utilização de Geradores."},
        {"id": "croqui_celas", "texto": "croqui_celas - Croqui de Celas Feito e Enviado."}
    ]
}

# --- PERSISTÊNCIA E BACKUP ---
def garantir_separador_backup(nome_backup):
    try:
        return doc_sheets.worksheet(nome_backup)
    except gspread.exceptions.WorksheetNotFound:
        return doc_sheets.add_worksheet(title=nome_backup, rows="1000", cols="20")

def salvar_com_backup(nome_aba, df):
    ws = doc_sheets.worksheet(nome_aba)
    dados = [df.columns.values.tolist()] + df.astype(str).values.tolist()
    
    ws.clear()
    ws.update(dados)
    
    try:
        ws_bkp = garantir_separador_backup(f"{nome_aba}_Backup")
        df_bkp = df.copy()
        df_bkp["_data_backup"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dados_bkp = [df_bkp.columns.values.tolist()] + df_bkp.astype(str).values.tolist()
        ws_bkp.clear()
        ws_bkp.update(dados_bkp)
    except Exception as e:
        st.warning(f"Aviso de backup ({nome_aba}): {e}")

def carregar_dados_sheets():
    ws_obras = doc_sheets.worksheet("Obras")
    ws_respostas = doc_sheets.worksheet("Respostas")
    
    df_obras = pd.DataFrame(ws_obras.get_all_records()).fillna("")
    df_respostas = pd.DataFrame(ws_respostas.get_all_records()).fillna("")
    
    if "forcar_desarquivado" not in df_obras.columns:
        df_obras["forcar_desarquivado"] = "Não"
        
    hoje = date.today()
    alterado = False
    
    # Verifica arquivamento automático (apenas se forcar_desarquivado != "Sim")
    if not df_obras.empty and "data_corte" in df_obras.columns:
        for idx, row in df_obras.iterrows():
            data_str = str(row["data_corte"]).strip()
            forcar = str(row.get("forcar_desarquivado", "Não"))
            
            if data_str and forcar != "Sim":
                try:
                    dt_corte = datetime.strptime(data_str, "%Y-%m-%d").date()
                    if dt_corte < hoje and row.get("arquivado") != "Sim":
                        df_obras.loc[idx, "arquivado"] = "Sim"
                        alterado = True
                except ValueError:
                    pass
                    
    if alterado:
        salvar_com_backup("Obras", df_obras)
        
    return df_obras, df_respostas

def gerar_relatorio_email(ref_obra, df_obras, df_respostas):
    obra_row = df_obras[df_obras["nome_ptd"] == ref_obra]
    data_corte = obra_row["data_corte"].values[0] if not obra_row.empty else datetime.now().strftime("%Y-%m-%d")
    resp_obra = df_respostas[df_respostas["nome_ptd"] == ref_obra]
    
    total_itens = len(resp_obra)
    feitos = sum(resp_obra["valor"].astype(str).str.contains("Feito|Conforme|Sim|Aprovado", case=False, na=False))
    prog = int((feitos / total_itens) * 100) if total_itens > 0 else 0

    relatorio = f"""Assunto: [Acompanhamento PIs/PITs] Estado do PTD - {ref_obra}

Viva,

Segue o ponto de situação do PTD {ref_obra} (Data de Corte: {data_corte}).

--- RESUMO DA AVALIAÇÃO ---
• Instalação / PTD: {ref_obra}
• Progresso Geral: {prog}%

--- DETALHE DOS CAMPOS ---
"""
    for idx, row in resp_obra.iterrows():
        c_id = row["campo_id"]
        val = row["valor"] if row["valor"] else "Pendente"
        obs = f" ({row['observacoes']})" if row["observacoes"] and str(row["observacoes"]) != "nan" else ""
        relatorio += f"• {c_id}: {val}{obs}\n"

    relatorio += """

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

with st.sidebar.expander("📦 Obras Arquivadas", expanded=False):
    df_arq = df_obras[df_obras["arquivado"] == "Sim"]
    
    if df_arq.empty:
        st.caption("Nenhuma obra no arquivo.")
    else:
        for idx, row in df_arq.iterrows():
            ref_arq = row["nome_ptd"]
            st.markdown(f"**📁 {ref_arq}** (Corte: {row.get('data_corte', 'N/A')})")
            
            c_abrir, c_desarq = st.columns(2)
            if c_abrir.button("Editar ✏️", key=f"edit_side_{ref_arq}", use_container_width=True):
                st.session_state.obra_selecionada = ref_arq
                st.rerun()
                
            if c_desarq.button("Desarq. 🔓", key=f"desarq_side_{ref_arq}", use_container_width=True):
                # Marca a obra para sair do arquivo e não voltar automaticamente
                df_obras.loc[df_obras["nome_ptd"] == ref_arq, "arquivado"] = "Não"
                df_obras.loc[df_obras["nome_ptd"] == ref_arq, "forcar_desarquivado"] = "Sim"
                salvar_com_backup("Obras", df_obras)
                st.rerun()
            st.markdown("---")

# --- DASHBOARD PRINCIPAL ---
if st.session_state.obra_selecionada is None:
    st.title("📁 Gestão de PIs / AITs / PTDs")
    st.subheader("Painel Principal de Acompanhamento")
    st.markdown("---")
    
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
                    "arquivado": "Não",
                    "forcar_desarquivado": "Não"
                }])
                
                df_obras = pd.concat([df_obras, nova_obra_df], ignore_index=True)
                salvar_com_backup("Obras", df_obras)
                
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
                salvar_com_backup("Respostas", df_respostas)
                
                st.success("PTD adicionado com sucesso!")
                st.rerun()

    st.markdown("### 🏬 PTDs Ativos (Em Acompanhamento)")
    df_ativas = df_obras[df_obras["arquivado"] != "Sim"]
    
    if df_ativas.empty:
        st.info("Nenhum PTD ativo no momento.")
    else:
        for idx, row in df_ativas.iterrows():
            ref = row["nome_ptd"]
            dt = row["data_corte"]
            dp = row.get("dp_aplicavel", "N/A")
            
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
                    df_obras.loc[df_obras["nome_ptd"] == ref, "forcar_desarquivado"] = "Não"
                    salvar_com_backup("Obras", df_obras)
                    st.rerun()

# --- ECRÃ DE EDIÇÃO DO PTD (LAYOUT FIEL À IMAGEM) ---
else:
    ref_atual = st.session_state.obra_selecionada
    
    e_arquivado = df_obras.loc[df_obras["nome_ptd"] == ref_atual, "arquivado"].values
    if len(e_arquivado) > 0 and e_arquivado[0] == "Sim":
        st.warning("⚠️ Esta obra encontra-se no Arquivo. Pode efetuar alterações ou desarquivá-la no menu lateral.")

    # Bloco superior para gerar e-mail
    with st.expander(" >  📄 GERAR RESUMO PARA E-MAIL", expanded=False):
        txt_email = gerar_relatorio_email(ref_atual, df_obras, df_respostas)
        st.code(txt_email, language="text")

    resp_obra = df_respostas[df_respostas["nome_ptd"] == ref_atual]
    modificado = False

    # Renderização idêntica à imagem anexada
    for categoria, itens in CHECKLIST_ESTRUTURA.items():
        with st.expander(f"📁 {categoria}", expanded=True):
            for item in itens:
                i_id = item["id"]
                match_idx = df_respostas[(df_respostas["nome_ptd"] == ref_atual) & (df_respostas["campo_id"] == i_id)].index
                
                if not match_idx.empty:
                    idx = match_idx[0]
                    col_txt, col_sel, col_obs = st.columns([5, 3, 3])
                    
                    # Nome do campo + Descrição do item em negrito
                    col_txt.markdown(f"**{item['texto']}**")
                    
                    val_atual = str(df_respostas.loc[idx, "valor"]).strip()
                    opcoes = OPCOES_CAMPOS.get(i_id, OPCOES_PADRAO)
                    
                    if val_atual and val_atual not in opcoes:
                        opcoes = [val_atual] + opcoes
                        
                    idx_opcao = opcoes.index(val_atual) if val_atual in opcoes else 0
                    
                    v_est = col_sel.selectbox(
                        f"Select_{i_id}",
                        options=opcoes,
                        index=idx_opcao,
                        key=f"sb_{ref_atual}_{i_id}",
                        label_visibility="collapsed"
                    )
                    
                    obs_atual = str(df_respostas.loc[idx, "observacoes"])
                    v_obs = col_obs.text_input(
                        f"Obs_{i_id}",
                        value="" if obs_atual in ["nan", "None"] else obs_atual,
                        placeholder="Observações...",
                        key=f"ti_{ref_atual}_{i_id}",
                        label_visibility="collapsed"
                    )
                    
                    if v_est != val_atual or v_obs != obs_atual:
                        df_respostas.loc[idx, "valor"] = v_est
                        df_respostas.loc[idx, "observacoes"] = v_obs
                        modificado = True

    if modificado:
        salvar_com_backup("Respostas", df_respostas)
        st.rerun()
