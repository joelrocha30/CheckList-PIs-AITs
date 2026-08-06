import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

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

# Função com CACHE para evitar erro de limites (429)
@st.cache_data(ttl=300)
def carregar_dados():
    try:
        df_o = conn.read(worksheet="Obras")
    except Exception:
        df_o = pd.DataFrame(columns=["nome_ptd", "data_corte", "dp_aplicavel", "data_descargas_parciais", "arquivado"])

    try:
        df_r = conn.read(worksheet="Respostas")
    except Exception:
        df_r = pd.DataFrame(columns=["nome_ptd", "campo_id", "valor", "observacoes"])

    # Garantir colunas necessárias e conversão para string
    if not df_o.empty:
        if "arquivado" not in df_o.columns:
            df_o["arquivado"] = "Não"
        for col in df_o.columns:
            df_o[col] = df_o[col].fillna("").astype(str)
    else:
        df_o = pd.DataFrame(columns=["nome_ptd", "data_corte", "dp_aplicavel", "data_descargas_parciais", "arquivado"])

    if not df_r.empty:
        for col in df_r.columns:
            df_r[col] = df_r[col].fillna("").astype(str)
    else:
        df_r = pd.DataFrame(columns=["nome_ptd", "campo_id", "valor", "observacoes"])

    return df_o, df_r

df_obras, df_respostas = carregar_dados()

# Estado de Navegação
if "ptd_selecionado" not in st.session_state:
    st.session_state.ptd_selecionado = None

# Função para extrair a primeira data (usada para ordenação)
def extrair_primeira_data(data_str):
    try:
        primeira = str(data_str).split(",")[0].split(" à ")[0].strip()
        return datetime.strptime(primeira, "%Y-%m-%d").date()
    except Exception:
        return date.max

# Função para extrair a última data (usada para verificação de arquivo automático)
def extrair_ultima_data(data_str):
    try:
        partes = str(data_str).replace(" à ", ",").split(",")
        ultima = partes[-1].strip()
        return datetime.strptime(ultima, "%Y-%m-%d").date()
    except Exception:
        return date.min

# Verificar se a obra tem PI e PIT Aprovados
def verificar_status_aprovado(ptd_nome, df_resp):
    pi_status = df_resp[(df_resp["nome_ptd"] == ptd_nome) & (df_resp["campo_id"] == "pi")]
    pit_status = df_resp[(df_resp["nome_ptd"] == ptd_nome) & (df_resp["campo_id"] == "pit")]
    
    pi_ok = not pi_status.empty and pi_status.iloc[0]["valor"] == "Feito e Aprovado"
    pit_ok = not pit_status.empty and pit_status.iloc[0]["valor"] == "Feito e Aprovado"
    
    return pi_ok and pit_ok

# --- BARRA LATERAL ---
st.sidebar.title("⚡ Gestão de Obras")
st.sidebar.markdown("**Fiscal:** Joel Machado Rocha")

if st.session_state.ptd_selecionado:
    if st.sidebar.button("⬅️ Voltar ao Histórico", use_container_width=True):
        st.session_state.ptd_selecionado = None
        st.rerun()

st.sidebar.markdown("---")

# Painel 1 da Sidebar: Apagar Obras
with st.sidebar.expander("🗑️ Gestão de Remoção"):
    if df_obras.empty:
        st.caption("Sem obras registadas.")
    else:
        for ptd_key in df_obras["nome_ptd"].tolist():
            if st.checkbox(f"Apagar {ptd_key}", key=f"del_chk_{ptd_key}"):
                if st.button(f"🗑️ Confirmar apagar {ptd_key}", key=f"del_btn_{ptd_key}"):
                    df_obras = df_obras[df_obras["nome_ptd"] != ptd_key]
                    df_respostas = df_respostas[df_respostas["nome_ptd"] != ptd_key]
                    try:
                        conn.update(worksheet="Obras", data=df_obras.astype(str))
                        conn.update(worksheet="Respostas", data=df_respostas.astype(str))
                        st.cache_data.clear()
                        st.session_state.ptd_selecionado = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao apagar: {e}")

# Painel 2 da Sidebar: Arquivo de Obras
with st.sidebar.expander("📦 Obras em Arquivo"):
    obras_arquivadas = []
    hoje = datetime.now().date()
    
    for idx, r in df_obras.iterrows():
        dt_fim = extrair_ultima_data(r["data_corte"])
        if r.get("arquivado") == "Sim" or (dt_fim != date.min and dt_fim < hoje):
            obras_arquivadas.append(r["nome_ptd"])

    if not obras_arquivadas:
        st.caption("Nenhuma obra em arquivo.")
    else:
        for arq_ptd in obras_arquivadas:
            c_a1, c_a2 = st.columns([2, 1])
            c_a1.caption(f"📁 {arq_ptd}")
            if c_a2.button("Desarquivar", key=f"unarch_{arq_ptd}"):
                idx_found = df_obras[df_obras["nome_ptd"] == arq_ptd].index
                if len(idx_found) > 0:
                    df_obras.loc[idx_found[0], "arquivado"] = "Não"
                    conn.update(worksheet="Obras", data=df_obras.astype(str))
                    st.cache_data.clear()
                    st.rerun()

