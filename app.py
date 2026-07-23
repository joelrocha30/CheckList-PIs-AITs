import streamlit as st
import json
import os
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="CHECKLIST DE PIs/AITs - E-REDES",
    page_icon="⚡",
    layout="wide"
)

DB_FILE = "historico_ptd_ps.json"

# Estrutura atualizada da Checklist com as novas opções e nomes
CAMPOS_CHECKLIST = [
    {
        "id": "croqui", 
        "label": "Croqui", 
        "tipo": "selecao", 
        "opcoes": ["Não Feito", "Feito"]
    },
    {
        "id": "rc", 
        "label": "RC (Responsável de Trabalhos)", 
        "tipo": "texto",
        "placeholder": "Nome da pessoa..."
    },
    {
        "id": "obra_dm", 
        "label": "Obra DM", 
        "tipo": "texto",
        "placeholder": "Número da Obra DM"
    },
    {
        "id": "pi", 
        "label": "Pedido de Indisponibilidade", 
        "tipo": "selecao", 
        "opcoes": ["Não Feito", "Feito e Guardado", "Feito e Submetido", "Feito e Aprovado"]
    },
    {
        "id": "pit", 
        "label": "Pedido de Intervenção em Tensão", 
        "tipo": "selecao", 
        "opcoes": ["Não Feito", "Feito e Guardado", "Feito e Submetido", "Feito e Aprovado"]
    },
    {
        "id": "clientes", 
        "label": "PTC Afetados?", 
        "tipo": "selecao", 
        "opcoes": ["Não", "Sim, Não foram contactados", "Sim, Já foram contactados"]
    },
    {
        "id": "geradores", 
        "label": "Tem Geradores?", 
        "tipo": "selecao", 
        "opcoes": ["Não", "Sim"]
    },
    {
        "id": "croqui_celas", 
        "label": "Croqui para Identificação das Celas", 
        "tipo": "selecao", 
        "opcoes": ["Não Feito", "Feito", "Feito e Enviado"]
    }
]

# Funções para gestão dos dados locais
def carregar_dados():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_dados(dados):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def criar_novo_ptd(nome_ptd, data_corte, dp_aplicavel, data_dp):
    return {
        "metadados": {
            "nome_ptd": nome_ptd,
            "data_corte": str(data_corte),
            "dp_aplicavel": dp_aplicavel,
            "data_descargas_parciais": str(data_dp)
        },
        "respostas": {
            campo["id"]: {
                "valor": campo.get("opcoes", [""])[0] if campo["tipo"] == "selecao" else "", 
                "observacoes": ""
            } for campo in CAMPOS_CHECKLIST
        }
    }

# Inicialização de Estado
if "db_ptd" not in st.session_state:
    st.session_state.db_ptd = carregar_dados()
if "ptd_selecionado" not in st.session_state:
    st.session_state.ptd_selecionado = None

db = st.session_state.db_ptd

# Barra Lateral
st.sidebar.title("⚡ CHECKLIST DE PIs / AITs")
st.sidebar.markdown("**Fiscal:** Joel Machado Rocha")

if st.session_state.ptd_selecionado:
    if st.sidebar.button("⬅️ Voltar ao Histórico", use_container_width=True):
        st.session_state.ptd_selecionado = None
        st.rerun()

