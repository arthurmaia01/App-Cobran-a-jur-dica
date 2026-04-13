import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import io
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Gestão Arthur Pinheiro", layout="wide")

def style():
    st.markdown("""
        <style>
        .stApp { background-color: #f4f7f9; }
        [data-testid="stSidebar"] { background-color: #001f3f !important; }
        .main-card { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; border-left: 5px solid #001f3f; }
        .watermark { position: fixed; bottom: 10px; right: 15px; opacity: 0.4; color: #001f3f; font-weight: bold; font-size: 12px; }
        </style>
        <div class="watermark">Arthur Pinheiro - Business Intelligence</div>
    """, unsafe_allow_html=True)

style()

# --- BANCO DE DADOS ---
conn = sqlite3.connect('banco_central.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT, password TEXT, role TEXT, status TEXT)')
    # client_id = 0 significa que a planilha está na biblioteca global (sem dono)
    c.execute('CREATE TABLE IF NOT EXISTS data_files (id INTEGER PRIMARY KEY, client_id INTEGER, name TEXT, content TEXT, type TEXT, date TEXT)')
    c.execute("INSERT OR IGNORE INTO users VALUES (1, 'admin@master.com', '1234', 'admin', 'active')")
    conn.commit()

init_db()

# --- LOGIN ---
if 'logged_user' not in st.session_state:
    st.session_state.logged_user = None

