import streamlit as st
import json
import os
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Registo de Intervenção PTD/PS - E-REDES",
    page_icon="⚡",
    layout="wide"
)

DB_FILE = "historico_ptd_ps.json"

# Campos estruturados da nova Checklist / Ficha de Campo
CAMPOS_CHECKLIST = [
    {"id": "croqui", "label": "Croqui", "tipo": "texto"},
    {"id": "rc", "label": "RC (Responsável pelos Trabalhos / Condução)", "tipo": "texto"},
    {"id": "obra_dm", "label": "Obra DM", "tipo": "texto"},
    {"id": "pi", "label": "PI (Pedido de Intervenção)", "tipo": "texto"},
    {"id": "pit", "label": "PIT (Plano de Intervenção Técnica)", "tipo": "texto"},
    {"id": "clientes", "label": "Clientes Afetados?", "tipo": "selecao", "opcoes": ["Não", "Sim - MT", "Sim - BT", "Sim - MT e BT"]},
    {"id": "croqui_celas", "label": "Croqui para Identificação das Celas", "tipo": "estado_obs"}
]

# Funções para gestão dos dados em JSON local
def carregar_dados():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_dados(dados):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def criar_novo_ptd(nome_ptd, data_corte, data_dp):
    return {
        "metadados": {
            "nome_ptd": nome_ptd,
            "data_corte": str(data_corte),
            "data_descargas_parciais": str(data_dp)
        },
        "respostas": {campo["id"]: {"valor": "", "estado": "Pendente", "observacoes": ""} for campo in CAMPOS_CHECKLIST}
    }

# Inicialização de Estado
if "db_ptd" not in st.session_state:
    st.session_state.db_ptd = carregar_dados()
if "ptd_selecionado" not in st.session_state:
    st.session_state.ptd_selecionado = None

db = st.session_state.db_ptd

# Barra Lateral
st.sidebar.title("⚡ Gestão de PTD / PS")
st.sidebar.markdown("**Fiscal:** Joel Machado Rocha")

if st.session_state.ptd_selecionado:
    if st.sidebar.button("⬅️ Voltar ao Histórico", use_container_width=True):
        st.session_state.ptd_selecionado = None
        st.rerun()

# --- ECRÃ 1: HISTÓRICO DE PTD/PS ---
if st.session_state.ptd_selecionado is None:
    st.title("📋 Registos de Intervenção e Ensaio - PTD / PS")
    st.subheader("Selecione um PTD/PS existente ou inicie um novo processo")
    st.markdown("---")

    # Novo Registo
    with st.expander("➕ REGISTAR NOVO PTD / PS", expanded=False):
        c1, c2, c3 = st.columns([2, 1, 1])
        nome_ptd = c1.text_input("Nome PTD / PS", placeholder="Ex: PTD-PRD-0124")
        dt_corte = c2.date_input("Data do Corte", value=datetime.now().date())
        dt_dp = c3.date_input("Data Descargas Parciais", value=datetime.now().date())

        if st.button("Criar Registo", type="primary"):
            if not nome_ptd.strip():
                st.error("Escreva o Nome do PTD/PS.")
            elif nome_ptd in db:
                st.error("Já existe um registo com este Nome PTD/PS!")
            else:
                db[nome_ptd] = criar_novo_ptd(nome_ptd, dt_corte, dt_dp)
                guardar_dados(db)
                st.session_state.ptd_selecionado = nome_ptd
                st.rerun()

    st.markdown("### 🏬 Histórico de Intervenções")
    if not db:
        st.info("Nenhum PTD/PS registado. Clique no botão acima para adicionar.")
    else:
        for ptd_key, ptd_data in list(db.items()):
            meta = ptd_data["metadados"]
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                col1.markdown(f"#### ⚡ {meta['nome_ptd']}")
                col2.markdown(f"📅 **Corte:** {meta['data_corte']}")
                col3.markdown(f"⚡ **Descargas Parciais:** {meta['data_descargas_parciais']}")

                if col4.button("Abrir 📂", key=f"open_{ptd_key}", use_container_width=True):
                    st.session_state.ptd_selecionado = ptd_key
                    st.rerun()

                if st.sidebar.checkbox(f"Apagar {ptd_key}", key=f"del_chk_{ptd_key}"):
                    if st.sidebar.button(f"🗑️ Confirmar apagar {ptd_key}", key=f"del_btn_{ptd_key}"):
                        del db[ptd_key]
                        guardar_dados(db)
                        st.rerun()

