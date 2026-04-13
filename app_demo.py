import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import io
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Banco de Dados - Clientes (DEMO)", layout="wide")

# --- FUNÇÃO GERADORA DE DADOS FICTÍCIOS (CACHEADA PARA PERFORMANCE) ---
@st.cache_data(show_spinner=False)
def load_data(n_ativos=15000, n_inativos=3000):
    # Dicionários base para simular a realidade de uma distribuidora no RJ
    gerencias = ['GER INTERNO', 'MBR GER INT', 'MGR GER FARMA VET', 'GER VAREJO ALIMENTAR', 'GER KEY ACCOUNT']
    equipes = ['EQP CENTRO', 'EQP BAIXADA', 'EQP ZONA SUL', 'EQP OESTE', 'EQP NITERÓI', 'EQP SÃO GONÇALO']
    vendedores = [
        (101, 'CARLOS SILVA'), (102, 'ANA SOUZA'), (103, 'JOAO PEREIRA'), (104, 'MARIA LIMA'),
        (105, 'VAGO ROTA 05'), (106, 'FERNANDO COSTA'), (107, 'JULIA ALVES'), (108, 'ROBERTO GOMES')
    ]
    municipios = ['Rio de Janeiro', 'Nova Iguaçu', 'Duque de Caxias', 'Belford Roxo', 'São João de Meriti', 'Niterói']
    bairros = ['Centro', 'Copacabana', 'Madureira', 'Posse', 'Comendador Soares', 'Vilar dos Teles', 'Icaraí']
    segmentos = ['FARMÁCIA', 'MERCADO', 'PET SHOP', 'CONVENIÊNCIA', 'PADARIA']
    origens = ['TARGET MOB', 'E-COMMERCE', 'DIGITACAO', 'TELEVENDAS']
    sit_cred = ['NORMAL', 'BLOQUEADO', 'AVALIACAO', 'LIMITE EXCEDIDO']
    
    # Coordenadas base (Centro do RJ) para gerar pontos próximos
    base_lat, base_lon = -22.9068, -43.1729 
    
    def generate_df(n_rows, is_ativo=True):
        np.random.seed(42 if is_ativo else 24) # Semente para sempre gerar os mesmos dados fictícios
        
        # Gerando Vendedores
        vends_escolhidos = [vendedores[i] for i in np.random.randint(0, len(vendedores), n_rows)]
        cod_vend = [v[0] for v in vends_escolhidos]
        nome_vend = [v[1] for v in vends_escolhidos]
        
        # Gerando Clientes (Simulando compartilhamento)
        # Se for ativo, criamos menos IDs únicos do que linhas para forçar duplicatas (compartilhados)
        n_unique_clients = int(n_rows * 0.85) if is_ativo else n_rows 
        cod_clientes = np.random.randint(10000, 10000 + n_unique_clients, n_rows)
        
        # Datas
        hoje = pd.Timestamp.now().normalize()
        dias_cad = np.random.randint(10, 1500, n_rows)
        dt_cad = hoje - pd.to_timedelta(dias_cad, unit='d')
        
        dias_ult_ped = np.random.randint(1, 150, n_rows)
        dt_ult_ped = hoje - pd.to_timedelta(dias_ult_ped, unit='d')
        # Algum percentual sem compra (nunca comprou)
        dt_ult_ped[np.random.rand(n_rows) > 0.9] = pd.NaT
        
        dias_contato = np.random.randint(1, 30, n_rows)
        dt_contato = dt_ult_ped + pd.to_timedelta(dias_contato, unit='d')
        
        # Financeiro
        limite = np.random.uniform(500, 50000, n_rows).round(2)
        inad = np.where(np.random.rand(n_rows) > 0.8, np.random.uniform(100, 5000, n_rows).round(2), 0)
        
        # Criando o dicionário de colunas
        data = {
            'Gerencia': np.random.choice(gerencias, n_rows),
            'Equipe': np.random.choice(equipes, n_rows),
            'Cod Vend': cod_vend,
            'Vendedor': nome_vend,
            'Cod Clien': cod_clientes,
            'Cliente': [f"CLIENTE FICTICIO {cod}" for cod in cod_clientes],
            'E-mail': [f"contato{cod}@email.com" for cod in cod_clientes],
            'Segmento': np.random.choice(segmentos, n_rows),
            'Endereco': [f"Rua Ficticia, {np.random.randint(1, 1000)}" for _ in range(n_rows)],
            'Bairro': np.random.choice(bairros, n_rows),
            'Municipio': np.random.choice(municipios, n_rows),
            'UF': 'RJ',
            'Latitude': base_lat + np.random.normal(0, 0.15, n_rows),
            'Longitude': base_lon + np.random.normal(0, 0.15, n_rows),
            'Colig': np.random.choice(['COLIGADA A', 'COLIGADA B', None, None], n_rows),
            'Grupo': np.random.choice(['GRUPO MASTER', 'REDE SUL', None, None], n_rows),
            'TipoPessoa': np.random.choice(['J', 'J', 'J', 'F'], n_rows),
            'CNPJ/CPF': [f"{np.random.randint(10,99)}.{np.random.randint(100,999)}.{np.random.randint(100,999)}/0001-{np.random.randint(10,99)}" for _ in range(n_rows)],
            'AreaVenda': np.random.choice(['ZONA NORTE', 'BAIXADA I', 'BAIXADA II', 'ZONA SUL'], n_rows),
            'SitCred': np.random.choice(sit_cred, n_rows),
            'LimiteTotal': limite,
            'UltPed': np.random.randint(500000, 600000, n_rows),
            'VendUltPed': np.where(np.random.rand(n_rows) > 0.3, cod_vend, np.random.choice([v[0] for v in vendedores], n_rows)),
            'DtUltPed': dt_ult_ped,
            'OrigemUltPedido': np.random.choice(origens, n_rows),
            'Inad-3dd': inad,
            'CondPgto': np.random.choice(['28 Dias', '14/28 Dias', None, 'A Vista'], n_rows),
            'UltContato': dt_contato,
            'RespUltContato': np.random.choice(['OPERADOR 1', 'OPERADOR 2', 'SISTEMA'], n_rows),
            'Resultado': np.random.choice(['VENDA', 'FALTOU DINHEIRO', 'SEM ESTOQUE', 'RECADO'], n_rows),
            'Motivo': np.random.choice(['VISITA', 'TELEFONE', 'WHATSAPP'], n_rows),
            'OBS': ['Obs teste portfólio' for _ in range(n_rows)],
            'DataCadastro': dt_cad
        }
        
        df = pd.DataFrame(data)
        return df

    # Gerando as bases
    df_ativos = generate_df(n_ativos, is_ativo=True)
    df_inativos = generate_df(n_inativos, is_ativo=False)
    
    # Tratamentos essenciais iguais aos do SQL
    for df in [df_ativos]:
        df['Inad-3dd'] = pd.to_numeric(df['Inad-3dd'], errors='coerce').fillna(0)
        df['LimiteTotal'] = pd.to_numeric(df['LimiteTotal'], errors='coerce').fillna(0)
        df['VendUltPed'] = pd.to_numeric(df['VendUltPed'], errors='coerce')
        df['UltPed'] = pd.to_numeric(df['UltPed'], errors='coerce')

    df_inativos['Cod Clien'] = pd.to_numeric(df_inativos['Cod Clien'], errors='coerce')
    df_ativos['Cod Clien'] = pd.to_numeric(df_ativos['Cod Clien'], errors='coerce')

    # Identificando compartilhados
    contagem_ativos = df_ativos['Cod Clien'].value_counts()
    clientes_compartilhados = contagem_ativos[contagem_ativos > 1].index.tolist()
    df_ativos['IsCompartilhado'] = df_ativos['Cod Clien'].isin(clientes_compartilhados)
    df_ativos['StatusCarteira'] = df_ativos['IsCompartilhado'].apply(lambda x: '👥 Compartilhado' if x else '👤 Único')

    return df_ativos, df_inativos

