import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime
from fpdf import FPDF
import io
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard Arthur Pinheiro", layout="wide")

# --- ESTILIZAÇÃO CUSTOMIZADA (Marinho + Cinza) ---
def apply_custom_css():
    st.markdown("""
        <style>
        .main { background-color: #f8f9fa; }
        [data-testid="stSidebar"] { background-color: #001f3f; border-right: 2px solid #708090; }
        [data-testid="stSidebar"] * { color: white !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #708090; border-radius: 4px; color: white; padding: 10px 20px;
        }
        .stTabs [aria-selected="true"] { background-color: #001f3f !important; }
        .watermark {
            position: fixed; bottom: 10px; right: 10px; opacity: 0.4;
            font-size: 14px; color: #001f3f; font-weight: bold; z-index: 1000;
        }
        </style>
        <div class="watermark">Arthur Pinheiro - Gestão de Dados</div>
    """, unsafe_allow_html=True)

apply_custom_css()

# --- BANCO DE DADOS ---
conn = sqlite3.connect('sistema_v2.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT, password TEXT, role TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS sheets (id INTEGER PRIMARY KEY, client_id INTEGER, name TEXT, type TEXT, content TEXT, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS logs (user_id INTEGER, action TEXT, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS comments (sheet_id INTEGER, user TEXT, text TEXT, date TEXT)')
    # Criar Admin Mestre se não existir
    c.execute("INSERT OR IGNORE INTO users (id, email, password, role, status) VALUES (1, 'admin@master.com', '1234', 'admin', 'active')")
    conn.commit()

init_db()

# --- FUNÇÕES DE SUPORTE ---
def log_activity(uid, msg):
    c.execute("INSERT INTO logs VALUES (?,?,?)", (uid, msg, datetime.now().strftime("%d/%m/%Y %H:%M")))
    conn.commit()

def convert_df_to_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "Relatorio de Performance", 1, 1, 'C')
    pdf.set_font("Arial", size=10)
    for i in range(len(df.head(15))):
        pdf.ln(5)
        pdf.write(5, str(df.iloc[i].to_dict()))
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- AUTENTICAÇÃO ---
if 'user' not in st.session_state:
    st.session_state.user = None

def login_screen():
    st.title("📊 Sistema de Relatórios")
    st.caption("Desenvolvido por Arthur Pinheiro")
    
    tab_login, tab_reg = st.tabs(["Login", "Solicitar Cadastro"])
    
    with tab_login:
        email = st.text_input("E-mail")
        pwd = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            c.execute("SELECT * FROM users WHERE email=? AND password=? AND status='active'", (email, pwd))
            user = c.fetchone()
            if user:
                st.session_state.user = user
                log_activity(user[0], "Fez login")
                st.rerun()
            else:
                st.error("Acesso negado ou aguardando aprovação do Admin Mestre.")

    with tab_reg:
        new_email = st.text_input("Novo E-mail")
        new_pwd = st.text_input("Defina uma Senha")
        new_role = st.selectbox("Tipo", ["Cliente", "Admin"])
        if st.button("Solicitar"):
            try:
                c.execute("INSERT INTO users (email, password, role, status) VALUES (?,?,?,?)", (new_email, new_pwd, new_role, 'pending'))
                conn.commit()
                st.success("Solicitação enviada!")
            except: st.error("Erro ao solicitar.")

