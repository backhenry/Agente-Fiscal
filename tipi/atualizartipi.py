import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import pandas as pd
import sqlite3
import os

def baixar_tipi_xlsx(output_filename="tipi_download.xlsx"):
    """
    Realiza o web scraping da página da Receita Federal para baixar
    o arquivo XLSX da TIPI, procurando pelo link do arquivo.
    """
    
    page_url = "https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/legislacao/tipi-tabela-de-incidencia-do-imposto-sobre-produtos-industrializados"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Acessando a página: {page_url}")
        response = requests.get(page_url, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        print("Procurando por um link de download do arquivo XLSX da TIPI...")
        
        link_tag = soup.find('a', href=re.compile(r"tipi.*\.xlsx", re.IGNORECASE))
        
        if not link_tag:
            print("Tentativa 1 falhou. Tentativa 2: Procurando por qualquer link que termine com '.xlsx'...")
            link_tag = soup.find('a', href=re.compile(r"\.xlsx$", re.IGNORECASE))

        if not link_tag:
            print("Erro: Não foi possível encontrar o link para o arquivo XLSX.")
            return None

        file_href = link_tag.get('href')
        absolute_file_url = urljoin(page_url, file_href)
        
        print(f"Link encontrado: {absolute_file_url}")

        print(f"Baixando o arquivo como '{output_filename}'...")
        file_response = requests.get(absolute_file_url, headers=headers, timeout=60)
        file_response.raise_for_status()

        with open(output_filename, 'wb') as f:
            f.write(file_response.content)

        print(f"Sucesso! O arquivo foi salvo como '{output_filename}'")
        return output_filename

    except requests.exceptions.Timeout:
        print("Erro: A requisição demorou muito para responder (timeout).")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Ocorreu um erro de rede ou HTTP durante o download: {e}")
        return None
    except Exception as e:
        print(f"Ocorreu um erro inesperado durante o download: {e}")
        return None

def processar_tipi_para_sqlite(excel_file, db_file="tipi.db", table_name='tipi'):
    """
    Lê o arquivo XLSX da TIPI, limpa os dados e salva em SQLite.
    (Versão com tratamento de erro de nome de coluna)
    """
    print(f"\nIniciando o processamento do arquivo: {excel_file}")

    try:
        # --- 1. Encontrar a linha do cabeçalho ---
        df_header_find = pd.read_excel(excel_file, nrows=20, header=None)
        header_row = -1
        for i, row in df_header_find.iterrows():
            if any(str(cell).strip() == 'NCM' for cell in row):
                header_row = i
                break
        if header_row == -1:
            print("Erro: Não foi possível encontrar a linha de cabeçalho 'NCM'.")
            return
        print(f"Cabeçalho 'NCM' encontrado na linha {header_row}.")

        # --- 2. Ler os dados reais ---
        # Lê o excel a partir da linha de cabeçalho correta
        df = pd.read_excel(excel_file, header=header_row)
        
        print(f"Colunas originais encontradas: {list(df.columns)}")

        # --- 3. Limpar e Renomear Colunas (MÉTODO CORRIGIDO) ---
        # Limpa espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()
        
        # Mapeamento robusto (procura por nomes que *contenham* o texto)
        rename_map = {}
        for col in df.columns:
            col_upper = str(col).upper()
            if 'NCM' in col_upper:
                rename_map[col] = 'ncm'
            elif 'DESCRIÇÃO' in col_upper: # 'DESCRIÇÃO' ou 'DESCRIÇAO'
                rename_map[col] = 'descricao'
            elif 'EX' == col_upper: # 'EX' é curto, melhor ser exato
                rename_map[col] = 'ex'
            elif 'ALÍQUOTA' in col_upper: # 'ALÍQUOTA (%)'
                rename_map[col] = 'aliquota'
        
        df = df.rename(columns=rename_map)

        # --- 4. Verificação pós-renomeação ---
        required_cols = ['ncm', 'descricao', 'aliquota']
        if not all(col in df.columns for col in required_cols):
            print(f"Erro: Falha ao renomear colunas. Colunas necessárias não encontradas.")
            print(f"Colunas encontradas após tentativa de renomear: {list(df.columns)}")
            print(f"Colunas necessárias: {required_cols}")
            return

        # --- 5. Limpar os Dados ---
        # Agora podemos aplicar os tipos e limpar os dados
        df['ncm'] = df['ncm'].astype(str).str.strip()
        df['descricao'] = df['descricao'].astype(str)
        df['aliquota'] = df['aliquota'].fillna('').astype(str).str.strip()
        
        if 'ex' in df.columns:
            df['ex'] = df['ex'].fillna('').astype(str).str.strip()
        else:
            df['ex'] = '' # Cria a coluna 'ex' vazia se ela não existir

        # Remove linhas onde ncm ou descricao são nulos
        df = df.dropna(subset=['ncm', 'descricao'])

        # Filtra apenas linhas que parecem ser NCMs (remove títulos de seção)
        df = df[df['ncm'].str.match(r'^\d{2,4}(\.\d{2}(\.\d{2})?(\.\d{2})?)?$')]

        print(f"Dados processados. Total de {len(df)} registros NCM válidos encontrados.")

        # --- 6. Salvar em Banco de Dados SQLite ---
        print(f"Salvando em banco de dados SQLite '{db_file}'...")
        conn = sqlite3.connect(db_file)
        
        df['ncm_ex'] = df['ncm'] + '|' + df['ex']
        
        # Reordenar colunas para garantir 'ncm_ex' primeiro
        cols_to_save = ['ncm_ex', 'ncm', 'ex', 'descricao', 'aliquota']
        final_df = df[[col for col in cols_to_save if col in df.columns]]

        final_df.to_sql(table_name, conn, if_exists='replace', index=False, dtype={
            'ncm_ex': 'TEXT PRIMARY KEY',
            'ncm': 'TEXT',
            'ex': 'TEXT',
            'descricao': 'TEXT',
            'aliquota': 'TEXT'
        })
        conn.close()
        print(f"Banco de dados SQLite salvo com sucesso na tabela '{table_name}'.")

    except FileNotFoundError:
        print(f"Erro: Arquivo '{excel_file}' não encontrado.")
    except KeyError as e:
        print(f"Erro de Chave (KeyError): {e}. Isso indica que uma coluna esperada não foi encontrada.")
        if 'df' in locals():
            print(f"Colunas disponíveis no DataFrame: {list(df.columns)}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado durante o processamento: {e}")

# --- Execução Principal ---
if __name__ == "__main__":
    
    arquivo_excel_baixado = baixar_tipi_xlsx(output_filename="tipi_download.xlsx")
    
    if arquivo_excel_baixado and os.path.exists(arquivo_excel_baixado):
        processar_tipi_para_sqlite(arquivo_excel_baixado, db_file="tipi.db")
    else:
        print("Processamento falhou, pois o download não foi concluído.")