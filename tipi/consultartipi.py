import sqlite3

def consultar_ncm(ncm_codigo, db_file='tipi.db', original_ncm=None):
    """
    Consulta a alíquota de um NCM no banco de dados SQLite.
    Normaliza o NCM para o formato XXXX.XX.XX e, se não encontrar,
    busca o NCM "pai" recursivamente.
    """
    # Normaliza o código NCM para garantir que esteja no formato com pontos
    ncm_digits = ''.join(filter(str.isdigit, str(ncm_codigo)))
    
    # A lógica de busca recursiva depende do formato com pontos.
    # Formatamos o NCM de 8 dígitos. Códigos menores (pais) já estarão 
    # no formato correto nas chamadas recursivas subsequentes.
    if len(ncm_digits) == 8:
        ncm_formatado = f"{ncm_digits[:4]}.{ncm_digits[4:6]}.{ncm_digits[6:]}"
    else:
        ncm_formatado = ncm_codigo

    if original_ncm is None:
        original_ncm = ncm_formatado # Armazena o NCM formatado para referência

    conn = None
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # A chave de busca é 'NCM|EX'. Para um NCM principal, o EX é ''.
        ncm_ex_key = f"{ncm_formatado}|"
        
        query = "SELECT ncm, descricao, aliquota, ex FROM tipi WHERE ncm_ex = ?"
        cursor.execute(query, (ncm_ex_key,))
        resultado = cursor.fetchone()

        if resultado:
            return {
                "ncm_consultado": original_ncm,
                "ncm_encontrado": resultado[0],
                "descricao": resultado[1],
                "aliquota": resultado[2],
                "ex": resultado[3]
            }
        else:
            # Se não encontrou, tenta buscar o NCM "pai"
            if '.' in ncm_formatado:
                ncm_pai = ncm_formatado.rsplit('.', 1)[0]
                return consultar_ncm(ncm_pai, db_file, original_ncm)
            else:
                return None

    except sqlite3.Error as e:
        print(f"Erro ao consultar o SQLite: {e}")
        return None
    finally:
        if conn:
            conn.close()