import pandas as pd
import sqlite3
import re

def processar_tipi_excel(excel_file, json_file, db_file, table_name='tipi'):
    """
    Lê o arquivo XLSX da TIPI, limpa os dados e salva em JSON e SQLite.
    """
    print(f"Iniciando o processamento do arquivo: {excel_file}")

    try:
        # --- 1. Encontrar a linha do cabeçalho ---
        # O arquivo da TIPI tem várias linhas de metadados antes da tabela real.
        # Vamos ler as primeiras 20 linhas para encontrar o cabeçalho "NCM".
        df_header_find = pd.read_excel(excel_file, nrows=20, header=None)
        
        header_row = -1
        for i, row in df_header_find.iterrows():
            # Procura pela célula que contém "NCM" (limpando espaços)
            if any(str(cell).strip() == 'NCM' for cell in row):
                header_row = i
                break

        if header_row == -1:
            print("Erro: Não foi possível encontrar a linha de cabeçalho 'NCM'.")
            return

        print(f"Cabeçalho 'NCM' encontrado na linha {header_row}.")

        # --- 2. Ler os dados reais ---
        # Define os tipos de dados na leitura para evitar problemas com NCM
        dtype_map = {
            'NCM': str,
            'EX': str,
            'DESCRIÇÃO': str,
            'ALÍQUOTA (%)': str  # Ler como string para manter "NT"
        }
        
        df = pd.read_excel(excel_file, header=header_row, dtype=dtype_map)

        # --- 3. Limpar os dados ---
        # Renomear colunas para facilitar o acesso
        df = df.rename(columns={
            'NCM': 'ncm',
            'EX': 'ex',
            'DESCRIÇÃO': 'descricao',
            'ALÍQUOTA (%)': 'aliquota'
        })

        # Remover linhas onde 'ncm' ou 'descricao' são nulos (linhas de capítulo, etc.)
        df = df.dropna(subset=['ncm', 'descricao'])
        
        # Preencher 'ex' e 'aliquota' nulos com string vazia
        df['ex'] = df['ex'].fillna('')
        df['aliquota'] = df['aliquota'].fillna('').astype(str).str.strip()
        df['ncm'] = df['ncm'].str.strip()
        
        # Filtra apenas linhas que parecem ser NCMs completos (ex: 8 ou 10 dígitos com pontos)
        # Isso ajuda a remover linhas de Título de Seção/Capítulo
        df = df[df['ncm'].str.match(r'^\d{2,4}\.\d{2}(\.\d{2})?(\.\d{2})?$')]

        print(f"Dados processados. Total de {len(df)} registros NCM válidos encontrados.")

        # --- 4. Salvar em JSON ---
        print(f"Salvando em {json_file}...")
        df.to_json(json_file, orient='records', indent=4, force_ascii=False)
        print("Arquivo JSON salvo com sucesso.")

        # --- 5. Salvar em Banco de Dados SQLite ---
        print(f"Salvando em banco de dados SQLite '{db_file}'...")
        conn = sqlite3.connect(db_file)
        
        # Salva o DataFrame na tabela, substituindo se já existir
        df.to_sql(table_name, conn, if_exists='replace', index=False, dtype={
            'ncm': 'TEXT PRIMARY KEY', # Definir NCM como chave primária é uma boa prática
            'ex': 'TEXT',
            'descricao': 'TEXT',
            'aliquota': 'TEXT'
        })
        conn.close()
        print(f"Banco de dados SQLite salvo com sucesso na tabela '{table_name}'.")

    except FileNotFoundError:
        print(f"Erro: Arquivo '{excel_file}' não encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

# --- Execução do Script ---
if __name__ == "__main__":
    processar_tipi_excel(
        excel_file='tipi_download.xlsx', 
        json_file='tipi_data.json',
        db_file='tipi.db'
    )