# --- VISÃO ADMIN ---
def admin_view():
    st.sidebar.subheader("👑 Painel Admin")
    page = st.sidebar.radio("Navegação", ["Dashboard", "Aprovar Usuários", "Upload/Links", "Log de Atividades"])

    if page == "Aprovar Usuários":
        st.header("Gerenciar Acessos")
        users = pd.read_sql("SELECT id, email, role, status FROM users WHERE status='pending'", conn)
        if users.empty: st.info("Nenhuma solicitação pendente.")
        else:
            st.table(users)
            uid = st.number_input("ID para aprovar", step=1)
            if st.button("Aprovar"):
                c.execute("UPDATE users SET status='active' WHERE id=?", (uid,))
                conn.commit()
                st.success("Usuário aprovado!")
                st.rerun()

    elif page == "Upload/Links":
        st.header("Vincular Planilha a Cliente")
        clients = pd.read_sql("SELECT id, email FROM users WHERE role='Cliente' AND status='active'", conn)
        
        if clients.empty:
            st.warning("Não há clientes cadastrados para receber planilhas.")
        else:
            client_map = dict(zip(clients['email'], clients['id']))
            selected_client_email = st.selectbox("Selecione o Cliente", list(client_map.keys()))
            target_id = client_map[selected_client_email]
            
            metodo = st.radio("Método", ["Upload de Arquivo", "Link Google Planilhas (CSV Export)"])
            
            if metodo == "Upload de Arquivo":
                file = st.file_uploader("Arquivo Excel ou CSV", type=['xlsx', 'csv'])
                if file and st.button("Salvar Planilha"):
                    df = pd.read_csv(file) if file.name.endswith('csv') else pd.read_excel(file)
                    c.execute("INSERT INTO sheets (client_id, name, type, content, date) VALUES (?,?,?,?,?)",
                              (target_id, file.name, "file", df.to_json(), datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Salvo com sucesso!")
            else:
                url = st.text_input("URL do Google Sheets (Precisa estar 'público para qualquer pessoa com o link')")
                nome_link = st.text_input("Nome da Aba/Relatório")
                if url and st.button("Vincular Link"):
                    # Converte link normal em link de exportação CSV
                    if "edit" in url: url = url.split("/edit")[0] + "/export?format=csv"
                    c.execute("INSERT INTO sheets (client_id, name, type, content, date) VALUES (?,?,?,?,?)",
                              (target_id, nome_link, "link", url, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Link vinculado!")

    elif page == "Log de Atividades":
        st.header("Frequência de Acesso")
        logs = pd.read_sql("SELECT u.email, l.action, l.date FROM logs l JOIN users u ON l.user_id = u.id ORDER BY l.date DESC", conn)
        st.dataframe(logs, use_container_width=True)

# --- VISÃO CLIENTE ---
def client_view():
    uid = st.session_state.user[0]
    st.sidebar.subheader("👤 Área do Cliente")
    
    my_sheets = pd.read_sql(f"SELECT * FROM sheets WHERE client_id={uid}", conn)
    
    if my_sheets.empty:
        st.info("Bem-vindo! Suas planilhas aparecerão aqui assim que o administrador fizer o upload.")
    else:
        sheet_names = my_sheets['name'].tolist()
        sel_name = st.sidebar.selectbox("Selecione o Relatório", sheet_names)
        row = my_sheets[my_sheets['name'] == sel_name].iloc[0]
        
        # Carregar Dados
        try:
            if row['type'] == "file": df = pd.read_json(io.StringIO(row['content']))
            else: df = pd.read_csv(row['content'])
            
            tab_geral, tab_fin, tab_perf, tab_dados = st.tabs(["Geral", "Financeiro", "Performance", "Dados Brutos"])
            
            with tab_geral:
                st.subheader(f"Dashboard: {sel_name}")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Registros", len(df))
                col2.metric("Última Atualização", row['date'])
                
                # Gráfico Automático
                num_cols = df.select_dtypes(include=['number']).columns
                if len(num_cols) > 0:
                    fig = px.bar(df.head(10), y=num_cols[0], title=f"Análise de {num_cols[0]}")
                    st.plotly_chart(fig, use_container_width=True)
                
            with tab_dados:
                st.dataframe(df, use_container_width=True)
                
                st.divider()
                st.subheader("Comentários")
                com_text = st.text_input("Deixe uma observação...")
                if st.button("Enviar Comentário"):
                    c.execute("INSERT INTO comments VALUES (?,?,?,?)", (int(row['id']), st.session_state.user[1], com_text, datetime.now().strftime("%d/%m %H:%M")))
                    conn.commit()
                
                coms = pd.read_sql(f"SELECT * FROM comments WHERE sheet_id={row['id']}", conn)
                for i, c_row in coms.iterrows():
                    st.caption(f"**{c_row['user']}** em {c_row['date']}: {c_row['text']}")

            # Botões de Exportação na Lateral
            st.sidebar.divider()
            if st.sidebar.button("Gerar PDF"):
                pdf_data = convert_df_to_pdf(df)
                st.sidebar.download_button("Baixar PDF", pdf_data, "relatorio.pdf")
            
            towriter = io.BytesIO()
            df.to_excel(towriter, index=False)
            st.sidebar.download_button("Baixar Excel", towriter.getvalue(), "relatorio.xlsx")

        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}. Verifique se o link do Google Sheets está público.")

# --- LÓGICA PRINCIPAL ---
if st.session_state.user is None:
    login_screen()
else:
    st.sidebar.write(f"Conectado como: **{st.session_state.user[1]}**")
    if st.sidebar.button("Sair"):
        st.session_state.user = None
        st.rerun()
    
    if st.session_state.user[3] == 'admin': admin_view()
    else: client_view()