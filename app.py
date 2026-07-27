import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="CHECKLIST DE PIs/AITs - E-REDES",
    page_icon="⚡",
    layout="wide"
)

# Estrutura da Checklist
CAMPOS_CHECKLIST = [
    {"id": "croqui", "label": "Croqui", "tipo": "selecao", "opcoes": ["Não Feito", "Feito"]},
    {"id": "rc", "label": "RC (Responsável de Trabalhos)", "tipo": "texto", "placeholder": "Nome da pessoa..."},
    {"id": "obra_dm", "label": "Obra DM", "tipo": "texto", "placeholder": "Número da Obra DM"},
    {"id": "pi", "label": "PI -Pedido de Indisponibilidade", "tipo": "selecao", "opcoes": ["Não Feito", "Feito e Guardado", "Feito e Submetido", "Feito e Aprovado"]},
    {"id": "pit", "label": "PIT -Pedido de Intervenção em Tensão", "tipo": "selecao", "opcoes": ["Não Feito", "Feito e Guardado", "Feito e Submetido", "Feito e Aprovado"]},
    {"id": "clientes", "label": "PTC Afetados?", "tipo": "selecao", "opcoes": ["Não", "Sim, Não foram contactados", "Sim, Já foram contactados"]},
    {"id": "geradores", "label": "Tem Geradores?", "tipo": "selecao", "opcoes": ["Não", "Sim"]},
    {"id": "croqui_celas", "label": "Croqui para Identificação das Celas", "tipo": "selecao", "opcoes": ["Não Feito", "Feito", "Feito e Enviado"]}
]

# Inicializar Ligação ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Função com CACHE para evitar o erro de limite de requisições (429)
@st.cache_data(ttl=300) # Mantém dados em cache durante 5 minutos
def carregar_dados():
    try:
        df_o = conn.read(worksheet="Obras")
    except Exception:
        df_o = pd.DataFrame(columns=["nome_ptd", "data_corte", "dp_aplicavel", "data_descargas_parciais"])

    try:
        df_r = conn.read(worksheet="Respostas")
    except Exception:
        df_r = pd.DataFrame(columns=["nome_ptd", "campo_id", "valor", "observacoes"])

    # Conversão de segurança para evitar o erro de 'float64'
    if not df_o.empty:
        for col in df_o.columns:
            df_o[col] = df_o[col].fillna("").astype(str)

    if not df_r.empty:
        for col in df_r.columns:
            df_r[col] = df_r[col].fillna("").astype(str)

    return df_o, df_r

df_obras, df_respostas = carregar_dados()

# Estado de Navegação
if "ptd_selecionado" not in st.session_state:
    st.session_state.ptd_selecionado = None

# Barra Lateral
st.sidebar.title("⚡ Lista de Obras")
st.sidebar.markdown("**Fiscal:** Joel Machado Rocha")

if st.session_state.ptd_selecionado:
    if st.sidebar.button("⬅️ Voltar ao Histórico", use_container_width=True):
        st.session_state.ptd_selecionado = None
        st.rerun()