# --- ECRÃ 1: HISTÓRICO DE OBRAS ---
if st.session_state.ptd_selecionado is None:
    st.title("📂 CHECKLIST DE PIs / AITs - Registos")
    st.subheader("Selecione um PTD/PS existente ou inicie um novo processo")
    st.markdown("---")

    # Novo Registo
    with st.expander("➕ REGISTAR NOVO PTD / PS", expanded=False):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        nome_ptd = c1.text_input("Nome PTD / PS", placeholder="Ex: PTD FLG 0266")
        dt_corte = c2.date_input("Data do Corte", value=datetime.now().date())
        
        dp_app = c3.selectbox("Descargas Parciais?", ["Aplicável", "Não Aplicável"])
        dt_dp = c4.date_input("Data Descargas Parciais", value=datetime.now().date(), disabled=(dp_app == "Não Aplicável"))

        if st.button("Criar Registo", type="primary"):
            if not nome_ptd.strip():
                st.error("Escreva o Nome do PTD/PS.")
            elif nome_ptd in db:
                st.error("Já existe um registo com este Nome PTD/PS!")
            else:
                db[nome_ptd] = criar_novo_ptd(nome_ptd, dt_corte, dp_app, dt_dp)
                guardar_dados(db)
                st.session_state.ptd_selecionado = nome_ptd
                st.rerun()

    st.markdown("### 🏬 Histórico de Intervenções")
    if not db:
        st.info("Nenhum PTD/PS registado. Clique no botão acima para adicionar.")
    else:
        for ptd_key, ptd_data in list(db.items()):
            meta = ptd_data["metadados"]
            dp_info = meta.get("data_descargas_parciais", "N/A") if meta.get("dp_aplicavel", "Aplicável") == "Aplicável" else "Não Aplicável"
            
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                col1.markdown(f"#### ⚡ Obra: {meta['nome_ptd']}")
                col2.markdown(f"📅 **Corte:** {meta['data_corte']}")
                col3.markdown(f"⚡ **Descargas Parciais:** {dp_info}")

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

    # Título conforme pedido: Obra : Nome do PTD
    st.title(f"⚡ Obra: {meta['nome_ptd']}")
    st.markdown("---")

    # Cabeçalho com Datas e Opção de Descargas Parciais
    with st.container(border=True):
        c_m1, c_m2, c_m3, c_m4 = st.columns([2, 2, 1.5, 2])
        c_m1.markdown(f"**Nome PTD/PS:** `{meta['nome_ptd']}`")

        # Ajuste de Data do Corte
        dt_corte_val = datetime.strptime(meta["data_corte"], "%Y-%m-%d").date()
        nova_dt_corte = c_m2.date_input("Data do Corte", value=dt_corte_val, key="dt_corte_head")

        # Estado e Data das Descargas Parciais
        dp_aplicavel_atual = meta.get("dp_aplicavel", "Aplicável")
        novo_dp_app = c_m3.selectbox("Descargas Parciais", ["Aplicável", "Não Aplicável"], index=0 if dp_aplicavel_atual == "Aplicável" else 1, key="dp_app_head")

        try:
            dt_dp_val = datetime.strptime(meta["data_descargas_parciais"], "%Y-%m-%d").date()
        except:
            dt_dp_val = datetime.now().date()

        nova_dt_dp = c_m4.date_input(
            "Data das Descargas Parciais", 
            value=dt_dp_val, 
            disabled=(novo_dp_app == "Não Aplicável"), 
            key="dt_dp_head"
        )

        # Atualizar metadados se alterados
        if (str(nova_dt_corte) != meta["data_corte"] or 
            novo_dp_app != dp_aplicavel_atual or 
            str(nova_dt_dp) != meta["data_descargas_parciais"]):
            
            db[ptd_key]["metadados"]["data_corte"] = str(nova_dt_corte)
            db[ptd_key]["metadados"]["dp_aplicavel"] = novo_dp_app
            db[ptd_key]["metadados"]["data_descargas_parciais"] = str(nova_dt_dp)
            guardar_dados(db)
            st.rerun()

    st.markdown("### 📋 Checklist e Elementos de Processo")

    for item in CAMPOS_CHECKLIST:
        i_id = item["id"]
        i_label = item["label"]
        i_tipo = item.get("tipo", "texto")
        i_ph = item.get("placeholder", "Notas suplementares...")

        # Garantir estrutura
        if i_id not in resps:
            resps[i_id] = {"valor": "", "observacoes": ""}

        dados_item = resps[i_id]

        with st.container(border=True):
            col_lbl, col_val, col_obs = st.columns([2.5, 3, 3.5])

            col_lbl.markdown(f"**{i_label}**")

            # Entrada de Seleção
            if i_tipo == "selecao":
                opcoes = item.get("opcoes", [])
                val_atual = dados_item.get("valor", opcoes[0])
                idx = opcoes.index(val_atual) if val_atual in opcoes else 0
                
                novo_val = col_val.selectbox(f"Val_{i_id}", opcoes, index=idx, label_visibility="collapsed")
                nova_obs = col_obs.text_input(f"Obs_{i_id}", value=dados_item.get("observacoes", ""), placeholder="Notas suplementares...", label_visibility="collapsed")

            # Entrada de Texto
            elif i_tipo == "texto":
                novo_val = col_val.text_input(f"Val_{i_id}", value=dados_item.get("valor", ""), placeholder=i_ph, label_visibility="collapsed")
                nova_obs = col_obs.text_input(f"Obs_{i_id}", value=dados_item.get("observacoes", ""), placeholder="Notas suplementares...", label_visibility="collapsed")

            # Gravação automática ao alterar qualquer valor
            if novo_val != dados_item.get("valor") or nova_obs != dados_item.get("observacoes"):
                db[ptd_key]["respostas"][i_id]["valor"] = novo_val
                db[ptd_key]["respostas"][i_id]["observacoes"] = nova_obs
                guardar_dados(db)
                st.rerun()