# --- FUNÇÕES AUXILIARES ---
def parse_text_list(text_input):
    if not text_input: return []
    text_input = text_input.replace('\n', ',').replace(';', ',')
    return [x.strip() for x in text_input.split(',') if x.strip()]

def clean_cnpj_cpf(series):
    return series.astype(str).str.replace(r'[./-]', '', regex=True)

def format_ptbr(numero):
    return f"{numero:,}".replace(",", ".")

def normalizar_cod(val):
    if pd.isna(val) or str(val).strip() == '' or str(val).strip().lower() == 'nan':
        return None
    val_str = str(val).strip()
    try:
        return str(int(float(val_str)))
    except:
        return val_str.upper()

def definir_status_rota(row, dias_limite):
    nome = str(row['Vendedor']).upper()
    if 'VAGO' in nome or 'VAGA' in nome:
        return '🔴 VAGA (Nome)'
    elif row['Dias_Sem_Venda'] >= dias_limite:
        return '🟠 PARADA (S/ Venda Própria)'
    else:
        return '🟢 ATIVA'

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# =============================================================================
# APLICAÇÃO PRINCIPAL
# =============================================================================

st.title("📊 Banco de Dados de Base Ativa e Inativa (Portfólio DEMO)")
st.markdown("⚠️ *Aviso: Todos os dados apresentados neste painel são fictícios e gerados aleatoriamente para fins de demonstração.*")
st.markdown("---")

# CONTROLE DE CACHE E EXIBIÇÃO
st.sidebar.header("⚙️ Gerenciamento de Dados")
if st.sidebar.button("🔄 Gerar Novos Dados Fictícios", help="Força a recriação da base de dados com novos valores aleatórios."):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🖥️ Opções de Exibição")
f_mostrar_todos = st.sidebar.toggle("Carregar todos os registros nas tabelas", value=False, help="Por padrão, exibe os Top 500 para melhorar a performance. Ative para ver a lista completa.")