# --- ECRÃ 2: FICHA DE CAMPO DO PTD/PS ---
else:
    ptd_key = st.session_state.ptd_selecionado
    ptd_obj = db[ptd_key]
    meta = ptd_obj["metadados"]
    resps = ptd_obj["respostas"]

    st.title(f"⚡ Ficha de Campo: {meta['nome_ptd']}")

    # Cabeçalho com as datas principais editáveis
    with st.container(border=True):
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.markdown(f"**Nome PTD/PS:** `{meta['nome_ptd']}`")

        # Permitir ajustar datas se necessário
        dt_corte_val = datetime.strptime(meta["data_corte"], "%Y-%m-%d").date()
        nova_dt_corte = c_m2.date_input("Data do Corte", value=dt_corte_val, key="dt_corte_head")

        dt_dp_val = datetime.strptime(meta["data_descargas_parciais"], "%Y-%m-%d").date()
        nova_dt_dp = c_m3.date_input("Data das Descargas Parciais", value=dt_dp_val, key="dt_dp_head")

        if str(nova_dt_corte) != meta["data_corte"] or str(nova_dt_dp) != meta["data_descargas_parciais"]:
            db[ptd_key]["metadados"]["data_corte"] = str(nova_dt_corte)
            db[ptd_key]["metadados"]["data_descargas_parciais"] = str(nova_dt_dp)
            guardar_dados(db)
            st.rerun()

    st.markdown("### 📋 Checklist e Elementos de Processo")

    modificado = False

    for item in CAMPOS_CHECKLIST:
        i_id = item["id"]
        i_label = item["label"]
        i_tipo = item.get("tipo", "texto")

        # Garantir estrutura no dicionário
        if i_id not in resps:
            resps[i_id] = {"valor": "", "estado": "Pendente", "observacoes": ""}

        dados_item = resps[i_id]

        with st.container(border=True):
            col_lbl, col_val, col_obs = st.columns([2.5, 3, 3.5])

            col_lbl.markdown(f"**{i_label}**")

            # Interface dinâmicas conforme o tipo de elemento
            if i_tipo == "texto":
                novo_val = col_val.text_input(f"Val_{i_id}", value=dados_item.get("valor", ""), placeholder="Indique a referência / código...", label_visibility="collapsed")
                novo_est = dados_item.get("estado", "Conforme")
                nova_obs = col_obs.text_input(f"Obs_{i_id}", value=dados_item.get("observacoes", ""), placeholder="Notas suplementares...", label_visibility="collapsed")

            elif i_tipo == "selecao":
                opcoes = item.get("opcoes", ["Não", "Sim"])
                val_atual = dados_item.get("valor", opcoes[0])
                idx = opcoes.index(val_atual) if val_atual in opcoes else 0
                novo_val = col_val.selectbox(f"Val_{i_id}", opcoes, index=idx, label_visibility="collapsed")
                novo_est = "Conforme"
                nova_obs = col_obs.text_input(f"Obs_{i_id}", value=dados_item.get("observacoes", ""), placeholder="Detalhes dos clientes...", label_visibility="collapsed")

            elif i_tipo == "estado_obs":
                novo_val = dados_item.get("valor", "")
                opcoes_est = ["Pendente", "Conforme", "Incompleto / Com Anomalia"]
                est_atual = dados_item.get("estado", "Pendente")
                idx_e = opcoes_est.index(est_atual) if est_atual in opcoes_est else 0

                novo_est = col_val.selectbox(f"Est_{i_id}", opcoes_est, index=idx_e, label_visibility="collapsed")
                nova_obs = col_obs.text_input(f"Obs_{i_id}", value=dados_item.get("observacoes", ""), placeholder="Esquema das celas / notas...", label_visibility="collapsed")

            # Gravação automática ao alterar
            if novo_val != dados_item.get("valor") or novo_est != dados_item.get("estado") or nova_obs != dados_item.get("observacoes"):
                db[ptd_key]["respostas"][i_id]["valor"] = novo_val
                db[ptd_key]["respostas"][i_id]["estado"] = novo_est
                db[ptd_key]["respostas"][i_id]["observacoes"] = nova_obs
                guardar_dados(db)
                st.rerun()
