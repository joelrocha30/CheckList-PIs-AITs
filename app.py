import streamlit as st
import json
import os
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="CHECKLIST DE PIs / AITs - E-REDES",
    page_icon="⚡",
    layout="wide"
)

# Ficheiro local para armazenamento de dados
FICHEIRO_DADOS = "dados_pt.json"

# Configuração da Checklist Estrutura
CHECKLIST_ESTRUTURA = {
    "1. Construção Civil e Infraestrutura": [
        {"id": "01", "texto": "Acesso direto e desimpedido a partir da via pública."},
        {"id": "02", "texto": "Portas com abertura para o exterior desimpedidas com fechadura operacional (Canhão Chave2)."},
        {"id": "03", "texto": "Grelhas de ventilação limpas, com rede mosquiteira/antideflagrante e IP regulamentar."},
        {"id": "04", "texto": "Sinalização exterior de segurança (placas de aviso 'Alta Tensão' e Chapa do PT na Porta)"},
        {"id": "05", "texto": "Tubos de passagem de cabos (cuba/cave) devidamente selados contra água e roedores."},
        {"id": "06", "texto": "Plataforma de Manobras (AI/AS)"}
    ],
    "2. Rede de Terras": [
        {"id": "07", "texto": "Separação regulamentar das terras de Proteção e Terras de Serviço e identificação das mesmas"},
        {"id": "08", "texto": "Mapa de Terras e croqui Simples da resistências de terras (<20 Ohm)"},
        {"id": "09", "texto": "Todas as massas metálicas (portas, quadros, calhas, ferragens da Tubagem e Terras de Apoio/Poste) ligadas à terra com ligadores amovíveis."}
    ],
    "3. Equipamento de Média Tensão (MT)": [
        {"id": "10", "texto": "Terminações/terminais de cabos de MT limpos, alinhados e sem vincos estruturais."},
        {"id": "11", "texto": "Encravamentos mecânicos das chaves de terra testados e 100% operacionais."},
        {"id": "12", "texto": "Instalação de BRA com a Identificação correcta (Nº da Cela + Nº Orgão)"},
        {"id": "13", "texto": "Instalação da alavanca para o Secc/IntSecc (AS/AI)"}
    ],
    "4. Transformador de Potência": [
        {"id": "14", "texto": "Placa de características (kVA, tensões nominal/secundária, grupo) coincide com projeto aprovado."},
        {"id": "15", "texto": "Aperto mecânico dos bornes (MT e BT) verificado criteriosamente com chave dinamométrica."},
        {"id": "16", "texto": "Comutador de tomadas em vazio posicionado na tomada correta para o arranque de exploração."},
        {"id": "17", "texto": "Acessórios instalados corretamente (termómetro, amortecedores de vibração, relé Buchholz)."}
    ],
    "5. Quadro Geral de Baixa Tensão (QGBT)": [
        {"id": "18", "texto": "Barramentos de cobre perfeitamente alinhados e com aperto verificado."},
        {"id": "19", "texto": "Fusíveis de proteção instalados com o tamanho e calibre adequados à potência do transformador."},
        {"id": "20", "texto": "Circuitos de serviços auxiliares (iluminação interna, tomadas, comando) operacionais."},
        {"id": "21", "texto": "DTC, Totalizador, Quadros de Comando, Contagem, Controlo e Comunicações (P4C ou Q4C)"}
    ],
    "6. Documentação e Equipamentos de Segurança": [
        {"id": "22", "texto": "Kit de segurança regulamentar completo em obra (tapete isolante, alavanca de manobra pregada na parede, lanterna, aloquetes, Luvas)."},
        {"id": "24", "texto": "Cartaz de primeiros socorros em caso de acidente elétrico."},
        {"id": "25", "texto": "Pavimento envolvente do PTD e/ou Muros."},
        {"id": "26", "texto": "Relatórios de ensaios aos cabos e certificados de conformidade"}
    ]
}

