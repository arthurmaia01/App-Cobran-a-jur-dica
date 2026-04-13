import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from datetime import datetime
from fpdf import FPDF
import io
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema de Gestão - Arthur Pinheiro", layout="wide", initial_sidebar_state="expanded")

# --- CSS CUSTOMIZADO PARA DESIGN PREMIUM ---
def apply_custom_css():
    st.markdown("""
        <style>
        /* Importação de fonte */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        * { font-family: 'Inter', sans-serif; }

        /* Background Geral e Sidebar */
        .stApp { background-color: #f4f7f9; }
        [data-testid="stSidebar"] { 
            background-color: #001f3f !important; 
            border-right: 1px solid #708090;
        }
        
        /* Estilo dos Cards */
        .metric-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-left: 5px solid #001f3f;
            margin-bottom: 20px;
        }

        /* Botões */
        .stButton>button {
            width: 100%;
            border-radius: 5px;
            background-color: #001f3f;
            color: white;
            font-weight: 600;
            border: none;
            padding: 10px;
            transition: 0.3s;
        }
        .stButton>button:hover {
            background-color: #708090;
            color: white;
        }

        /* Tabs (Abas) */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #e9ecef;
            border-radius: 5px 5px 0 0;
            padding: 10px 30px;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: #001f3f !important;
            color: white !important;
        }

        /* Marca D'água */
        .watermark {
            position: fixed;
            bottom: 20px;
            right: 20px;
            opacity: 0.3;
            font-size: 14px;
            color: #001f3f;
            font-weight: bold;
            z-index: 1000;
        }

        /* Centralizar Login */
        .login-container {
            max-width: 450px;
            margin: auto;
            padding: 40px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
        </style>
        <div class="watermark">Arthur Pinheiro - Gestão Especializada</div>
    """, unsafe_allow_html=True)

apply_custom_css()

# --- BANCO DE DADOS ---
conn = sqlite3.connect('gestao_arthur.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS sheets (id INTEGER PRIMARY KEY, client_id INTEGER, name TEXT, type TEXT, content TEXT, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS logs (user_id INTEGER, action TEXT, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS comments (sheet_id INTEGER, user TEXT, text TEXT, date TEXT)')
    c.execute("INSERT OR IGNORE INTO users (id, email, password, role, status) VALUES (1, 'admin@master.com', '1234', 'admin', 'active')")
    conn.commit()

init_db()

# --- FUNÇÕES ---
def log_activity(uid, msg):
    c.execute("INSERT INTO logs VALUES (?,?,?)", (uid, msg, datetime.now().strftime("%d/%m/%Y %H:%M")))
    conn.commit()