try:
    with st.spinner("Gerando e processando dados mockados (Pode levar alguns segundos)..."):
        df_ativos, df_inativos = load_data()

    # =========================================================================
    # LÓGICA DE AGRUPAMENTO DE VENDEDORES
    # =========================================================================
    df_ativos['Cod_Clean'] = df_ativos['Cod Vend'].apply(normalizar_cod)
    
    def agregar_codigos_sem_nan(x):
        codigos_validos = [str(cod).strip() for cod in x if str(cod).strip().lower() not in ['nan', 'none', '', 'nat']]
        return ', '.join(sorted(codigos_validos))

    df_share_info = df_ativos.groupby('Cod Clien')['Cod_Clean'].unique().apply(agregar_codigos_sem_nan).reset_index()
    df_share_info.columns = ['Cod Clien', 'Códs. Vendedores']
    df_ativos = df_ativos.merge(df_share_info, on='Cod Clien', how='left')

    df_a_filtered = df_ativos.copy()
    df_i_filtered = df_inativos.copy()

    # =========================================================================
    # SIDEBAR - FILTROS EM CASCATA
    # =========================================================================
    st.sidebar.markdown("---")
    st.sidebar.header("Filtros Analíticos")

    with st.sidebar.expander("🔍 Busca e Vendedores", expanded=True):
        
        op_gerencia = sorted(list(set(df_a_filtered['Gerencia'].dropna()) | set(df_i_filtered['Gerencia'].dropna())))
        f_gerencia = st.multiselect("Gerência", op_gerencia)
        if f_gerencia:
            df_a_filtered = df_a_filtered[df_a_filtered['Gerencia'].isin(f_gerencia)]
            df_i_filtered = df_i_filtered[df_i_filtered['Gerencia'].isin(f_gerencia)]

        op_equipe = sorted(list(set(df_a_filtered['Equipe'].dropna()) | set(df_i_filtered['Equipe'].dropna())))
        f_equipe = st.multiselect("Equipe", op_equipe)
        if f_equipe:
            df_a_filtered = df_a_filtered[df_a_filtered['Equipe'].isin(f_equipe)]
            df_i_filtered = df_i_filtered[df_i_filtered['Equipe'].isin(f_equipe)]
        
        todos_vendedores = pd.concat([df_a_filtered['Vendedor'], df_i_filtered['Vendedor']]).dropna().astype(str)
        if not todos_vendedores.empty:
            op_prefixos = sorted(list(set(todos_vendedores.str.split().str[0].unique())))
        else:
            op_prefixos = []
        f_prefixo_vend = st.multiselect("Prefixo Vendedor", op_prefixos)
        if f_prefixo_vend:
            for df in [df_a_filtered, df_i_filtered]:
                if not df.empty:
                    prefixo_temp = df['Vendedor'].astype(str).str.split().str[0]
                    df.drop(df[~prefixo_temp.isin(f_prefixo_vend)].index, inplace=True)

        todos_vendedores_filtered = pd.concat([df_a_filtered['Vendedor'], df_i_filtered['Vendedor']]).dropna().unique()
        op_vendedor = sorted(list(todos_vendedores_filtered))
        f_vendedor_select = st.multiselect("Nome do Vendedor", op_vendedor)
        if f_vendedor_select:
            df_a_filtered = df_a_filtered[df_a_filtered['Vendedor'].isin(f_vendedor_select)]
            df_i_filtered = df_i_filtered[df_i_filtered['Vendedor'].isin(f_vendedor_select)]

        st.markdown("---") 

        f_cliente = st.text_input("Nome do Cliente", placeholder="Contém...")
        f_lista_cod_cli = st.text_area("Lista Cód. Clientes", height=68)
        f_lista_cod_vend = st.text_area("Lista Cód. Vendedores", height=68)
        f_lista_vend_ult_ped = st.text_area("Lista Cód. Vend. Últ. Pedido", height=68)
        f_lista_cnpj = st.text_area("Lista CNPJ/CPF", height=68)
        
        op_grupo = sorted(list(set(df_a_filtered['Grupo'].dropna()) | set(df_i_filtered['Grupo'].dropna())))
        f_grupo = st.multiselect("Grupo", op_grupo)
        
        op_colig = sorted(list(set(df_a_filtered['Colig'].dropna()) | set(df_i_filtered['Colig'].dropna())))
        f_colig = st.multiselect("Coligação", op_colig)
        
        f_email = st.text_input("Buscar em E-mail", placeholder="Contém...")

    # APLICANDO FILTROS DE TEXTO
    for df in [df_a_filtered, df_i_filtered]:
        if f_cliente: df.drop(df[~df['Cliente'].str.contains(f_cliente, case=False, na=False)].index, inplace=True)
        if f_email: df.drop(df[~df['E-mail'].str.contains(f_email, case=False, na=False)].index, inplace=True)
        if f_grupo: df.drop(df[~df['Grupo'].isin(f_grupo)].index, inplace=True)
        if f_colig: df.drop(df[~df['Colig'].isin(f_colig)].index, inplace=True)
        if f_lista_cod_cli:
            lista = [int(x) for x in parse_text_list(f_lista_cod_cli) if x.isdigit()]
            if lista: df.drop(df[~df['Cod Clien'].isin(lista)].index, inplace=True)
        if f_lista_cod_vend:
            clean_input = [normalizar_cod(x) for x in parse_text_list(f_lista_cod_vend)]
            clean_input = [x for x in clean_input if x is not None]
            if clean_input:
                temp_col = df['Cod Vend'].apply(normalizar_cod)
                df.drop(df[~temp_col.isin(clean_input)].index, inplace=True)
        if f_lista_vend_ult_ped:
            clean_input_ult = [normalizar_cod(x) for x in parse_text_list(f_lista_vend_ult_ped)]
            clean_input_ult = [x for x in clean_input_ult if x is not None]
            if clean_input_ult and 'VendUltPed' in df.columns:
                temp_col_ult = df['VendUltPed'].apply(normalizar_cod)
                df.drop(df[~temp_col_ult.isin(clean_input_ult)].index, inplace=True)
        if f_lista_cnpj:
            lista_clean = [x.replace('.','').replace('-','').replace('/','') for x in parse_text_list(f_lista_cnpj)]
            if lista_clean:
                col_temp = clean_cnpj_cpf(df['CNPJ/CPF'])
                df.drop(df[~col_temp.isin(lista_clean)].index, inplace=True)

    with st.sidebar.expander("🌍 Localização e Estrutura"):
        op_area = sorted(list(set(df_a_filtered['AreaVenda'].dropna()))) 
        f_area = st.multiselect("Área de Venda", op_area)
        if f_area:
            df_a_filtered = df_a_filtered[df_a_filtered['AreaVenda'].isin(f_area)]

        op_segmento = sorted(list(set(df_a_filtered['Segmento'].dropna()) | set(df_i_filtered['Segmento'].dropna())))
        f_segmento = st.multiselect("Segmento", op_segmento)
        if f_segmento:
            df_a_filtered = df_a_filtered[df_a_filtered['Segmento'].isin(f_segmento)]
            df_i_filtered = df_i_filtered[df_i_filtered['Segmento'].isin(f_segmento)]

        op_municipio = sorted(list(set(df_a_filtered['Municipio'].dropna()) | set(df_i_filtered['Municipio'].dropna())))
        f_municipio = st.multiselect("Município", op_municipio)
        if f_municipio:
            df_a_filtered = df_a_filtered[df_a_filtered['Municipio'].isin(f_municipio)]
            df_i_filtered = df_i_filtered[df_i_filtered['Municipio'].isin(f_municipio)]
            
        op_bairro = sorted(list(set(df_a_filtered['Bairro'].dropna()) | set(df_i_filtered['Bairro'].dropna())))
        f_bairro = st.multiselect("Bairro", op_bairro)
        if f_bairro:
            df_a_filtered = df_a_filtered[df_a_filtered['Bairro'].isin(f_bairro)]
            df_i_filtered = df_i_filtered[df_i_filtered['Bairro'].isin(f_bairro)]

    with st.sidebar.expander("📋 Perfil e Cadastro"):
        f_data_cad_range = st.date_input("Data de Cadastro", value=[])
        col1, col2 = st.columns(2)
        f_incluir_colig = col1.checkbox("Incluir Coligação", value=True)
        f_incluir_grupo = col2.checkbox("Incluir Grupo", value=True)
        st.markdown("**Duplicidade de Vendedores**")
        f_apenas_compartilhados = st.checkbox("Apenas Clientes Compartilhados", value=False)
        op_tipo_pessoa = sorted(list(df_a_filtered['TipoPessoa'].dropna().unique()))
        f_tipo_pessoa = st.multiselect("Tipo Pessoa", op_tipo_pessoa)

    for df in [df_a_filtered, df_i_filtered]:
        if not f_incluir_colig: df.drop(df[df['Colig'].notna() & (df['Colig'] != '')].index, inplace=True)
        if not f_incluir_grupo: df.drop(df[df['Grupo'].notna() & (df['Grupo'] != '')].index, inplace=True)
    if len(f_data_cad_range) == 2:
        df_a_filtered = df_a_filtered[(df_a_filtered['DataCadastro'].dt.date >= f_data_cad_range[0]) & (df_a_filtered['DataCadastro'].dt.date <= f_data_cad_range[1])]
    if f_apenas_compartilhados:
        df_a_filtered = df_a_filtered[df_a_filtered['IsCompartilhado'] == True]
    if f_tipo_pessoa:
        df_a_filtered = df_a_filtered[df_a_filtered['TipoPessoa'].isin(f_tipo_pessoa)]

    with st.sidebar.expander("💰 Financeiro e Vendas (Ativos)"):
        f_dt_ult_ped_range = st.date_input("Data Últ. Pedido (Intervalo)", value=[])
        col_f1, col_f2 = st.columns(2)
        f_nunca_comprou = col_f1.checkbox("Nunca Comprou (Sem Data)", value=False)
        
        op_origem = sorted(list(df_a_filtered['OrigemUltPedido'].dropna().unique()))
        f_origem = st.multiselect("Origem Último Pedido", op_origem)

        op_sitcred = sorted(list(df_a_filtered['SitCred'].dropna().unique()))
        f_sitcred = st.multiselect("Situação Crédito", op_sitcred)
        
        if not df_a_filtered.empty:
            min_lim_data = float(df_a_filtered['LimiteTotal'].min())
            max_lim_data = float(df_a_filtered['LimiteTotal'].max())
        else:
            min_lim_data, max_lim_data = 0.0, 0.0
            
        st.write("Faixa de Limite de Crédito (R$)")
        c_l1, c_l2 = st.columns(2)
        val_min_lim = c_l1.number_input("Mínimo", value=min_lim_data, step=100.0)
        val_max_lim = c_l2.number_input("Máximo", value=max_lim_data, step=100.0)

        f_cond_pgto = st.radio("Condição Pgto", ["Todos", "Apenas Depósito", "Com Prazo"], index=0)
        f_inad_tipo = st.multiselect("Status Financeiro", 
                                     ["Inadimplentes (>3dd)", "Adimplentes", "Com Crédito (Negativo)"],
                                     default=["Inadimplentes (>3dd)", "Adimplentes", "Com Crédito (Negativo)"])
        f_dias_sem_compra = st.number_input("Mínimo dias sem compra", min_value=0, value=0)

    if f_nunca_comprou:
        df_a_filtered = df_a_filtered[df_a_filtered['DtUltPed'].isna()]
    elif len(f_dt_ult_ped_range) == 2:
        df_a_filtered = df_a_filtered[(df_a_filtered['DtUltPed'].dt.date >= f_dt_ult_ped_range[0]) & (df_a_filtered['DtUltPed'].dt.date <= f_dt_ult_ped_range[1])]

    if f_origem: df_a_filtered = df_a_filtered[df_a_filtered['OrigemUltPedido'].isin(f_origem)]
    if f_sitcred: df_a_filtered = df_a_filtered[df_a_filtered['SitCred'].isin(f_sitcred)]
    df_a_filtered = df_a_filtered[(df_a_filtered['LimiteTotal'] >= val_min_lim) & (df_a_filtered['LimiteTotal'] <= val_max_lim)]

    if f_cond_pgto == "Apenas Depósito":
        df_a_filtered = df_a_filtered[df_a_filtered['CondPgto'].isna() | (df_a_filtered['CondPgto'] == '')]
    elif f_cond_pgto == "Com Prazo":
        df_a_filtered = df_a_filtered[df_a_filtered['CondPgto'].notna() & (df_a_filtered['CondPgto'] != '')]

    mask_inad = pd.Series(False, index=df_a_filtered.index)
    sel_inad = False
    if "Inadimplentes (>3dd)" in f_inad_tipo: mask_inad |= (df_a_filtered['Inad-3dd'] > 0); sel_inad=True
    if "Adimplentes" in f_inad_tipo: mask_inad |= (df_a_filtered['Inad-3dd'] == 0); sel_inad=True
    if "Com Crédito (Negativo)" in f_inad_tipo: mask_inad |= (df_a_filtered['Inad-3dd'] < 0); sel_inad=True
    if sel_inad: df_a_filtered = df_a_filtered[mask_inad]

    if f_dias_sem_compra > 0:
        today = pd.Timestamp.now()
        dt_ult_ped_safe = pd.to_datetime(df_a_filtered['DtUltPed'], errors='coerce')
        dias_diff = (today - dt_ult_ped_safe).dt.days.fillna(99999)
        df_a_filtered = df_a_filtered[dias_diff >= f_dias_sem_compra]

    with st.sidebar.expander("📞 CRM e Contatos (Ativos)"):
        f_dt_contato = st.date_input("Data Últ. Contato", value=[])
        op_resp = sorted(list(df_a_filtered['RespUltContato'].dropna().unique()))
        f_resp = st.multiselect("Responsável Contato", op_resp)
        op_result = sorted(list(df_a_filtered['Resultado'].dropna().unique()))
        f_result = st.multiselect("Resultado", op_result)
        op_motivo = sorted(list(df_a_filtered['Motivo'].dropna().unique()))
        f_motivo = st.multiselect("Motivo", op_motivo)
        f_obs_busca = st.text_input("Buscar na OBS")

    if len(f_dt_contato) == 2:
        df_a_filtered = df_a_filtered[(df_a_filtered['UltContato'].dt.date >= f_dt_contato[0]) & (df_a_filtered['UltContato'].dt.date <= f_dt_contato[1])]
    if f_resp: df_a_filtered = df_a_filtered[df_a_filtered['RespUltContato'].isin(f_resp)]
    if f_result: df_a_filtered = df_a_filtered[df_a_filtered['Resultado'].isin(f_result)]
    if f_motivo: df_a_filtered = df_a_filtered[df_a_filtered['Motivo'].isin(f_motivo)]
    if f_obs_busca: df_a_filtered = df_a_filtered[df_a_filtered['OBS'].str.contains(f_obs_busca, case=False, na=False)]

    # =========================================================================
    # LÓGICA DE ROTAS (SAFE)
    # =========================================================================
    df_rotas = df_ativos.copy()
    
    if f_gerencia: df_rotas = df_rotas[df_rotas['Gerencia'].isin(f_gerencia)]
    if f_equipe: df_rotas = df_rotas[df_rotas['Equipe'].isin(f_equipe)]
    if f_prefixo_vend: 
        prefixo_temp = df_rotas['Vendedor'].astype(str).str.split().str[0]
        df_rotas = df_rotas[prefixo_temp.isin(f_prefixo_vend)]
    if f_vendedor_select:
        df_rotas = df_rotas[df_rotas['Vendedor'].isin(f_vendedor_select)]
    if f_municipio: df_rotas = df_rotas[df_rotas['Municipio'].isin(f_municipio)]
    if f_area: df_rotas = df_rotas[df_rotas['AreaVenda'].isin(f_area)]
    
    if not df_rotas.empty:
        df_rotas['Cod_Vend_Str'] = df_rotas['Cod Vend'].apply(normalizar_cod)
        df_rotas['VendUltPed_Str'] = df_rotas['VendUltPed'].apply(normalizar_cod)

        condicao_venda_propria = (df_rotas['OrigemUltPedido'] == 'TARGET MOB') & \
                                 (df_rotas['Cod_Vend_Str'] == df_rotas['VendUltPed_Str'])

        dt_propria = np.where(
            condicao_venda_propria, 
            df_rotas['DtUltPed'], 
            pd.NaT
        )
        df_rotas['DtUltPed_Proprio'] = pd.to_datetime(dt_propria, errors='coerce')
    else:
        df_rotas['DtUltPed_Proprio'] = pd.NaT

    # =========================================================================
    # KPIS E VISUALIZAÇÃO
    # =========================================================================
    total_linhas_ativos = len(df_a_filtered)
    total_clientes_unicos = df_a_filtered['Cod Clien'].nunique()
    qtd_compartilhados = df_a_filtered['IsCompartilhado'].sum()
    qtd_inad = df_a_filtered[df_a_filtered['Inad-3dd'] > 0]['Cod Clien'].nunique()
    data_corte_churn = pd.Timestamp.now() - pd.Timedelta(days=90)
    df_risco = df_a_filtered[(df_a_filtered['DtUltPed'] < data_corte_churn) | (df_a_filtered['DtUltPed'].isna())]
    qtd_churn_risco = df_risco['Cod Clien'].nunique()

    colunas_ativos_ordem = [
        'StatusCarteira', 'Códs. Vendedores', 'DataCadastro', 'Gerencia', 'Equipe', 'Cod Vend', 'Vendedor', 'CNPJ/CPF', 
        'Cod Clien', 'Cliente', 'Segmento', 'AreaVenda', 'Municipio', 'Bairro', 
        'Endereco', 'UF', 'Latitude', 'Longitude', 'Colig', 'Grupo', 'TipoPessoa', 
        'SitCred', 'LimiteTotal', 'CondPgto', 'Inad-3dd', 'DtUltPed', 'VendUltPed', 'OrigemUltPedido', 'UltPed', 
        'UltContato', 'RespUltContato', 'Resultado', 'Motivo', 'OBS', 'E-mail'
    ]
    colunas_inativos_ordem = [
        'Gerencia', 'Equipe', 'Cod Vend', 'Vendedor', 'CNPJ/CPF', 'Cod Clien', 
        'Cliente', 'Segmento', 'Municipio', 'Bairro', 'Endereco', 'UF', 'Colig', 
        'Grupo', 'E-mail'
    ]
    cols_a_finais = [c for c in colunas_ativos_ordem if c in df_a_filtered.columns]
    cols_i_finais = [c for c in colunas_inativos_ordem if c in df_i_filtered.columns]

    st.subheader("📊 Indicadores de Desempenho (KPIs)")
    row1_c1, row1_c2, row1_c3, row1_c4, row1_c5 = st.columns(5)
    row1_c1.metric("Clientes Únicos", format_ptbr(total_clientes_unicos))
    row1_c2.metric("Total Posições (Linhas)", format_ptbr(total_linhas_ativos))
    row1_c3.metric("Compartilhados (Linhas)", format_ptbr(qtd_compartilhados))
    row1_c4.metric("Inadimplentes", format_ptbr(qtd_inad), delta_color="inverse")
    row1_c5.metric("+90 Dias s/ Compra", format_ptbr(qtd_churn_risco), delta_color="inverse")
    
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["Base Ativa", "Base Inativa", "🗺️ Geolocalização", "🚛 Monitoramento de Rotas"])

    with tab1:
        st.subheader("Registros - Clientes Ativos")
        
        excel_data_a = to_excel(df_a_filtered[cols_a_finais])
        st.download_button(label="📥 Baixar Excel Completo (Ativos)", data=excel_data_a, file_name=f"clientes_ativos_demo_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        df_a_view = df_a_filtered if f_mostrar_todos else df_a_filtered.head(500)
        
        if not f_mostrar_todos and total_linhas_ativos > 500:
            st.info(f"💡 Exibindo apenas os **Top 500** registros de {format_ptbr(total_linhas_ativos)} para melhor performance. Use o menu lateral para carregar todos ou baixe o Excel.")
            
        st.dataframe(
            df_a_view[cols_a_finais], 
            use_container_width=True,
            column_config={
                "Cod Clien": st.column_config.NumberColumn("Cod Clien", format="%d"),
                "UltPed": st.column_config.NumberColumn("UltPed", format="%d"),
                "VendUltPed": st.column_config.NumberColumn("VendUltPed", format="%d"),
                "LimiteTotal": st.column_config.NumberColumn("LimiteTotal", format="R$ %.2f"),
                "Inad-3dd": st.column_config.NumberColumn("Inad-3dd", format="R$ %.2f"),
                "DataCadastro": st.column_config.DateColumn("DataCadastro", format="DD/MM/YYYY"),
                "DtUltPed": st.column_config.DateColumn("DtUltPed", format="DD/MM/YYYY"),
                "UltContato": st.column_config.DateColumn("UltContato", format="DD/MM/YYYY")
            }
        )
        
        st.subheader("📊 Resumo por Origem de Pedido")
        if not df_a_filtered.empty:
            resumo_origem = df_a_filtered.groupby('OrigemUltPedido')['Cod Clien'].nunique().reset_index()
            resumo_origem.columns = ['Origem', 'Qtd Clientes Únicos']

            qtd_nunca_comprou = df_a_filtered[df_a_filtered['DtUltPed'].isna()]['Cod Clien'].nunique()
            if qtd_nunca_comprou > 0:
                row_nunca = pd.DataFrame({'Origem': ['NUNCA COMPROU'], 'Qtd Clientes Únicos': [qtd_nunca_comprou]})
                resumo_origem = pd.concat([resumo_origem, row_nunca], ignore_index=True)

            total_clientes_resumo = resumo_origem['Qtd Clientes Únicos'].sum()

            if total_clientes_resumo > 0:
                resumo_origem['% do Total'] = (resumo_origem['Qtd Clientes Únicos'] / total_clientes_resumo) * 100
            else:
                resumo_origem['% do Total'] = 0.0

            row_total = pd.DataFrame({
                'Origem': ['TOTAL'],
                'Qtd Clientes Únicos': [total_clientes_resumo],
                '% do Total': [100.0]
            })
            resumo_origem = pd.concat([resumo_origem, row_total], ignore_index=True)

            st.dataframe(
                resumo_origem,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Qtd Clientes Únicos": st.column_config.NumberColumn(format="%d"),
                    "% do Total": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)
                }
            )
        else:
            st.warning("Sem dados para gerar resumo.")
    
    with tab2:
        st.subheader("Registros - Clientes Inativos")
        
        excel_data_i = to_excel(df_i_filtered[cols_i_finais])
        st.download_button(label="📥 Baixar Excel Completo (Inativos)", data=excel_data_i, file_name=f"clientes_inativos_demo_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        tot_ina_pos = len(df_i_filtered)
        tot_ina_uniq = df_i_filtered['Cod Clien'].nunique()
        ci1, ci2, ci3 = st.columns([1, 1, 3])
        ci1.metric("Inativos Únicos (CNPJ)", format_ptbr(tot_ina_uniq))
        ci2.metric("Inativos Posições", format_ptbr(tot_ina_pos))
        
        df_i_view = df_i_filtered if f_mostrar_todos else df_i_filtered.head(500)
        
        if not f_mostrar_todos and tot_ina_pos > 500:
            st.info(f"💡 Exibindo apenas os **Top 500** registros de {format_ptbr(tot_ina_pos)} para melhor performance.")
            
        st.dataframe(
            df_i_view[cols_i_finais], 
            use_container_width=True,
            column_config={
                "Cod Clien": st.column_config.NumberColumn("Cod Clien", format="%d")
            }
        )

    with tab3:
        col_map1, col_map2 = st.columns([1, 4])
        with col_map1:
            st.markdown("### Configuração do Mapa")
            raio_ponto = st.number_input("Raio do Ponto (m)", min_value=10, value=100, step=10)

        with col_map2:
            st.subheader("Mapeamento (Base Ativa)")
            df_map = df_a_filtered.copy()
            
            try:
                df_map['latitude_proc'] = df_map['Latitude']
                df_map['longitude_proc'] = df_map['Longitude']
            except KeyError:
                st.error("Colunas Latitude/Longitude ausentes.")
                st.stop()
            
            df_map['latitude_proc'] = pd.to_numeric(df_map['latitude_proc'], errors='coerce')
            df_map['longitude_proc'] = pd.to_numeric(df_map['longitude_proc'], errors='coerce')
            df_map = df_map.dropna(subset=['latitude_proc', 'longitude_proc'])
            
            if not df_map.empty:
                initial_view_state = pdk.ViewState(
                    latitude=df_map['latitude_proc'].mean(),
                    longitude=df_map['longitude_proc'].mean(),
                    zoom=9, pitch=0
                )
                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_map,
                    get_position='[longitude_proc, latitude_proc]',
                    get_color='[255, 140, 0, 255]',
                    get_radius=raio_ponto,
                    pickable=True, auto_highlight=True 
                )
                tooltip = {
                    "html": "<b>Cód:</b> {Cod Clien} <br/><b>Cliente:</b> {Cliente} <br/><b>Município:</b> {Municipio} <br/><b>Bairro:</b> {Bairro} <br/><b>Vendedor:</b> {Vendedor}",
                    "style": {"backgroundColor": "steelblue", "color": "white", "fontSize": "13px", "padding": "10px", "borderRadius": "5px"}
                }
                st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=initial_view_state, tooltip=tooltip, map_style=None))
                st.caption(f"Exibindo {len(df_map)} clientes no mapa.")
            else:
                st.warning("Não há clientes com coordenadas válidas nos filtros selecionados.")

    with tab4:
        st.subheader("🚛 Monitoramento de Cobertura e Ociosidade (Rotas)")
        
        lista_gerencias = sorted(df_rotas['Gerencia'].dropna().unique())
        padrao_desejado = ['GER INTERNO', 'MBR GER INT', 'MGR GER FARMA VET', 'PET GER ESTRAT', 'SOR GER INTERNO', 'GER DIGITAL']
        padrao_exclusao = [g for g in padrao_desejado if g in lista_gerencias]
        
        gerencias_ignorar = st.multiselect(
            "Ignorar Gerências nesta análise (Vendas não contabilizadas):",
            options=lista_gerencias,
            default=padrao_exclusao
        )
        
        if gerencias_ignorar:
            df_rotas_analise = df_rotas[~df_rotas['Gerencia'].isin(gerencias_ignorar)].copy()
        else:
            df_rotas_analise = df_rotas.copy()

        if not df_rotas_analise.empty:
            df_rotas_agg = df_rotas_analise.groupby(['Cod Vend', 'Vendedor']).agg(
                Gerencia=('Gerencia', 'first'),
                Equipe=('Equipe', 'first'),
                Qtd_Clientes=('Cod Clien', 'nunique'),
                Qtd_Compartilhados=('IsCompartilhado', 'sum'),
                Ultima_Venda_Propria=('DtUltPed_Proprio', 'max'),
                Bases_Cruzadas=('Códs. Vendedores', lambda x: x.unique().tolist()) 
            ).reset_index()
            
            def limpar_cruzamento_rota(lista_strings, vendedor_atual):
                vendedor_atual = str(vendedor_atual).replace('.0', '').strip()
                codigos_unicos = set()
                for s in lista_strings:
                    if s:
                        partes = [p.strip() for p in s.split(',')]
                        codigos_unicos.update(partes)
                if vendedor_atual in codigos_unicos:
                    codigos_unicos.remove(vendedor_atual)
                return ', '.join(sorted(codigos_unicos))

            df_rotas_agg['Bases_Cruzadas'] = df_rotas_agg.apply(lambda row: limpar_cruzamento_rota(row['Bases_Cruzadas'], row['Cod Vend']), axis=1)

            today = pd.Timestamp.now().normalize()
            last_sale_safe = pd.to_datetime(df_rotas_agg['Ultima_Venda_Propria'])
            df_rotas_agg['Dias_Sem_Venda'] = (today - last_sale_safe).dt.days.fillna(9999)
            df_rotas_agg['Pct_Compartilhada'] = (df_rotas_agg['Qtd_Compartilhados'] / df_rotas_agg['Qtd_Clientes'] * 100).round(1)

            col_r1, col_r2 = st.columns([1, 3])
            dias_corte = col_r1.number_input("Dias sem venda PRÓPRIA para considerar PARADA:", value=5, min_value=1)
            df_rotas_agg['Status'] = df_rotas_agg.apply(lambda row: definir_status_rota(row, dias_corte), axis=1)
            
            filtro_status = col_r2.multiselect("Filtrar Status da Rota", 
                                               options=['🔴 VAGA (Nome)', '🟠 PARADA (S/ Venda Própria)', '🟢 ATIVA'],
                                               default=['🔴 VAGA (Nome)', '🟠 PARADA (S/ Venda Própria)'])
            
            if filtro_status:
                df_rotas_view = df_rotas_agg[df_rotas_agg['Status'].isin(filtro_status)]
            else:
                df_rotas_view = df_rotas_agg

            df_rotas_view = df_rotas_view.sort_values(by=['Dias_Sem_Venda'], ascending=False)
            df_rotas_view['Dias_Sem_Venda'] = df_rotas_view['Dias_Sem_Venda'].replace(9999, None)
            
            excel_data_r = to_excel(df_rotas_view)
            st.download_button(label="📥 Baixar Excel Completo (Rotas)", data=excel_data_r, file_name=f"analise_rotas_demo_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            st.dataframe(
                df_rotas_view[['Status', 'Cod Vend', 'Vendedor', 'Gerencia', 'Equipe', 'Qtd_Clientes', 'Qtd_Compartilhados', 'Pct_Compartilhada', 'Bases_Cruzadas', 'Ultima_Venda_Propria', 'Dias_Sem_Venda']],
                use_container_width=True,
                column_config={
                    "Ultima_Venda_Propria": st.column_config.DateColumn("Últ. Venda (Dono)", format="DD/MM/YYYY"),
                    "Qtd_Clientes": st.column_config.NumberColumn("Total Clientes"),
                    "Pct_Compartilhada": st.column_config.ProgressColumn("% Compart.", format="%.1f%%", min_value=0, max_value=100),
                    "Bases_Cruzadas": st.column_config.TextColumn("Bases Cruzadas")
                }
            )
        else:
            st.warning("Nenhuma rota encontrada com os filtros selecionados.")

except Exception as e:
    st.error("Ocorreu um erro na execução.")
    st.error(f"Detalhes: {e}")
