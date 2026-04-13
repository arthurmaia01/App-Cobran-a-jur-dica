import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import io
from datetime import datetime

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Arthur Pinheiro | Business Intelligence", layout="wide")

def style():
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f6; }
        [data-testid="stSidebar"] { background-color: #001f3f !important; }
        [data-testid="stSidebar"] * { color: white !important; }
        .main-card {
            background-color: white; padding: 25px; border-radius: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-top: 5px solid #001f3f;
        }
        .watermark { position: fixed; bottom: 10px; right: 15px; opacity: 0.5; color: #001f3f; font-weight: bold; }
        </style>
        <div class="watermark">Arthur Pinheiro - Gestão de Dados</div>
    """, unsafe_allow_html=True)

style()

# --- BANCO DE DADOS ---
conn = sqlite3.connect('banco_final.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT, password TEXT, role TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS data_files (id INTEGER PRIMARY KEY, client_id INTEGER, name TEXT, content TEXT, type TEXT, date TEXT)')
    c.execute("INSERT OR IGNORE INTO users VALUES (1, 'admin@master.com', '1234', 'admin', 'active')")
    conn.commit()

init_db()

# --- INTERFACE DE LOGIN ---
if 'logged_user' not in st.session_state:
    st.session_state.logged_user = None

if st.session_state.logged_user is None:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.title("🚀 Sistema de Relatórios")
        st.subheader("Arthur Pinheiro")
        
        mode = st.tabs(["Acessar", "Solicitar Cadastro"])
        
        with mode[0]:
            e = st.text_input("E-mail")
            p = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                c.execute("SELECT * FROM users WHERE email=? AND password=? AND status='active'", (e, p))
                res = c.fetchone()
                if res:
                    st.session_state.logged_user = res
                    st.rerun()
                else: st.error("Usuário não encontrado ou pendente.")
        
        with mode[1]:
            new_e = st.text_input("Novo E-mail")
            new_p = st.text_input("Nova Senha")
            new_r = st.selectbox("Tipo", ["Cliente", "Admin"])
            if st.button("Enviar Solicitação"):
                c.execute("INSERT INTO users (email, password, role, status) VALUES (?,?,?,?)", (new_e, new_p, new_r, 'pending'))
                conn.commit()
                st.success("Solicitação enviada ao Admin Mestre!")
        st.markdown('</div>', unsafe_allow_html=True)

# --- SISTEMA LOGADO ---
else:
    u_id, u_email, _, u_role, _ = st.session_state.logged_user
    st.sidebar.title("📊 Menu Principal")
    st.sidebar.write(f"Conectado: **{u_email}**")
    
    if st.sidebar.button("Sair"):
        st.session_state.logged_user = None
        st.rerun()

    # --- VISÃO ADMIN ---
    if u_role == 'admin':
        st.sidebar.divider()
        menu = st.sidebar.radio("Navegação", ["Dashboard", "Aprovar Usuários", "Gerenciar Planilhas"])
        
        if menu == "Aprovar Usuários":
            st.header("👥 Pendentes de Aprovação")
            pends = pd.read_sql("SELECT id, email, role FROM users WHERE status='pending'", conn)
            st.dataframe(pends, use_container_width=True)
            uid_app = st.number_input("ID para aprovar", step=1)
            if st.button("Confirmar Aprovação"):
                c.execute("UPDATE users SET status='active' WHERE id=?", (uid_app,))
                conn.commit()
                st.rerun()

        elif menu == "Gerenciar Planilhas":
            st.header("📂 Área de Upload e Links")
            clientes = pd.read_sql("SELECT id, email FROM users WHERE role='Cliente'", conn)
            
            if clientes.empty:
                st.warning("Cadastre e aprove um Cliente primeiro!")
            else:
                sel_cli = st.selectbox("Selecione o Cliente", clientes['email'].tolist())
                cid = clientes[clientes['email'] == sel_cli]['id'].values[0]
                
                tipo = st.radio("Origem do Dado", ["Arquivo Local", "Google Sheets (Link)"])
                
                if tipo == "Arquivo Local":
                    f = st.file_uploader("Subir Excel/CSV", type=["xlsx", "csv"])
                    if f and st.button("Salvar no Sistema"):
                        df = pd.read_csv(f) if f.name.endswith('csv') else pd.read_excel(f)
                        c.execute("INSERT INTO data_files (client_id, name, content, type, date) VALUES (?,?,?,?,?)",
                                  (int(cid), f.name, df.to_json(), "file", datetime.now().strftime("%d/%m/%Y")))
                        conn.commit()
                        st.success("Planilha enviada!")
                else:
                    link = st.text_input("Link da Planilha (Export CSV)")
                    nome = st.text_input("Nome do Relatório")
                    if st.button("Vincular Link"):
                        c.execute("INSERT INTO data_files (client_id, name, content, type, date) VALUES (?,?,?,?,?)",
                                  (int(cid), nome, link, "link", datetime.now().strftime("%d/%m/%Y")))
                        conn.commit()
                        st.success("Link salvo!")

    # --- VISÃO CLIENTE ---
    else:
        st.header(f"👋 Bem-vindo, {u_email}")
        files = pd.read_sql(f"SELECT * FROM data_files WHERE client_id={u_id}", conn)
        
        if files.empty:
            st.info("Seu administrador ainda não disponibilizou relatórios.")
        else:
            sel_f = st.sidebar.selectbox("Selecione sua Planilha", files['name'].tolist())
            row = files[files['name'] == sel_f].iloc[0]
            
            # Carregar DataFrame
            if row['type'] == 'file': df = pd.read_json(io.StringIO(row['content']))
            else: df = pd.read_csv(row['content'])
            
            tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 Dados", "💬 Feedback"])
            
            with tab1:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total de Linhas", len(df))
                    # Gráfico de Barras Automático
                    num_col = df.select_dtypes(include='number').columns
                    if not num_col.empty:
                        fig = px.bar(df.head(20), y=num_col[0], title=f"Análise de {num_col[0]}", color_discrete_sequence=['#001f3f'])
                        st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.metric("Data da Carga", row['date'])
                    if len(df.columns) > 1:
                        fig2 = px.line(df.head(20), title="Tendência Temporal")
                        st.plotly_chart(fig2, use_container_width=True)
            
            with tab2:
                st.dataframe(df, use_container_width=True)
                # Exportar
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Excel (CSV)", csv, "relatorio.csv", "text/csv")