# Funções auxiliares para guardar/carregar dados
def carregar_dados():
    if os.path.exists(FICHEIRO_DADOS):
        try:
            with open(FICHEIRO_DADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                for obra in dados.get("obras", []):
                    if "arquivada" not in obra:
                        obra["arquivada"] = False
                return dados
        except Exception:
            return {"obras": [], "respostas": []}
    return {"obras": [], "respostas": []}

def guardar_dados(dados):
    with open(FICHEIRO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

# Função para Gerar Relatório Resumido para E-mail
def gerar_relatorio_email(ref_obra, dados_base):
    obra_info = next((o for o in dados_base["obras"] if o["obra_ref"] == ref_obra), {})
    resp_pt = [r for r in dados_base["respostas"] if r["obra_ref"] == ref_obra]
    
    conf = sum(1 for r in resp_pt if r["estado"] == "Conforme")
    n_conf = sum(1 for r in resp_pt if r["estado"] == "Não Conforme")
    na_it = sum(1 for r in resp_pt if r["estado"] == "N/A")
    pend = sum(1 for r in resp_pt if r["estado"] == "Pendente")
    prog = int(((conf + n_conf + na_it) / 26) * 100) if resp_pt else 0

    data_vist = obra_info.get('data_vistoria', datetime.now().strftime('%Y-%m-%d'))

    relatorio = f"""Assunto: [Fiscalização PT] Relatório de Inconformidades - {ref_obra}

Viva,

Segue o resumo da fiscalização efetuada à instalação {ref_obra} no dia {data_vist}.

--- RESUMO DA VISTORIA ---
• Instalação / PT: {ref_obra}
• Progresso da Fiscalização: {prog}%
• Conformes: {conf} | Não Conformes: {n_conf} | N/A: {na_it} | Pendentes: {pend}
"""

    inconformidades = []
    for categoria, itens in CHECKLIST_ESTRUTURA.items():
        for item in itens:
            i_id = str(item["id"])
            dados_linha = next((r for r in resp_pt if r["item_id"] == i_id and r["estado"] == "Não Conforme"), None)
            if dados_linha:
                obs = dados_linha.get("observacoes", "").strip()
                inconformidades.append({
                    "id": i_id,
                    "texto": item["texto"],
                    "obs": obs if obs else "Sem observações adicionais."
                })

    if inconformidades:
        relatorio += f"\n--- ❌ PONTOS NÃO CONFORMES DETETADOS ({len(inconformidades)}) ---\n"
        for idx, inc in enumerate(inconformidades, 1):
            relatorio += f"\n{idx}. [Item {inc['id']}] {inc['texto']}\n   👉 Anomalia/Nota: {inc['obs']}\n"
        relatorio += "\nSolicita-se a resolução/correção das anomalias acima identificadas."
    else:
        relatorio += "\n--- ✅ SITUAÇÃO DE CONFORMIDADE ---\nNão foram detetadas inconformidades até ao momento."

    relatorio += f"""

Com os melhores cumprimentos,
Joel Machado Rocha
Fiscalização de Obras / E-REDES
"""
    return relatorio

# Inicializar Estado da Sessão
if "base_dados" not in st.session_state:
    st.session_state.base_dados = carregar_dados()

if "obra_selecionada" not in st.session_state:
    st.session_state.obra_selecionada = None

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.title("⚡ Gestão de Obras")
st.sidebar.caption("Fiscal: Joel Machado Rocha")
st.sidebar.markdown("---")

if st.session_state.obra_selecionada:
    if st.sidebar.button("⬅️ Voltar ao Dashboard", use_container_width=True):
        st.session_state.obra_selecionada = None
        st.rerun()

# EXPANDER DE OBRAS ARQUIVADAS NA SIDEBAR
with st.sidebar.expander("📦 Obras em Arquivo", expanded=False):
    obras_arquivadas = [o for o in st.session_state.base_dados["obras"] if o.get("arquivada", False)]
    
    if not obras_arquivadas:
        st.caption("Nenhuma obra no arquivo.")
    else:
        for obra in obras_arquivadas:
            ref_arq = obra["obra_ref"]
            c_txt, c_btn = st.columns([1.8, 1.2])
            c_txt.caption(f"📁 {ref_arq}")
            
            if c_btn.button("Desarquivar", key=f"desarq_side_{ref_arq}", use_container_width=True):
                obra["arquivada"] = False
                guardar_dados(st.session_state.base_dados)
                st.rerun()

# --- ECRÃ 1: DASHBOARD DE OBRAS ---
if st.session_state.obra_selecionada is None:
    st.title("📁 CHECKLIST DE PIs / AITs - Registos")
    st.subheader("Selecione uma Obra ou Crie uma nova")
    st.markdown("---")
    
    # Registar Nova Obra
    with st.expander("➕ REGISTAR NOVA OBRA", expanded=False):
        col_n1, col_n2 = st.columns([3, 1])
        nova_ref = col_n1.text_input("Referência / Designação da Obra", placeholder="Ex: PTD 0158 PFR - TP1")
        nova_data = col_n2.date_input("Data de Vistoria / Corte", value=datetime.now().date())
        
        if st.button("Registar Nova Obra", type="primary"):
            nova_ref_clean = nova_ref.strip()
            obras_existentes = [o["obra_ref"] for o in st.session_state.base_dados["obras"]]
            
            if nova_ref_clean == "":
                st.error("Insira uma referência válida.")
            elif nova_ref_clean in obras_existentes:
                st.error("Esta obra já se encontra registada.")
            else:
                st.session_state.base_dados["obras"].append({
                    "obra_ref": nova_ref_clean,
                    "data_vistoria": str(nova_data),
                    "arquivada": False
                })
                
                for cat, itens in CHECKLIST_ESTRUTURA.items():
                    for item in itens:
                        st.session_state.base_dados["respostas"].append({
                            "obra_ref": nova_ref_clean,
                            "item_id": str(item["id"]),
                            "estado": "Pendente",
                            "data_verificacao": str(nova_data),
                            "observacoes": ""
                        })
                
                guardar_dados(st.session_state.base_dados)
                st.success("Obra adicionada com sucesso!")
                st.rerun()

    # Histórico de Intervenções Ativas
    st.markdown("### 🏬 Histórico de Intervenções Ativas")
    obras_ativas = [o for o in st.session_state.base_dados["obras"] if not o.get("arquivada", False)]
    
    if not obras_ativas:
        st.info("Nenhuma obra ativa no momento.")
    else:
        for row in obras_ativas:
            ref = row["obra_ref"]
            dt = row["data_vistoria"]
            
            resp_pt = [r for r in st.session_state.base_dados["respostas"] if r["obra_ref"] == ref]
            conf = sum(1 for r in resp_pt if r["estado"] == "Conforme")
            n_conf = sum(1 for r in resp_pt if r["estado"] == "Não Conforme")
            na_it = sum(1 for r in resp_pt if r["estado"] == "N/A")
            
            prog = int(((conf + n_conf + na_it) / 26) * 100) if resp_pt else 0
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3.5, 2, 2.5, 1, 1])
                c1.markdown(f"#### ⚡ {ref}")
                c2.markdown(f"📅 **Corte:** {dt}")
                
                if n_conf > 0:
                    c3.markdown(f"🔴 **{n_conf} Inconformidades** ({prog}%)")
                else:
                    c3.markdown(f"🟢 **APROVADO / CONCLUÍDO** ({prog}%)")
                    
                if c4.button("Abrir 📂", key=f"btn_open_{ref}", use_container_width=True):
                    st.session_state.obra_selecionada = ref
                    st.rerun()
                    
                if c5.button("Arquivar 📦", key=f"btn_arq_{ref}", use_container_width=True):
                    row["arquivada"] = True
                    guardar_dados(st.session_state.base_dados)
                    st.rerun()

