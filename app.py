import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import io
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arthur Pinheiro | Business Intelligence", layout="wide", initial_sidebar_state="expanded")

# --- DESIGN PREMIUM (CSS CUSTOMIZADO) ---
def local_css():
    st.markdown("""
        <style>
        /* Importar Fonte Profissional */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"]  {
            font-family: 'Inter', sans-serif;
            background-color: #F8F9FB;
        }

        /* Sidebar Customizada */
        [data-testid="stSidebar"] {
            background-color: #001f3f !important;
            border-right: 1px solid #708090;
        }
        [data-testid="stSidebar"] * { color: white !important; }

        /* Cards de KPI e Layout */
        .kpi-card {
            background-color: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            border-bottom: 4px solid #001f3f;
            text-align: center;
        }
        .kpi-card h3 { color: #708090; font-size: 14px; margin-bottom: 5px; }
        .kpi-card h2 { color: #001f3f; font-size: 28px; font-weight: 700; }

        /* Estilização de Botões */
        .stButton>button {
            width: 100%;
            border-radius: 8px;
            background-color: #001f3f;
            color: white;
            border: none;
            padding: 12px;
            font-weight: 600;
            transition: 0.3s;
        }
        .stButton>button:hover {
            background-color: #708090;
            transform: translateY(-2px);
        }

        /* Marca d'água */
        .watermark {
            position: fixed;
            bottom: 20px;
            right: 30px;
            opacity: 0.4;
            font-weight: 700;
            color: #001f3f;
            font-size: 14px;
            z-index: 100;
        }

        /* Títulos */
        h1, h2, h3 { color: #001f3f; font-weight: 700; }
        
        /* Ajuste de tabelas */
        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }
        </style>
        <div class="watermark">ARTHUR PINHEIRO - GESTÃO DE DADOS</div>
    """, unsafe_allow_html=True)

local_css()

# --- BANCO DE DADOS ---
conn = sqlite3.connect('banco_premium.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS biblioteca (id INTEGER PRIMARY KEY, client_id INTEGER, name TEXT, content TEXT, type TEXT, date TEXT)')
    c.execute("INSERT OR IGNORE INTO users (id, email, password, role, status) VALUES (1, 'admin@master.com', '1234', 'admin', 'active')")
    conn.commit()

init_db()

