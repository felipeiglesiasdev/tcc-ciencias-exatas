# ARQUIVO PARA ESTABELECER UMA CONEXÃO PADRÃO COM O MYSQL
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os


load_dotenv()
def create_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "cnpj"),
            charset="utf8mb4",
            use_unicode=True
        )

        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"[INFO] Conectado ao servidor MySQL versão {db_info}")
            print(f"[INFO] Banco de dados ativo: {os.getenv('DB_NAME', 'cnpj')}")
            return connection
    except Error as e:
        print(f"[ERRO] Falha ao conectar ao MySQL: {e}")
        raise e


def close_connection(connection, cursor=None):
    try:
        if cursor is not None:
            try:
                cursor.close()
            except Exception as e:
                print(f"[WARN] Erro ao fechar cursor: {e}")

        # Fecha a conexão
        if connection is not None and connection.is_connected():
            connection.close()
            print("[INFO] Conexão MySQL encerrada com sucesso.")
    except Error as e:
        print(f"[ERRO] Falha ao encerrar a conexão: {e}")


if __name__ == "__main__":
    conn = None
    cursor = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()[0]
        print(f"[INFO] Conectado ao banco: {db_name}")
    finally:
        close_connection(conn, cursor)
