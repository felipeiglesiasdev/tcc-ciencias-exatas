import csv
import os
from connection_standard import create_connection, close_connection

# --------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# --------------------------------------------------------

DATASET_DIR = os.path.join(os.getcwd(), "datasets")

# Dicionário com as tabelas e os respectivos caminhos CSV
REFERENCE_TABLES = {
    "cnaes": os.path.join(DATASET_DIR, "cnaes", "cnaes.csv"),
    "naturezas_juridicas": os.path.join(DATASET_DIR, "naturezas", "naturezas.csv"),
    "municipios": os.path.join(DATASET_DIR, "municipios", "naturezass.csv"),
    "paises": os.path.join(DATASET_DIR, "paises", "paises.csv"),
    "qualificacoes_socios": os.path.join(DATASET_DIR, "qualificacoes", "qualificacoes.csv"),
    "empresas": os.path.join(DATASET_DIR, "empresas", "empresas.csv"),
}

CSV_DELIMITER = ";"  # Padrão do governo
CSV_ENCODING = "latin-1"  # Padrão comum nos datasets do CNPJ


# --------------------------------------------------------
# FUNÇÃO GENÉRICA DE INSERÇÃO LINHA A LINHA
# --------------------------------------------------------
TABLE_COLUMNS = {
    "cnaes": ["codigo", "descricao"],
    "naturezas_juridicas": ["codigo", "descricao"],
    "municipios": ["codigo", "descricao"],
    "paises": ["codigo", "descricao"],
    "qualificacoes_socios": ["codigo", "descricao"],
    "empresas": ["cnpj_basico", "razao_social", "natureza_juridica", "qualificacao_responsavel", "capital_social", "porte_empresa", "ente_federativo_responsavel"],
}


def insert_csv_line_by_line(table_name: str, csv_path: str):
    """
    Lê um CSV e insere cada linha individualmente na tabela informada.
    Faz commit a cada linha (modo mais lento, mas seguro).
    """
    conn = None
    cursor = None
    total = 0
    errors = 0

    print(f"\n[INFO] Iniciando inserção linha a linha da tabela '{table_name}'...")
    print(f"[INFO] Arquivo: {csv_path}")

    if not os.path.exists(csv_path):
        print(f"[ERRO] Arquivo CSV não encontrado: {csv_path}")
        return

    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Pega colunas da tabela mapeada
        headers = TABLE_COLUMNS.get(table_name)
        if not headers:
            print(f"[ERRO] Tabela '{table_name}' não está mapeada em TABLE_COLUMNS.")
            return

        placeholders = ", ".join(["%s"] * len(headers))
        columns = ", ".join(headers)
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        print(f"[INFO] Colunas usadas: {headers}")

        with open(csv_path, "r", encoding=CSV_ENCODING, newline="", errors="replace") as csvfile:
            reader = csv.reader(csvfile, delimiter=CSV_DELIMITER)
            for i, row in enumerate(reader, start=1):
                try:
                    cursor.execute(sql, row)
                    conn.commit()
                    total += 1
                except Exception as e:
                    errors += 1
                    print(f"[ERRO] Linha {i}: {e}")

                if i % 1000 == 0:
                    print(f"[INFO] {i} linhas processadas. ({errors} erros)")

        print(f"[DONE] Tabela '{table_name}': {total} linhas inseridas, {errors} erros.\n")

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            close_connection(conn)


# --------------------------------------------------------
# EXECUÇÃO PRINCIPAL
# --------------------------------------------------------

if __name__ == "__main__":
    print("\n========== INSERÇÃO DAS TABELAS DE REFERÊNCIA ==========\n")

    for table, csv_path in REFERENCE_TABLES.items():
        insert_csv_line_by_line(table, csv_path)

    print("\n========== INSERÇÃO FINALIZADA ==========\n")