# --- SESSÃO E LOGIN ---
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
            <div style='text-align: center; margin-bottom: 20px;'>
                <h1 style='font-size: 40px;'>💎</h1>
                <h2>Portal Arthur Pinheiro</h2>
                <p style='color: #708090;'>Business Intelligence & Analytics</p>
            </div>
        """, unsafe_allow_html=True)
        
        tab_l, tab_r = st.tabs(["🔐 Entrar", "📝 Criar Conta"])
        with tab_l:
            e = st.text_input("E-mail")
            p = st.text_input("Senha", type="password")
            if st.button("Acessar Dashboard"):
                c.execute("SELECT * FROM users WHERE email=? AND password=? AND status='active'", (e, p))
                res = c.fetchone()
                if res:
                    st.session_state.user = res
                    st.rerun()
                else: st.error("Credenciais inválidas ou conta aguardando aprovação.")
        with tab_r:
            ne = st.text_input("E-mail Profissional")
            np = st.text_input("Senha Desejada", type="password")
            nr = st.selectbox("Perfil de Acesso", ["Cliente", "Admin"])
            if st.button("Solicitar Cadastro"):
                try:
                    c.execute("INSERT INTO users (email, password, role, status) VALUES (?,?,?,?)", (ne, np, nr, 'pending'))
                    conn.commit()
                    st.success("Solicitação enviada com sucesso!")
                except: st.error("Este e-mail já está em nossa base.")

else:
    u_id, u_email, _, u_role, _ = st.session_state.user
    
    # --- SIDEBAR PROFISSIONAL ---
    st.sidebar.markdown(f"""
        <div style='text-align: center; padding: 20px 0;'>
            <h2 style='color: white; margin-bottom: 0;'>Arthur Pinheiro</h2>
            <p style='color: #708090; font-size: 12px;'>SISTEMA DE GESTÃO</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.divider()
    
    if u_role == 'admin':
        menu = st.sidebar.radio("MENU ADMINISTRATIVO", ["📊 Dashboard Geral", "📥 Biblioteca de Dados", "🔗 Vincular Clientes", "👥 Gestão de Acessos"])
    else:
        menu = "Área do Cliente"

    st.sidebar.divider()
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state.user = None
        st.rerun()

    # --- LÓGICA ADMIN ---
    if u_role == 'admin':
        if menu == "📊 Dashboard Geral":
            st.title("📊 Visão Estratégica")
            
            df_all = pd.read_sql("SELECT * FROM biblioteca", conn)
            df_users = pd.read_sql("SELECT * FROM users WHERE role='Cliente'", conn)
            
            col_k1, col_k2, col_k3 = st.columns(3)
            with col_k1:
                st.markdown(f"<div class='kpi-card'><h3>RELATÓRIOS TOTAIS</h3><h2>{len(df_all)}</h2></div>", unsafe_allow_html=True)
            with col_k2:
                st.markdown(f"<div class='kpi-card'><h3>CLIENTES ATIVOS</h3><h2>{len(df_users[df_users['status']=='active'])}</h2></div>", unsafe_allow_html=True)
            with col_k3:
                st.markdown(f"<div class='kpi-card'><h3>ITENS NA BIBLIOTECA</h3><h2>{len(df_all[df_all['client_id']==0])}</h2></div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("📋 Monitoramento de Planilhas")
            st.dataframe(df_all, use_container_width=True)

        elif menu == "📥 Biblioteca de Dados":
            st.title("📥 Central de Upload")
            with st.container():
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                c_u1, c_u2 = st.columns(2)
                with c_u1:
                    nome = st.text_input("Título do Relatório")
                    tipo_f = st.radio("Origem dos Dados", ["Upload de Arquivo", "Link Google Sheets"])
                with c_u2:
                    if tipo_f == "Upload de Arquivo":
                        arq = st.file_uploader("Arraste o Excel ou CSV", type=['xlsx', 'csv'])
                    else:
                        link = st.text_input("Cole o link CSV do Google")
                
                if st.button("⚡ Salvar e Processar"):
                    if nome:
                        content = ""
                        if tipo_f == "Upload de Arquivo" and arq:
                            df_p = pd.read_csv(arq) if arq.name.endswith('csv') else pd.read_excel(arq)
                            content = df_p.to_json()
                        else: content = link
                        
                        c.execute("INSERT INTO biblioteca (client_id, name, content, type, date) VALUES (0, ?, ?, ?, ?)",
                                  (nome, content, 'file' if tipo_f == "Upload de Arquivo" else 'link', datetime.now().strftime("%d/%m/%Y %H:%M")))
                        conn.commit()
                        st.success("Dados armazenados na biblioteca!")
                st.markdown("</div>", unsafe_allow_html=True)

        elif menu == "🔗 Vincular Clientes":
            st.title("🔗 Direcionamento de Dados")
            livres = pd.read_sql("SELECT id, name FROM biblioteca WHERE client_id=0", conn)
            clientes = pd.read_sql("SELECT id, email FROM users WHERE role='Cliente' AND status='active'", conn)
            
            if livres.empty or clientes.empty:
                st.warning("Certifique-se de ter planilhas na biblioteca e clientes aprovados.")
            else:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                sel_p = st.selectbox("Selecione a Planilha", livres['name'].tolist())
                sel_c = st.selectbox("Selecione o Cliente", clientes['email'].tolist())
                if st.button("Confirmar Entrega do Relatório"):
                    pid = livres[livres['name']==sel_p]['id'].values[0]
                    cid = clientes[clientes['email']==sel_c]['id'].values[0]
                    c.execute("UPDATE biblioteca SET client_id=? WHERE id=?", (int(cid), int(pid)))
                    conn.commit()
                    st.success(f"O cliente {sel_c} agora tem acesso ao relatório {sel_p}!")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        elif menu == "👥 Gestão de Acessos":
            st.title("👥 Controle de Usuários")
            users = pd.read_sql("SELECT id, email, role, status FROM users", conn)
            st.dataframe(users, use_container_width=True)
            u_id_app = st.number_input("ID para Ativar", step=1)
            if st.button("✅ Aprovar Usuário"):
                c.execute("UPDATE users SET status='active' WHERE id=?", (u_id_app,))
                conn.commit()
                st.rerun()

    # --- ÁREA DO CLIENTE (O DIFERENCIAL) ---
    else:
        st.title("💎 Seu Painel de Performance")
        meus_dados = pd.read_sql(f"SELECT * FROM biblioteca WHERE client_id={u_id}", conn)
        
        if meus_dados.empty:
            st.info("Arthur Pinheiro está preparando seus dados. Em breve estarão disponíveis aqui.")
        else:
            sel_rep = st.selectbox("Selecione o Relatório para Visualizar", meus_dados['name'].tolist())
            row = meus_dados[meus_dados['name'] == sel_rep].iloc[0]
            
            # Carregar Dados
            if row['type'] == 'file': df = pd.read_json(io.StringIO(row['content']))
            else: df = pd.read_csv(row['content'])
            
            # Layout Premium Cliente
            st.markdown(f"### 📑 {sel_rep}")
            st.caption(f"Última atualização: {row['date']}")
            
            c_k1, c_k2, c_k3, c_k4 = st.columns(4)
            with c_k1: st.markdown(f"<div class='kpi-card'><h3>TOTAL REGISTROS</h3><h2>{len(df)}</h2></div>", unsafe_allow_html=True)
            with c_k2: 
                v = df.select_dtypes(include='number').columns
                val = round(df[v[0]].sum(), 2) if not v.empty else "N/A"
                st.markdown(f"<div class='kpi-card'><h3>VOLUME TOTAL</h3><h2>{val}</h2></div>", unsafe_allow_html=True)
            with c_k3: st.markdown(f"<div class='kpi-card'><h3>COLUNAS</h3><h2>{len(df.columns)}</h2></div>", unsafe_allow_html=True)
            with c_k4: st.markdown(f"<div class='kpi-card'><h3>STATUS</h3><h2>CONCLUÍDO</h2></div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # GRÁFICO INTERATIVO (PLOTLY)
            st.subheader("📈 Análise Gráfica Interativa")
            col_x = st.selectbox("Eixo X (Categorias)", df.columns)
            col_y = st.selectbox("Eixo Y (Valores)", df.select_dtypes(include='number').columns if not df.select_dtypes(include='number').columns.empty else df.columns)
            
            fig = px.bar(df.head(30), x=col_x, y=col_y, 
                         color_discrete_sequence=['#001f3f'], 
                         template="plotly_white",
                         text_auto='.2s')
            fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

            # TABELA INTERATIVA
            st.subheader("📋 Tabela de Dados Completa")
            st.dataframe(df, use_container_width=True, height=400)
            
            # EXPORTAÇÃO
            st.markdown("<br>", unsafe_allow_html=True)
            col_ex1, col_ex2 = st.columns([1, 4])
            with col_ex1:
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Excel (CSV)", csv_data, f"{sel_rep}.csv", "text/csv")