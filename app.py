import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import io
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arthur Pinheiro | Gestão de Dados", layout="wide")

def aplicar_estilo():
    st.markdown("""
        <style>
        .stApp { background-color: #f4f7f9; }
        [data-testid="stSidebar"] { background-color: #001f3f !important; }
        .card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 6px solid #001f3f; margin-bottom: 20px; }
        .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .watermark { position: fixed; bottom: 10px; right: 15px; opacity: 0.4; font-weight: bold; color: #001f3f; font-size: 13px; }
        </style>
        <div class="watermark">Desenvolvido por: Arthur Pinheiro</div>
    """, unsafe_allow_html=True)

aplicar_estilo()

# --- BANCO DE DADOS ---
conn = sqlite3.connect('banco_central_v4.db', check_same_thread=False)
c = conn.cursor()

def criar_tabelas():
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS biblioteca (id INTEGER PRIMARY KEY, client_id INTEGER, name TEXT, content TEXT, type TEXT, date TEXT)')
    c.execute("INSERT OR IGNORE INTO users (id, email, password, role, status) VALUES (1, 'admin@master.com', '1234', 'admin', 'active')")
    conn.commit()

criar_tabelas()

# --- SESSÃO ---
if 'usuario' not in st.session_state:
    st.session_state.usuario = None