# --- ECRÃ 1: HISTÓRICO DE OBRAS ---
if st.session_state.ptd_selecionado is None:
    st.title("📂 CHECKLIST DE PIs / AITs - Registos")
    st.subheader("Selecione uma Obra ou Crie uma nova")
    st.markdown("---")

    # Registar Nova Obra
    with st.expander("➕ REGISTAR NOVA OBRA", expanded=False):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        nome_ptd = c1.text_input("Nome da Obra", placeholder="Ex: PTD FLG 0266")
        dt_corte = c2.date_input("Data do Corte", value=datetime.now().date())
        dp_app = c3.selectbox("Descargas Parciais?", ["Aplicável", "Não Aplicável"])
        dt_dp = c4.date_input("Data Descargas Parciais", value=datetime.now().date(), disabled=(dp_app == "Não Aplicável"))

        if st.button("Criar Registo", type="primary"):
            nome_clean = nome_ptd.strip()
            if not nome_clean:
                st.error("Escreva o Nome da Obra e/ou PTD/PS.")
            elif not df_obras.empty and "nome_ptd" in df_obras.columns and nome_clean in df_obras["nome_ptd"].values:
                st.error("Já existe um registo com esta Obra!")
            else:
                # Criar novos dataframes
                nova_obra = pd.DataFrame([{
                    "nome_ptd": str(nome_clean),
                    "data_corte": str(dt_corte),
                    "dp_aplicavel": str(dp_app),
                    "data_descargas_parciais": str(dt_dp)
                }])
                df_obras = pd.concat([df_obras, nova_obra], ignore_index=True)

                novas_respostas = []
                for campo in CAMPOS_CHECKLIST:
                    val_padrao = campo["opcoes"][0] if campo["tipo"] == "selecao" else ""
                    novas_respostas.append({
                        "nome_ptd": str(nome_clean),
                        "campo_id": str(campo["id"]),
                        "valor": str(val_padrao),
                        "observacoes": ""
                    })
                df_respostas = pd.concat([df_respostas, pd.DataFrame(novas_respostas)], ignore_index=True)

                # Atualização do Google Sheets
                try:
                    conn.update(worksheet="Obras", data=df_obras.astype(str))
                    conn.update(worksheet="Respostas", data=df_respostas.astype(str))
                    st.cache_data.clear() # Limpa a cache para ler os dados atualizados
                    st.session_state.ptd_selecionado = nome_clean
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao gravar no Google Sheets: {e}")

    st.markdown("### 🏬 Histórico de Intervenções")
    if df_obras.empty or "nome_ptd" not in df_obras.columns:
        st.info("Nenhuma Obra registada. Clique no botão acima para adicionar.")
    else:
        for idx, row in df_obras.iterrows():
            ptd_key = str(row["nome_ptd"])
            dt_corte_val = str(row.get("data_corte", ""))
            dp_app_val = str(row.get("dp_aplicavel", ""))
            dp_info = str(row.get("data_descargas_parciais", "")) if dp_app_val == "Aplicável" else "Não Aplicável"

            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                col1.markdown(f"#### ⚡ Obra: {ptd_key}")
                col2.markdown(f"📅 **Corte:** {dt_corte_val}")
                col3.markdown(f"⚡ **Descargas Parciais:** {dp_info}")

                if col4.button("Abrir 📂", key=f"open_{ptd_key}", use_container_width=True):
                    st.session_state.ptd_selecionado = ptd_key
                    st.rerun()

                if st.sidebar.checkbox(f"Apagar {ptd_key}", key=f"del_chk_{ptd_key}"):
                    if st.sidebar.button(f"🗑️ Confirmar apagar {ptd_key}", key=f"del_btn_{ptd_key}"):
                        df_obras = df_obras[df_obras["nome_ptd"] != ptd_key]
                        df_respostas = df_respostas[df_respostas["nome_ptd"] != ptd_key]
                        try:
                            conn.update(worksheet="Obras", data=df_obras.astype(str))
                            conn.update(worksheet="Respostas", data=df_respostas.astype(str))
                            st.cache_data.clear() # Limpa a cache para atualizar a lista
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao apagar no Google Sheets: {e}")

