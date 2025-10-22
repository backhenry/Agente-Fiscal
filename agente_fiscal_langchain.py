# Arquivo: agente_fiscal_langchain.py (Versão Final Multimodal)

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate
from ferramentas_fiscais import (
    extrair_dados_xml, 
    extrair_dados_pdf, 
    auditar_dados_fiscais, 
    classificar_documento, # Importa a ferramenta de classificação
    salvar_dados_no_banco  # Importa a ferramenta de salvamento
)

# Carregamento da chave de API do arquivo .env
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("A variável de ambiente OPENAI_API_KEY não foi encontrada.")

# 1. Configuração do LLM
llm = ChatOpenAI(api_key=openai_api_key, model="gpt-4-turbo", temperature=0)


# 2. Lista de Ferramentas - Agora com a ferramenta de classificação e salvamento!
tools = [extrair_dados_xml, extrair_dados_pdf, auditar_dados_fiscais, classificar_documento, salvar_dados_no_banco]

# 3. Prompt Aprimorado - Ensinando o agente a salvar os dados
prompt_template = """
Você é um assistente fiscal especialista. Sua função é processar, analisar e armazenar documentos fiscais.

Use as seguintes regras para decidir qual ferramenta usar:
1.  Analise a tarefa do usuário para identificar o nome do arquivo.
2.  **FLUXO DE PROCESSAMENTO OBRIGATÓRIO:** Você deve executar as ferramentas na seguinte ordem exata:
    a. **Extração**: Use `extrair_dados_xml` ou `extrair_dados_pdf` com base na extensão do arquivo.
    b. **Auditoria**: Use `auditar_dados_fiscais`.
    c. **Classificação**: Use `classificar_documento`.
    d. **Salvamento**: Use `salvar_dados_no_banco`.

3.  **REGRA DE OURO PARA PASSAGEM DE DADOS**: O resultado de uma ferramenta é uma string JSON. Você DEVE passar essa string JSON **COMPLETA E SEM MODIFICAÇÕES** como o argumento para a ferramenta seguinte na cadeia. Por exemplo, o output completo de `auditar_dados_fiscais` deve ser o input de `classificar_documento`. NÃO tente extrair ou manipular o JSON entre as etapas.

4.  **Finalização**: Após a ferramenta `salvar_dados_no_banco` ser executada, sua tarefa está concluída. Apresente o resultado final da última ferramenta executada de forma clara para o usuário.

**Exemplo de Raciocínio Correto:**
1.  Chamo `extrair_dados_xml` e recebo o JSON '{{"tipo_documento": ...}}'.
2.  Pego essa string JSON inteira e chamo `auditar_dados_fiscais` com ela. Recebo '{{"status": "OK", "dados_fiscais": ...}}'.
3.  Pego essa nova string JSON inteira e chamo `classificar_documento` com ela. Recebo '{{"status": "OK", "dados_fiscais": {{"classificacao": ...}}}}'.
4.  Pego essa última string JSON inteira e chamo `salvar_dados_no_banco` com ela.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", prompt_template),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# 4. Criação do Agente
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 5. Execução (Invocando o Agente)
if __name__ == "__main__":
    print("--- Agente Fiscal LangChain Multimodal Pronto ---")
    print("Exemplos de tarefas: 'Processe o arquivo nfe.xml' ou 'Analise o documento nota_exemplo.pdf'")
    
    # Tarefa dinâmica - você pode mudar a string para testar
    tarefa = "Extraia as informações e audite o documento fiscal que está no arquivo 'nota_exemplo.pdf'"
    # tarefa = "Processe e audite a nota fiscal que está no arquivo 'nfe.xml'" # Descomente para testar o XML
    
    print(f"\nTarefa recebida: '{tarefa}'")
    
    resultado = agent_executor.invoke({"input": tarefa})
    
    print("\n--- ✅ Resposta Final do Agente ---")
    print(resultado["output"])