# --- TELA DE LOGIN ---
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/3222/3222800.png", width=80) # Ícone genérico
        st.title("Acesso ao Sistema")
        st.caption("Insira suas credenciais para gerenciar seus relatórios.")
        
        tab_log, tab_reg = st.tabs(["🔐 Entrar", "📝 Solicitar Conta"])
        
        with tab_log:
            email = st.text_input("E-mail", key="log_email")
            pwd = st.text_input("Senha", type="password", key="log_pwd")
            if st.button("Acessar Painel"):
                c.execute("SELECT * FROM users WHERE email=? AND password=? AND status='active'", (email, pwd))
                user = c.fetchone()
                if user:
                    st.session_state.user = user
                    log_activity(user[0], "Login realizado")
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos, ou conta pendente de aprovação.")
        
        with tab_reg:
            re_email = st.text_input("Seu E-mail", key="reg_email")
            re_pwd = st.text_input("Escolha uma Senha", type="password", key="reg_pwd")
            re_role = st.selectbox("Eu sou:", ["Cliente", "Admin"])
            if st.button("Enviar Solicitação de Cadastro"):
                try:
                    c.execute("INSERT INTO users (email, password, role, status) VALUES (?,?,?,?)", (re_email, re_pwd, re_role, 'pending'))
                    conn.commit()
                    st.success("Solicitação enviada! Aguarde a aprovação de Arthur Pinheiro.")
                except: st.error("Este e-mail já possui uma solicitação.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- VISÃO ADMIN ---
def admin_view():
    st.sidebar.markdown(f"<h2 style='color:white;'>Painel Mestre</h2>", unsafe_allow_html=True)
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navegação", ["🏠 Home Admin", "👥 Gerenciar Clientes", "📂 Upload & Links", "📑 Logs de Acesso"])

    if menu == "🏠 Home Admin":
        st.header("Visão Geral do Administrador")
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown('<div class="metric-card"><h3>Usuários</h3><h4>'+str(len(pd.read_sql("SELECT * FROM users", conn)))+'</h4></div>', unsafe_allow_html=True)
        with c2: st.markdown('<div class="metric-card"><h3>Planilhas</h3><h4>'+str(len(pd.read_sql("SELECT * FROM sheets", conn)))+'</h4></div>', unsafe_allow_html=True)
        with c3: st.markdown('<div class="metric-card"><h3>Pendentes</h3><h4>'+str(len(pd.read_sql("SELECT * FROM users WHERE status='pending'", conn)))+'</h4></div>', unsafe_allow_html=True)

    elif menu == "👥 Gerenciar Clientes":
        st.header("Aprovação de Novos Usuários")
        pendentes = pd.read_sql("SELECT id, email, role FROM users WHERE status='pending'", conn)
        if pendentes.empty:
            st.info("Não há novos cadastros para aprovar.")
        else:
            st.dataframe(pendentes, use_container_width=True)
            user_id = st.number_input("Digite o ID do usuário para aprovar", step=1)
            if st.button("Aprovar Acesso"):
                c.execute("UPDATE users SET status='active' WHERE id=?", (user_id,))
                conn.commit()
                st.success("Usuário agora tem acesso ao sistema!")
                st.rerun()

    elif menu == "📂 Upload & Links":
        st.header("Anexar Dados aos Clientes")
        clientes = pd.read_sql("SELECT id, email FROM users WHERE role='Cliente' AND status='active'", conn)
        
        if clientes.empty:
            st.warning("⚠️ Primeiro, você precisa aprovar um usuário como 'Cliente' na aba 'Gerenciar Clientes'.")
        else:
            col_u1, col_u2 = st.columns([1, 1])
            with col_u1:
                st.subheader("1. Selecione o Destinatário")
                client_choice = st.selectbox("Para qual cliente é este dado?", clientes['email'].tolist())
                target_id = clientes[clientes['email'] == client_choice]['id'].values[0]
            
            with col_u2:
                st.subheader("2. Formato do Dado")
                metodo = st.radio("Como deseja enviar?", ["Arquivo Local (Excel/CSV)", "Link do Google Planilhas"])

            st.divider()

            if metodo == "Arquivo Local (Excel/CSV)":
                file = st.file_uploader("Arraste seu arquivo aqui", type=['xlsx', 'csv', 'xls'])
                if file:
                    df_temp = pd.read_csv(file) if file.name.endswith('csv') else pd.read_excel(file)
                    nome_doc = st.text_input("Nome deste relatório (Ex: Financeiro 2024)", value=file.name)
                    if st.button("Finalizar e Enviar"):
                        c.execute("INSERT INTO sheets (client_id, name, type, content, date) VALUES (?,?,?,?,?)",
                                  (int(target_id), nome_doc, "file", df_temp.to_json(), datetime.now().strftime("%d/%m/%Y")))
                        conn.commit()
                        st.success(f"Sucesso! {nome_doc} enviado para {client_choice}")

            else:
                url_g = st.text_input("Cole o Link 'Compartilhado' do Google Sheets")
                nome_g = st.text_input("Nome do Relatório via Link")
                st.caption("Dica: A planilha precisa estar configurada como 'Qualquer pessoa com o link pode ler'.")
                if st.button("Vincular Planilha Online"):
                    if "edit" in url_g: url_g = url_g.split("/edit")[0] + "/export?format=csv"
                    c.execute("INSERT INTO sheets (client_id, name, type, content, date) VALUES (?,?,?,?,?)",
                              (int(target_id), nome_g, "link", url_g, datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    st.success("Link vinculado com sucesso!")

    elif menu == "📑 Logs de Acesso":
        st.header("Histórico de Atividade")
        logs = pd.read_sql("SELECT u.email, l.action, l.date FROM logs l JOIN users u ON l.user_id = u.id ORDER BY l.date DESC", conn)
        st.table(logs)

# --- VISÃO CLIENTE ---
def client_view():
    uid = st.session_state.user[0]
    st.sidebar.markdown(f"<h2 style='color:white;'>Olá, Cliente</h2>", unsafe_allow_html=True)
    
    minhas_planilhas = pd.read_sql(f"SELECT * FROM sheets WHERE client_id={uid}", conn)
    
    if minhas_planilhas.empty:
        st.title("Bem-vindo ao seu Portal")
        st.info("Arthur Pinheiro está preparando seus dados. Assim que disponíveis, eles aparecerão aqui.")
    else:
        relatorio_foco = st.sidebar.selectbox("Selecione o Relatório", minhas_planilhas['name'].tolist())
        dados_row = minhas_planilhas[minhas_planilhas['name'] == relatorio_foco].iloc[0]
        
        # Carregar o DataFrame
        if dados_row['type'] == "file":
            df = pd.read_json(io.StringIO(dados_row['content']))
        else:
            df = pd.read_csv(dados_row['content'])

        st.title(f"📊 {relatorio_foco}")
        
        t1, t2, t3, t4 = st.tabs(["🎯 Geral", "💰 Financeiro", "📈 Performance", "📋 Dados Brutos"])
        
        with t1:
            st.subheader("Indicadores Chave (KPIs)")
            k1, k2, k3 = st.columns(3)
            with k1: st.markdown(f'<div class="metric-card">Total de Registros<br><h2>{len(df)}</h2></div>', unsafe_allow_html=True)
            with k2: st.markdown(f'<div class="metric-card">Última Atualização<br><h2>{dados_row["date"]}</h2></div>', unsafe_allow_html=True)
            with k3: st.markdown(f'<div class="metric-card">Status<br><h2>Ativo</h2></div>', unsafe_allow_html=True)
            
            if not df.empty:
                st.subheader("Distribuição de Dados")
                col_graf = st.selectbox("Analisar por:", df.columns)
                fig = px.pie(df.head(100), names=col_graf, hole=0.4, color_discrete_sequence=px.colors.qualitative.Prism)
                st.plotly_chart(fig, use_container_width=True)

        with t4:
            st.subheader("Tabela de Dados Filtrável")
            filtros = st.multiselect("Filtrar colunas:", df.columns.tolist(), default=df.columns.tolist()[:5])
            st.dataframe(df[filtros], use_container_width=True)
            
            st.divider()
            st.subheader("💬 Comentários e Documentos")
            col_c1, col_c2 = st.columns([2, 1])
            with col_c1:
                comentario = st.text_area("Escreva um comentário para o consultor Arthur...")
                if st.button("Postar Comentário"):
                    c.execute("INSERT INTO comments VALUES (?,?,?,?)", (int(dados_row['id']), st.session_state.user[1], comentario, datetime.now().strftime("%d/%m %H:%M")))
                    conn.commit()
                    st.rerun()
                
                coms_df = pd.read_sql(f"SELECT * FROM comments WHERE sheet_id={dados_row['id']}", conn)
                for i, r in coms_df.iterrows():
                    st.info(f"**{r['user']}**: {r['text']} (_{r['date']}_)")
            
            with col_c2:
                st.markdown("### Exportar")
                # Exportar Excel
                towriter = io.BytesIO()
                df.to_excel(towriter, index=False)
                st.download_button("📥 Baixar Planilha Excel", towriter.getvalue(), "relatorio.xlsx", "application/vnd.ms-excel")
                
                # Exportar PDF Simplificado
                if st.button("📄 Gerar Relatório PDF"):
                    st.write("PDF Gerado com sucesso! (Simulação)")

# --- LOGICA DE SESSÃO ---
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    login_screen()
else:
    with st.sidebar:
        st.write(f"Sessão: {st.session_state.user[1]}")
        if st.button("🚪 Sair do Sistema"):
            st.session_state.user = None
            st.rerun()
    
    if st.session_state.user[3] == 'admin':
        admin_view()
    else:
        client_view()