if st.session_state.logged_user is None:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.title("🛡️ Portal de Relatórios")
        t_log, t_reg = st.tabs(["Entrar", "Novo Cadastro"])
        with t_log:
            e = st.text_input("E-mail")
            p = st.text_input("Senha", type="password")
            if st.button("Acessar Sistema"):
                c.execute("SELECT * FROM users WHERE email=? AND password=? AND status='active'", (e, p))
                res = c.fetchone()
                if res:
                    st.session_state.logged_user = res
                    st.rerun()
                else: st.error("Acesso não autorizado.")
        with t_reg:
            ne = st.text_input("E-mail de Cadastro")
            np = st.text_input("Senha de Cadastro")
            nr = st.selectbox("Perfil", ["Cliente", "Admin"])
            if st.button("Solicitar Acesso"):
                c.execute("INSERT INTO users (email, password, role, status) VALUES (?,?,?,?)", (ne, np, nr, 'pending'))
                conn.commit()
                st.success("Solicitação enviada!")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    u_id, u_email, _, u_role, _ = st.session_state.logged_user
    st.sidebar.markdown(f"<h3 style='color:white;'>Olá, {u_email.split('@')[0]}</h3>", unsafe_allow_html=True)
    
    if st.sidebar.button("Sair"):
        st.session_state.logged_user = None
        st.rerun()

    # --- DASHBOARD ADMIN ---
    if u_role == 'admin':
        menu = st.sidebar.radio("Navegação", ["Dashboard", "Biblioteca de Planilhas", "Vincular a Clientes", "Gestão de Usuários"])

        if menu == "Dashboard":
            st.header("📈 Visão Geral Administrativa")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Usuários", len(pd.read_sql("SELECT * FROM users", conn)))
            c2.metric("Planilhas no Sistema", len(pd.read_sql("SELECT * FROM data_files", conn)))
            c3.metric("Planilhas Sem Dono", len(pd.read_sql("SELECT * FROM data_files WHERE client_id=0", conn)))

        elif menu == "Biblioteca de Planilhas":
            st.header("📂 Central de Upload (Independente)")
            st.markdown("Aqui você anexa as planilhas ao sistema, mesmo que o cliente ainda não exista.")
            
            tipo = st.radio("Fonte", ["Arquivo Excel/CSV", "Link Google Sheets"])
            nome_rel = st.text_input("Nome do Relatório (Ex: Faturamento Mensal)")
            
            if tipo == "Arquivo Excel/CSV":
                f = st.file_uploader("Arraste o arquivo", type=['xlsx', 'csv'])
                if f and nome_rel and st.button("Salvar na Biblioteca"):
                    df = pd.read_csv(f) if f.name.endswith('csv') else pd.read_excel(f)
                    c.execute("INSERT INTO data_files (client_id, name, content, type, date) VALUES (0, ?, ?, 'file', ?)",
                              (nome_rel, df.to_json(), datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    st.success(f"'{nome_rel}' salvo na biblioteca global!")
            else:
                link = st.text_input("Link de Exportação CSV do Google")
                if link and nome_rel and st.button("Vincular Link à Biblioteca"):
                    c.execute("INSERT INTO data_files (client_id, name, content, type, date) VALUES (0, ?, ?, 'link', ?)",
                              (nome_rel, link, datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    st.success("Link guardado no sistema!")

        elif menu == "Vincular a Clientes":
            st.header("🔗 Direcionar Relatórios")
            
            # 1. Escolher Planilha da Biblioteca
            planilhas_livres = pd.read_sql("SELECT id, name FROM data_files WHERE client_id=0", conn)
            if planilhas_livres.empty:
                st.info("Não há planilhas pendentes na biblioteca.")
            else:
                p_escolhida = st.selectbox("Qual planilha deseja vincular?", planilhas_livres['name'].tolist())
                p_id = planilhas_livres[planilhas_livres['name'] == p_escolhida]['id'].values[0]
                
                # 2. Escolher Cliente
                clientes = pd.read_sql("SELECT id, email FROM users WHERE role='Cliente' AND status='active'", conn)
                if clientes.empty:
                    st.warning("Não há clientes ativos. Aprove um cliente primeiro em 'Gestão de Usuários'.")
                else:
                    c_escolhido = st.selectbox("Para qual cliente?", clientes['email'].tolist())
                    c_id = clientes[clientes['email'] == c_escolhido]['id'].values[0]
                    
                    if st.button("Confirmar Entrega"):
                        c.execute("UPDATE data_files SET client_id=? WHERE id=?", (int(c_id), int(p_id)))
                        conn.commit()
                        st.success(f"Planilha vinculada com sucesso ao cliente {c_escolhido}!")
                        st.rerun()

        elif menu == "Gestão de Usuários":
            st.header("👥 Aprovação de Contas")
            users = pd.read_sql("SELECT id, email, role, status FROM users", conn)
            st.dataframe(users, use_container_width=True)
            u_to_app = st.number_input("ID do Usuário para Ativar/Aprovar", step=1)
            if st.button("Aprovar Agora"):
                c.execute("UPDATE users SET status='active' WHERE id=?", (u_to_app,))
                conn.commit()
                st.rerun()

    # --- DASHBOARD CLIENTE ---
    else:
        st.header(f"📊 Seus Relatórios Disponíveis")
        files = pd.read_sql(f"SELECT * FROM data_files WHERE client_id={u_id}", conn)
        
        if files.empty:
            st.info("Nenhum relatório foi direcionado para você ainda.")
        else:
            sel_f = st.selectbox("Escolha o Relatório para Visualizar", files['name'].tolist())
            row = files[files['name'] == sel_f].iloc[0]
            
            if row['type'] == 'file': df = pd.read_json(io.StringIO(row['content']))
            else: df = pd.read_csv(row['content'])
            
            # Layout do Relatório
            st.markdown(f'<div class="main-card"><h3>{sel_f}</h3><p>Data da Carga: {row["date"]}</p></div>', unsafe_allow_html=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Indicadores Principais")
                st.metric("Total de Registros", len(df))
                num_cols = df.select_dtypes(include='number').columns
                if not num_cols.empty:
                    fig = px.bar(df.head(15), y=num_cols[0], color_discrete_sequence=['#001f3f'], title=f"Top 15 - {num_cols[0]}")
                    st.plotly_chart(fig, use_container_width=True)
            
            with col_b:
                st.subheader("Exploração de Dados")
                st.dataframe(df, height=400)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Exportar para Excel/CSV", csv, f"{sel_f}.csv", "text/csv")