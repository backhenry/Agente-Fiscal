# Arquivo: app.py (Versão com Dashboard)

import streamlit as st
import os
import pandas as pd
import json
from agente_fiscal_langchain import agent_executor
# Importamos a ferramenta de leitura diretamente para o dashboard
from ferramentas_fiscais import ler_registros_do_banco

# --- Configuração da Página ---
st.set_page_config(page_title="Agente Fiscal Inteligente", page_icon="🤖", layout="wide")

st.title("🤖 Agente Fiscal Inteligente")
st.caption("Uma solução de IA para automatizar a análise e o gerenciamento de documentos fiscais.")

# --- ABAS DA APLICAÇÃO ---
tab_processamento, tab_dashboard = st.tabs(["Processar Novo Documento", "Dashboard de Documentos"])


# --- ABA 1: PROCESSAMENTO DE DOCUMENTOS ---
with tab_processamento:
    st.header("Análise de Documento Individual")
    uploaded_file = st.file_uploader("Selecione o documento fiscal (XML ou PDF)", type=['xml', 'pdf'])

    if uploaded_file is not None:
        temp_dir = "temp_uploads"
        if not os.path.exists(temp_dir): os.makedirs(temp_dir)
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())

        if st.button("Analisar Documento", type="primary", use_container_width=True):
            tarefa = f"Extraia, audite e salve no banco de dados o documento fiscal '{file_path}'"
            with st.spinner('O Agente está trabalhando...'):
                try:
                    resultado = agent_executor.invoke({"input": tarefa})
                    st.subheader("✅ Análise Concluída")
                    st.markdown(resultado["output"])
                    with st.expander("Ver o raciocínio detalhado do Agente"):
                        st.json(resultado)
                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")

# --- ABA 2: DASHBOARD ---
with tab_dashboard:
    st.header("Documentos Fiscais Processados")
    
    # Botão para recarregar os dados do banco
    if st.button("Atualizar Dados", use_container_width=True):
        st.cache_data.clear() # Limpa o cache para garantir dados novos

    @st.cache_data(ttl=60) # Cache para não ler o banco a cada interação
    def carregar_dados():
        dados_json = ler_registros_do_banco.invoke({}) # Chama a ferramenta
        return json.loads(dados_json)

    dados = carregar_dados()

    if isinstance(dados, list) and dados:
        df = pd.DataFrame(dados)
        st.dataframe(df, use_container_width=True)
        
        # Gráficos simples
        st.subheader("Análises Rápidas")
        col1, col2 = st.columns(2)
        with col1:
            st.write("Total por Tipo de Documento")
            tipo_counts = df['tipo_documento'].value_counts()
            st.bar_chart(tipo_counts)
        with col2:
            st.write("Valor Total por Tipo")
            valor_por_tipo = df.groupby('tipo_documento')['valor_total'].sum()
            st.bar_chart(valor_por_tipo)

    elif isinstance(dados, dict) and 'erro' in dados:
        st.error(f"Erro ao carregar dados do banco: {dados['erro']}")
    else:
        st.info("Nenhum documento processado ainda. Processe um documento na aba ao lado.")