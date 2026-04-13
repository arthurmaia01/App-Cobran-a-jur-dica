import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import io
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Arthur Pinheiro | BI", layout="wide")

def aplicar_estilo():
    st.markdown("""
        <style>
        .stApp { background-color: #f8f9fa; }
        [data-testid="stSidebar"] { background-color: #001f3f !important; }
        .card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-left: 6px solid #001f3f; margin-bottom: 20px; }
        .watermark { position: fixed; bottom: 10px; right: 15px; opacity: 0.3; font-weight: bold; color: #001f3f; }
        </style>
        <div class="watermark">Arthur Pinheiro - Business Intelligence</div>
    """, unsafe_allow_html=True)

aplicar_estilo()

# --- BANCO DE DADOS ---
conn = sqlite3.connect('banco_geral_v3.db', check_same_thread=False)
c = conn.cursor()

def criar_tabelas():
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT, password TEXT, role TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS biblioteca (id INTEGER PRIMARY KEY, client_id INTEGER, name TEXT, content TEXT, type TEXT, date TEXT)')
    c.execute("INSERT OR IGNORE INTO users VALUES (1, 'admin@master.com', '1234', 'admin', 'active')")
    conn.commit()

criar_tabelas()

# --- LOGICA DE ACESSO ---
if 'usuario' not in st.session_state:
    st.session_state.usuario = None

if st.session_state.usuario is None:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.title("🔐 Acesso Restrito")
        aba1, aba2 = st.tabs(["Login", "Solicitar Cadastro"])
        with aba1:
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar no Sistema"):
                c.execute("SELECT * FROM users WHERE email=? AND password=? AND status='active'", (email, senha))
                user = c.fetchone()
                if user:
                    st.session_state.usuario = user
                    st.rerun()
                else: st.error("Usuário não encontrado ou não aprovado.")
        with aba2:
            n_email = st.text_input("E-mail para cadastro")
            n_senha = st.text_input("Senha para cadastro")
            n_role = st.selectbox("Eu sou:", ["Cliente", "Admin"])
            if st.button("Enviar Pedido"):
                try:
                    c.execute("INSERT INTO users (email, password, role, status) VALUES (?,?,?,?)", (n_email, n_senha, n_role, 'pending'))
                    conn.commit()
                    st.success("Pedido enviado! Fale com Arthur para aprovar.")
                except: st.error("Erro ou e-mail já cadastrado.")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    u_id, u_email, _, u_role, _ = st.session_state.usuario
    st.sidebar.title("Menu")
    st.sidebar.write(f"Logado como: **{u_email}**")
    if st.sidebar.button("Sair"):
        st.session_state.usuario = None
        st.rerun()

    # --- ÁREA DO ADMINISTRADOR ---
    if u_role == 'admin':
        menu = st.sidebar.radio("Navegação", ["📥 Biblioteca (Upload)", "🔗 Vincular ao Cliente", "👥 Aprovar Usuários", "📊 Visão Geral"])

        if menu == "📥 Biblioteca (Upload)":
            st.header("📥 Central de Planilhas (Biblioteca)")
            st.markdown('<div class="card">Nesta área você sobe os arquivos para o sistema de forma independente. Eles ficam guardados aqui até você decidir para qual cliente enviar.</div>', unsafe_allow_html=True)
            
            nome_doc = st.text_input("Nome do Relatório (Ex: Performance Vendas Jan/24)")
            metodo = st.radio("Origem", ["Arquivo (Excel/CSV)", "Link (Google Sheets)"])
            
            if metodo == "Arquivo (Excel/CSV)":
                arq = st.file_uploader("Selecione o arquivo", type=['xlsx', 'csv'])
                if arq and nome_doc and st.button("Salvar na Biblioteca"):
                    df = pd.read_csv(arq) if arq.name.endswith('csv') else pd.read_excel(arq)
                    # client_id = 0 significa que está na biblioteca sem dono
                    c.execute("INSERT INTO biblioteca (client_id, name, content, type, date) VALUES (0, ?, ?, 'file', ?)",
                              (nome_doc, df.to_json(), datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    st.success(f"'{nome_doc}' adicionado à biblioteca com sucesso!")
            else:
                link_g = st.text_input("Link de exportação CSV do Google")
                if link_g and nome_doc and st.button("Vincular Link"):
                    c.execute("INSERT INTO biblioteca (client_id, name, content, type, date) VALUES (0, ?, ?, 'link', ?)",
                              (nome_doc, link_g, datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    st.success("Link salvo na biblioteca!")

        elif menu == "🔗 Vincular ao Cliente":
            st.header("🔗 Direcionar Planilha para Cliente")
            
            # Pega planilhas que estão na biblioteca (client_id = 0)
            livres = pd.read_sql("SELECT id, name FROM biblioteca WHERE client_id=0", conn)
            # Pega clientes ativos
            clientes = pd.read_sql("SELECT id, email FROM users WHERE role='Cliente' AND status='active'", conn)
            
            if livres.empty:
                st.info("Não há planilhas novas na biblioteca para vincular.")
            elif clientes.empty:
                st.warning("Não há clientes cadastrados ou aprovados.")
            else:
                p_nome = st.selectbox("Escolha a Planilha", livres['name'].tolist())
                c_email = st.selectbox("Escolha o Cliente Destinatário", clientes['email'].tolist())
                
                p_id = livres[livres['name'] == p_nome]['id'].values[0]
                c_id = clientes[clientes['email'] == c_email]['id'].values[0]
                
                if st.button("Vincular Agora"):
                    c.execute("UPDATE biblioteca SET client_id=? WHERE id=?", (int(c_id), int(p_id)))
                    conn.commit()
                    st.success("Vinculado com sucesso! O cliente já pode ver o relatório.")
                    st.rerun()

        elif menu == "👥 Aprovar Usuários":
            st.header("👥 Gerenciar Acessos")
            usuarios = pd.read_sql("SELECT id, email, role, status FROM users", conn)
            st.dataframe(usuarios, use_container_width=True)
            uid = st.number_input("ID do usuário para Aprovar", step=1)
            if st.button("Aprovar Cadastro"):
                c.execute("UPDATE users SET status='active' WHERE id=?", (uid,))
                conn.commit()
                st.success("Usuário aprovado!")
                st.rerun()

    # --- ÁREA DO CLIENTE ---
    else:
        st.header(f"📊 Seus Relatórios")
        meus_dados = pd.read_sql(f"SELECT * FROM biblioteca WHERE client_id={u_id}", conn)
        
        if meus_dados.empty:
            st.info("Olá! Seus relatórios aparecerão aqui assim que forem processados pelo administrador.")
        else:
            escolha = st.selectbox("Selecione o Relatório", meus_dados['name'].tolist())
            linha = meus_dados[meus_dados['name'] == escolha].iloc[0]
            
            if linha['type'] == 'file': df = pd.read_json(io.StringIO(linha['content']))
            else: df = pd.read_csv(linha['content'])
            
            st.markdown(f'<div class="card"><h3>{escolha}</h3><p>Atualizado em: {linha["date"]}</p></div>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Total de Linhas", len(df))
                nums = df.select_dtypes(include='number').columns
                if not nums.empty:
                    fig = px.bar(df.head(10), y=nums[0], title=f"Análise: {nums[0]}", color_discrete_sequence=['#001f3f'])
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.dataframe(df, height=350)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Excel (CSV)", csv, f"{escolha}.csv")