# --- ECRÃ 2: FICHA DA OBRA ---
else:
    ptd_key = st.session_state.ptd_selecionado
    obra_row_idx = df_obras[df_obras["nome_ptd"] == ptd_key].index

    if len(obra_row_idx) > 0:
        idx_obra = obra_row_idx[0]
        meta = df_obras.loc[idx_obra]

        st.title(f"⚡ Obra: {meta['nome_ptd']}")
        st.markdown("---")

        with st.container(border=True):
            c_m1, c_m2, c_m3, c_m4 = st.columns([2, 2, 1.5, 2])
            c_m1.markdown(f"**Nome da Obra:** `{meta['nome_ptd']}`")

            try:
                dt_corte_val = datetime.strptime(str(meta["data_corte"]), "%Y-%m-%d").date()
            except Exception:
                dt_corte_val = datetime.now().date()
            nova_dt_corte = c_m2.date_input("Data do Corte", value=dt_corte_val, key="dt_corte_head")

            dp_aplicavel_atual = str(meta["dp_aplicavel"])
            novo_dp_app = c_m3.selectbox("Descargas Parciais", ["Aplicável", "Não Aplicável"], index=0 if dp_aplicavel_atual == "Aplicável" else 1, key="dp_app_head")

            try:
                dt_dp_val = datetime.strptime(str(meta["data_descargas_parciais"]), "%Y-%m-%d").date()
            except Exception:
                dt_dp_val = datetime.now().date()

            nova_dt_dp = c_m4.date_input(
                "Data das Descargas Parciais",
                value=dt_dp_val,
                disabled=(novo_dp_app == "Não Aplicável"),
                key="dt_dp_head"
            )

            if (str(nova_dt_corte) != str(meta["data_corte"]) or 
                novo_dp_app != dp_aplicavel_atual or 
                str(nova_dt_dp) != str(meta["data_descargas_parciais"])):

                df_obras.loc[idx_obra, "data_corte"] = str(nova_dt_corte)
                df_obras.loc[idx_obra, "dp_aplicavel"] = novo_dp_app
                df_obras.loc[idx_obra, "data_descargas_parciais"] = str(nova_dt_dp)
                try:
                    conn.update(worksheet="Obras", data=df_obras.astype(str))
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar no Google Sheets: {e}")

        st.markdown("### 📋 Checklist e Elementos de Processo")
        modificado = False

        for item in CAMPOS_CHECKLIST:
            i_id = item["id"]
            i_label = item["label"]
            i_tipo = item.get("tipo", "texto")
            i_ph = item.get("placeholder", "Notas suplementares...")

            resp_idx = df_respostas[(df_respostas["nome_ptd"] == ptd_key) & (df_respostas["campo_id"] == i_id)].index

            if len(resp_idx) > 0:
                r_idx = resp_idx[0]
                val_atual = str(df_respostas.loc[r_idx, "valor"]) if pd.notna(df_respostas.loc[r_idx, "valor"]) else ""
                obs_atual = str(df_respostas.loc[r_idx, "observacoes"]) if pd.notna(df_respostas.loc[r_idx, "observacoes"]) else ""

                with st.container(border=True):
                    col_lbl, col_val, col_obs = st.columns([2.5, 3, 3.5])
                    col_lbl.markdown(f"**{i_label}**")

                    if i_tipo == "selecao":
                        opcoes = item.get("opcoes", [])
                        idx_sel = opcoes.index(val_atual) if val_atual in opcoes else 0
                        novo_val = col_val.selectbox(f"Val_{i_id}", opcoes, index=idx_sel, label_visibility="collapsed")
                        nova_obs = col_obs.text_input(f"Obs_{i_id}", value=obs_atual, placeholder="Notas suplementares...", label_visibility="collapsed")
                    else:
                        novo_val = col_val.text_input(f"Val_{i_id}", value=val_atual, placeholder=i_ph, label_visibility="collapsed")
                        nova_obs = col_obs.text_input(f"Obs_{i_id}", value=obs_atual, placeholder="Notas suplementares...", label_visibility="collapsed")

                    if str(novo_val) != str(val_atual) or str(nova_obs) != str(obs_atual):
                        df_respostas["observacoes"] = df_respostas["observacoes"].astype(str)
                        df_respostas["valor"] = df_respostas["valor"].astype(str)

                        df_respostas.loc[r_idx, "valor"] = str(novo_val)
                        df_respostas.loc[r_idx, "observacoes"] = str(nova_obs)
                        modificado = True

        if modificado:
            try:
                conn.update(worksheet="Respostas", data=df_respostas.astype(str))
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao guardar respostas no Google Sheets: {e}")