# --- TELA DE LOGIN ---
if st.session_state.usuario is None:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.title("🛡️ Sistema Arthur Pinheiro")
        aba_log, aba_reg = st.tabs(["Login", "Novo Cadastro"])
        with aba_log:
            e = st.text_input("E-mail")
            p = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                c.execute("SELECT * FROM users WHERE email=? AND password=? AND status='active'", (e, p))
                res = c.fetchone()
                if res:
                    st.session_state.usuario = res
                    st.rerun()
                else: st.error("Acesso negado ou pendente.")
        with aba_reg:
            ne = st.text_input("Novo E-mail")
            np = st.text_input("Defina Senha")
            nr = st.selectbox("Perfil", ["Cliente", "Admin"])
            if st.button("Solicitar Acesso"):
                try:
                    c.execute("INSERT INTO users (email, password, role, status) VALUES (?,?,?,?)", (ne, np, nr, 'pending'))
                    conn.commit()
                    st.success("Solicitação enviada!")
                except: st.error("E-mail já cadastrado.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- SISTEMA LOGADO ---
else:
    u_id, u_email, _, u_role, _ = st.session_state.usuario
    st.sidebar.title("Navegação")
    st.sidebar.write(f"Usuário: **{u_email}**")
    if st.sidebar.button("Sair"):
        st.session_state.usuario = None
        st.rerun()

    if u_role == 'admin':
        menu = st.sidebar.radio("Ir para:", ["📊 Visão Geral", "📥 Biblioteca (Upload)", "🔗 Vincular a Clientes", "👥 Gerenciar Usuários"])

        # --- VISÃO GERAL ---
        if menu == "📊 Visão Geral":
            st.header("📊 Painel de Controle")
            
            # KPIs
            total_planilhas = pd.read_sql("SELECT * FROM biblioteca", conn)
            total_users = pd.read_sql("SELECT * FROM users WHERE role='Cliente'", conn)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total de Planilhas", len(total_planilhas))
            c2.metric("Clientes Ativos", len(total_users[total_users['status']=='active']))
            c3.metric("Planilhas na Biblioteca", len(total_planilhas[total_planilhas['client_id']==0]))

            st.divider()
            st.subheader("📋 Status de Todas as Planilhas")
            if not total_planilhas.empty:
                # Criar uma visualização bonita de quem é dono de que
                status_df = total_planilhas.copy()
                status_df['Status'] = status_df['client_id'].apply(lambda x: 'Disponível na Biblioteca' if x == 0 else f'Vinculada ao Cliente ID {x}')
                st.dataframe(status_df[['id', 'name', 'type', 'date', 'Status']], use_container_width=True)
            else:
                st.info("Nenhuma planilha encontrada no banco de dados.")

        # --- BIBLIOTECA (UPLOAD) ---
        elif menu == "📥 Biblioteca (Upload)":
            st.header("📥 Adicionar Planilha à Biblioteca")
            
            with st.expander("➕ Clique aqui para fazer novo Upload", expanded=True):
                nome_doc = st.text_input("Nome do Relatório")
                metodo = st.radio("Formato", ["Excel/CSV", "Link Google Sheets"])
                
                if metodo == "Excel/CSV":
                    arq = st.file_uploader("Escolha o arquivo", type=['xlsx', 'csv'])
                    if arq and nome_doc and st.button("Salvar na Biblioteca"):
                        df_up = pd.read_csv(arq) if arq.name.endswith('csv') else pd.read_excel(arq)
                        c.execute("INSERT INTO biblioteca (client_id, name, content, type, date) VALUES (0, ?, ?, 'file', ?)",
                                  (nome_doc, df_up.to_json(), datetime.now().strftime("%d/%m/%Y")))
                        conn.commit()
                        st.success(f"'{nome_doc}' salvo com sucesso!")
                else:
                    link_g = st.text_input("Link CSV do Google")
                    if link_g and nome_doc and st.button("Vincular Link"):
                        c.execute("INSERT INTO biblioteca (client_id, name, content, type, date) VALUES (0, ?, ?, 'link', ?)",
                                  (nome_doc, link_g, datetime.now().strftime("%d/%m/%Y")))
                        conn.commit()
                        st.success("Link salvo!")

            st.divider()
            st.subheader("📦 Itens Atuais na Biblioteca (Sem Dono)")
            livres = pd.read_sql("SELECT id, name, type, date FROM biblioteca WHERE client_id=0", conn)
            if livres.empty:
                st.info("A biblioteca está vazia.")
            else:
                st.table(livres)
                if st.button("Limpar Biblioteca (Apagar itens sem dono)"):
                    c.execute("DELETE FROM biblioteca WHERE client_id=0")
                    conn.commit()
                    st.rerun()

        # --- VINCULAR ---
        elif menu == "🔗 Vincular a Clientes":
            st.header("🔗 Entregar Relatório para Cliente")
            livres = pd.read_sql("SELECT id, name FROM biblioteca WHERE client_id=0", conn)
            clientes = pd.read_sql("SELECT id, email FROM users WHERE role='Cliente' AND status='active'", conn)
            
            if livres.empty:
                st.warning("Não há planilhas na biblioteca para vincular.")
            elif clientes.empty:
                st.warning("Não há clientes ativos para receber dados.")
            else:
                p_escolha = st.selectbox("Selecione a Planilha", livres['name'].tolist())
                c_escolha = st.selectbox("Selecione o Cliente", clientes['email'].tolist())
                
                p_id = livres[livres['name'] == p_escolha]['id'].values[0]
                c_id = clientes[clientes['email'] == c_escolha]['id'].values[0]
                
                if st.button("Confirmar Vinculação"):
                    c.execute("UPDATE biblioteca SET client_id=? WHERE id=?", (int(c_id), int(p_id)))
                    conn.commit()
                    st.success(f"Pronto! '{p_escolha}' agora pertence a {c_escolha}")
                    st.rerun()

        elif menu == "👥 Gerenciar Usuários":
            st.header("👥 Aprovação de Cadastros")
            usuarios = pd.read_sql("SELECT id, email, role, status FROM users", conn)
            st.dataframe(usuarios, use_container_width=True)
            uid = st.number_input("ID do Usuário", step=1)
            if st.button("Aprovar/Ativar"):
                c.execute("UPDATE users SET status='active' WHERE id=?", (uid,))
                conn.commit()
                st.rerun()

    # --- VISÃO CLIENTE ---
    else:
        st.header(f"📊 Seus Relatórios")
        meus_dados = pd.read_sql(f"SELECT * FROM biblioteca WHERE client_id={u_id}", conn)
        
        if meus_dados.empty:
            st.info("Aguarde. Arthur Pinheiro está processando seus dados.")
        else:
            escolha = st.selectbox("Escolha o Relatório", meus_dados['name'].tolist())
            linha = meus_dados[meus_dados['name'] == escolha].iloc[0]
            
            try:
                if linha['type'] == 'file': df = pd.read_json(io.StringIO(linha['content']))
                else: df = pd.read_csv(linha['content'])
                
                st.markdown(f'<div class="card"><h3>{escolha}</h3><p>Data: {linha["date"]}</p></div>', unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.metric("Total de Linhas", len(df))
                    st.dataframe(df, height=300)
                with c2:
                    nums = df.select_dtypes(include='number').columns
                    if not nums.empty:
                        fig = px.bar(df.head(20), y=nums[0], title=f"Análise de {nums[0]}", color_discrete_sequence=['#001f3f'])
                        st.plotly_chart(fig, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Planilha", csv, f"{escolha}.csv")
            except:
                st.error("Erro ao ler os dados. Verifique o formato do arquivo ou o link.")