# --- ECRÃ 2: ENTRADA DE DADOS DA CHECKLIST ---
else:
    ref_atual = st.session_state.obra_selecionada
    st.title(f"⚡ Inspecionando: {ref_atual}")
    st.markdown("---")
    
    resp_pt = [r for r in st.session_state.base_dados["respostas"] if r["obra_ref"] == ref_atual]
    
    conf = sum(1 for r in resp_pt if r["estado"] == "Conforme")
    n_conf = sum(1 for r in resp_pt if r["estado"] == "Não Conforme")
    na_it = sum(1 for r in resp_pt if r["estado"] == "N/A")
    prog = int(((conf + n_conf + na_it) / 26) * 100) if resp_pt else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Progresso da Vistoria", f"{prog}%")
    m2.metric("Itens Conformes ✅", conf)
    m3.metric("Inconformidades Detetadas ❌", n_conf)
    st.progress(prog / 100)
    st.markdown(" ")

    # Módulo de E-mail Resumido
    with st.expander("✉️ GERAR RESUMO PARA E-MAIL (INCONFORMIDADES)", expanded=False):
        txt_email = gerar_relatorio_email(ref_atual, st.session_state.base_dados)
        st.code(txt_email, language="text")
        
        st.download_button(
            label="📥 Descarregar Texto para E-mail (.txt)",
            data=txt_email,
            file_name=f"Email_Inconformidades_{ref_atual.replace(' ', '_')}.txt",
            mime="text/plain"
        )

    modificado = False

    for categoria, itens in CHECKLIST_ESTRUTURA.items():
        with st.expander(f"📂 {categoria.upper()}", expanded=True):
            col_id, col_txt, col_est, col_dt, col_obs = st.columns([0.6, 5, 2, 1.8, 4])
            col_id.markdown("**ID**")
            col_txt.markdown("**Item de Verificação**")
            col_est.markdown("**Estado**")
            col_dt.markdown("**Data Verif.**")
            col_obs.markdown("**Observações / Anomalias**")
            st.divider()

            for item in itens:
                i_id = str(item["id"])
                dados_linha = next((r for r in st.session_state.base_dados["respostas"] if r["obra_ref"] == ref_atual and r["item_id"] == i_id), None)
                
                if dados_linha:
                    c_id, c_txt, c_est, c_dt, c_obs = st.columns([0.6, 5, 2, 1.8, 4])
                    
                    c_id.info(f"**{i_id}**")
                    c_txt.markdown(f"<div style='padding-top: 5px;'>{item['texto']}</div>", unsafe_allow_html=True)
                    
                    opcoes = ["Pendente", "Conforme", "Não Conforme", "N/A"]
                    est_atual = dados_linha["estado"] if dados_linha["estado"] in opcoes else "Pendente"
                    v_est = c_est.selectbox(f"Est_{i_id}", opcoes, index=opcoes.index(est_atual), label_visibility="collapsed")
                    
                    try:
                        v_dt_padrao = datetime.strptime(str(dados_linha["data_verificacao"]), "%Y-%m-%d").date()
                    except Exception:
                        v_dt_padrao = datetime.now().date()
                    v_dt = c_dt.date_input(f"Dt_{i_id}", value=v_dt_padrao, label_visibility="collapsed")
                    
                    v_obs = c_obs.text_input(f"Obs_{i_id}", value=str(dados_linha["observacoes"]), placeholder="Notas...", label_visibility="collapsed")
                    
                    if v_est != dados_linha["estado"] or str(v_dt) != str(dados_linha["data_verificacao"]) or v_obs != dados_linha["observacoes"]:
                        dados_linha["estado"] = v_est
                        dados_linha["data_verificacao"] = str(v_dt)
                        dados_linha["observacoes"] = v_obs
                        modificado = True

    if modificado:
        guardar_dados(st.session_state.base_dados)
        st.rerun()