# --- ECRÃ 1: HISTÓRICO DE OBRAS ---
if st.session_state.ptd_selecionado is None:
    st.title("📂 CHECKLIST DE PIs / AITs - Registos")
    st.subheader("Selecione uma Obra ou Crie uma nova")
    st.markdown("---")

    # Registar Nova Obra
    with st.expander("➕ REGISTAR NOVA OBRA", expanded=False):
        c1, c2, c3, c4 = st.columns([2, 1.5, 1, 1])
        nome_ptd = c1.text_input("Nome da Obra", placeholder="Ex: PTD FLG 0266")
        
        # CORREÇÃO AQUI: date_input configurado para aceitar 1 dia ou intervalo de datas
        dt_corte_input = c2.date_input("Data(s) do Corte", value=[datetime.now().date()])
        
        dp_app = c3.selectbox("Descargas Parciais?", ["Aplicável", "Não Aplicável"])
        dt_dp = c4.date_input("Data Descargas Parciais", value=datetime.now().date(), disabled=(dp_app == "Não Aplicável"))

        if st.button("Criar Registo", type="primary"):
            nome_clean = nome_ptd.strip()
            if not nome_clean:
                st.error("Escreva o Nome da Obra e/ou PTD/PS.")
            elif not df_obras.empty and "nome_ptd" in df_obras.columns and nome_clean in df_obras["nome_ptd"].values:
                st.error("Já existe um registo com esta Obra!")
            else:
                # Tratar se o utilizador selecionou 1 dia ou um intervalo
                if isinstance(dt_corte_input, (list, tuple)):
                    dt_corte_str = " à ".join([str(d) for d in dt_corte_input])
                else:
                    dt_corte_str = str(dt_corte_input)

                nova_obra = pd.DataFrame([{
                    "nome_ptd": str(nome_clean),
                    "data_corte": dt_corte_str,
                    "dp_aplicavel": str(dp_app),
                    "data_descargas_parciais": str(dt_dp),
                    "arquivado": "Não"
                }])
                df_obras = pd.concat([df_obras, nova_obra], ignore_ignore_index=True) if hasattr(pd, "concat") else df_obras.append(nova_obra)
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

                try:
                    conn.update(worksheet="Obras", data=df_obras.astype(str))
                    conn.update(worksheet="Respostas", data=df_respostas.astype(str))
                    st.cache_data.clear()
                    st.session_state.ptd_selecionado = nome_clean
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao gravar no Google Sheets: {e}")

    st.markdown("### 🏬 Histórico de Intervenções Ativas")

    if df_obras.empty or "nome_ptd" not in df_obras.columns:
        st.info("Nenhuma Obra registada. Clique no botão acima para adicionar.")
    else:
        df_obras["temp_sort_date"] = df_obras["data_corte"].apply(extrair_primeira_data)
        df_obras_ordenadas = df_obras.sort_values(by="temp_sort_date", ascending=True)

        hoje = datetime.now().date()
        obras_visiveis = 0

        for idx, row in df_obras_ordenadas.iterrows():
            ptd_key = str(row["nome_ptd"])
            dt_corte_val = str(row.get("data_corte", ""))
            dp_app_val = str(row.get("dp_aplicavel", ""))
            dp_info = str(row.get("data_descargas_parciais", "")) if dp_app_val == "Aplicável" else "Não Aplicável"
            is_arquivado = str(row.get("arquivado", "Não")) == "Sim"

            dt_fim = extrair_ultima_data(dt_corte_val)
            passou_data = (dt_fim != date.min and dt_fim < hoje)

            if is_arquivado or passou_data:
                continue

            obras_visiveis += 1

            aprovado = verificar_status_aprovado(ptd_key, df_respostas)
            cor_destaque = "#28a745" if aprovado else "#dc3545"
            icone_status = "🟢 APROVADO (PI + PIT)" if aprovado else "🔴 PENDENTE / EM CURSO"

            with st.container(border=True):
                col_status, col1, col2, col3, col4, col5 = st.columns([0.3, 3, 2, 2, 1, 1])
                
                col_status.markdown(f"<div style='background-color: {cor_destaque}; height: 45px; width: 8px; border-radius: 4px;'></div>", unsafe_allow_html=True)
                
                col1.markdown(f"#### ⚡ {ptd_key}\n<small>{icone_status}</small>", unsafe_allow_html=True)
                col2.markdown(f"📅 **Corte:** {dt_corte_val}")
                col3.markdown(f"⚡ **Descargas Parciais:** {dp_info}")

                if col4.button("Abrir 📂", key=f"open_{ptd_key}", use_container_width=True):
                    st.session_state.ptd_selecionado = ptd_key
                    st.rerun()

                if col5.button("📦 Arquivar", key=f"arch_btn_{ptd_key}", use_container_width=True):
                    df_obras.loc[idx, "arquivado"] = "Sim"
                    if "temp_sort_date" in df_obras.columns:
                        df_obras = df_obras.drop(columns=["temp_sort_date"])
                    try:
                        conn.update(worksheet="Obras", data=df_obras.astype(str))
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao arquivar: {e}")

        if obras_visiveis == 0:
            st.info("Não existem obras ativas de momento. Todas as obras estão em arquivo ou foram concluídas.")

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

            dt_corte_val_str = str(meta["data_corte"])
            c_m2.markdown(f"**Data(s) do Corte:** `{dt_corte_val_str}`")

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

            if (novo_dp_app != dp_aplicavel_atual or str(nova_dt_dp) != str(meta["data_descargas_parciais"])):
                df_obras.loc[idx_obra, "dp_aplicavel"] = novo_dp_app
                df_obras.loc[idx_obra, "data_descargas_parciais"] = str(nova_dt_dp)
                if "temp_sort_date" in df_obras.columns:
                    df_obras = df_obras.drop(columns=["temp_sort_date"])
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
