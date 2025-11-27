# =====================================================================
# ARQUIVO: insert_batch_all.py
# OBJETIVO: INSERÇÃO EM LOTES ROBUSTA (500 LINHAS)
# COMPARAÇÃO COM LINE-BY-LINE E LOAD DATA
# RELATÓRIO PDF E MONITORAMENTO COMPLETO
# AUTOR: FELIPE IGLESIAS (TCC CIÊNCIAS EXATAS - 2025)
# =====================================================================

import os
import csv
import time
import psutil
from threading import Thread
from dotenv import load_dotenv

# PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.pagesizes import landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# CONEXÃO PADRÃO (MYSQL)
from connection_standard import create_connection, close_connection

# =====================================================================
# CARREGAR VARIÁVEIS DO .ENV
# =====================================================================
load_dotenv()

# =====================================================================
# CONFIGURAÇÕES GERAIS
# =====================================================================
DATASET_DIR = os.path.join(os.getcwd(), "datasets")

CSV_DELIMITER = ";"
CSV_ENCODING = "latin-1"

# TAMANHO DO LOTE (fixo 500)
BATCH_SIZE = 500

# DADOS PARA RELATÓRIO FINAL
REPORT_DATA = {}

# FLAG PARA ENCERRAR MONITORAMENTO
STOP_MONITORING = False

# =====================================================================
# MAPEAMENTO DE PASTAS POR TABELA
# =====================================================================
REFERENCE_TABLES = {
    "cnaes": os.path.join(DATASET_DIR, "cnaes"),
    "naturezas_juridicas": os.path.join(DATASET_DIR, "naturezas"),
    "municipios": os.path.join(DATASET_DIR, "municipios"),
    "paises": os.path.join(DATASET_DIR, "paises"),
    "qualificacoes_socios": os.path.join(DATASET_DIR, "qualificacoes"),
    "empresas": os.path.join(DATASET_DIR, "empresas"),
    #"estabelecimentos": os.path.join(DATASET_DIR, "estabelecimentos"),
    #"socios": os.path.join(DATASET_DIR, "socios"),
    #"simples": os.path.join(DATASET_DIR, "simples"),
}

# =====================================================================
# COLUNAS DE CADA TABELA
# =====================================================================
TABLE_COLUMNS = {
    "cnaes": ["codigo", "descricao"],
    "naturezas_juridicas": ["codigo", "descricao"],
    "municipios": ["codigo", "descricao"],
    "paises": ["codigo", "descricao"],
    "qualificacoes_socios": ["codigo", "descricao"],

    "empresas": [
        "cnpj_basico", "razao_social", "natureza_juridica",
        "qualificacao_responsavel", "capital_social",
        "porte_empresa", "ente_federativo_responsavel"
    ],

    "estabelecimentos": [
        "cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador_matriz_filial",
        "nome_fantasia", "situacao_cadastral", "data_situacao_cadastral",
        "motivo_situacao_cadastral", "nome_cidade_exterior", "pais",
        "data_inicio_atividade", "cnae_fiscal_principal",
        "cnae_fiscal_secundaria", "tipo_logradouro", "logradouro",
        "numero", "complemento", "bairro", "cep", "uf", "municipio",
        "ddd1", "telefone1", "ddd2", "telefone2",
        "ddd_fax", "fax", "correio_eletronico",
        "situacao_especial", "data_situacao_especial"
    ],

    "socios": [
        "cnpj_basico", "identificador_socio", "nome_socio",
        "cnpj_cpf_socio", "qualificacao_socio", "data_entrada_sociedade",
        "pais", "representante_legal", "nome_representante",
        "qualificacao_representante_legal", "faixa_etaria"
    ],

    "simples": [
        "cnpj_basico", "opcao_pelo_simples", "data_opcao_pelo_simples",
        "data_exclusao_do_simples", "opcao_pelo_mei",
        "data_opcao_pelo_mei", "data_exclusao_do_mei"
    ],
}

# =====================================================================
# MONITORAMENTO CPU/RAM/DISCO
# =====================================================================
def monitor_system(metrics_list):
    """
    MONITORA CPU, RAM E DISCO A CADA 0.1s.
    A primeira leitura de cpu_percent SEMPRE é 0, então ignoramos ela.
    """

    global STOP_MONITORING
    process = psutil.Process(os.getpid())

    psutil.cpu_percent(interval=None)  # ignora primeira leitura

    while not STOP_MONITORING:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = process.memory_info().rss / (1024 * 1024)  # MB
        disk = psutil.disk_io_counters()

        metrics_list.append({
            "timestamp": time.time(),
            "cpu": cpu,
            "ram": ram,
            "read": disk.read_bytes,
            "write": disk.write_bytes
        })


# =====================================================================
# FUNÇÃO: INSERIR EM LOTES (ROBUSTO)
# =====================================================================
def insert_batch_for_table(table_name, folder_path):
    """
    INSERE EM LOTES DE 500 LINHAS COM FILTRAGEM ROBUSTA:
    - Remove linhas inválidas antes de entrar no lote
    - Evita perda de 500 registros por causa de 1 erro
    - Executemany() só recebe lotes válidos
    - Performance MUITO superior ao line-by-line
    """

    global STOP_MONITORING

    print(f"\n=====================================================================")
    print(f"[INÍCIO - BATCH ROBUSTO] TABELA: {table_name.upper()}")
    print("=====================================================================\n")

    # -----------------------------------------------------------------
    # Verifica se a pasta existe
    # -----------------------------------------------------------------
    if not os.path.isdir(folder_path):
        print(f"[ERRO] Pasta não existe: {folder_path}")
        return

    files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(".csv")])
    print(f"[INFO] {len(files)} arquivos CSV encontrados para {table_name}\n")

    # -----------------------------------------------------------------
    # Contar total de linhas — ETA
    # -----------------------------------------------------------------
    print(f"[{table_name.upper()}] Contando total de linhas...")

    total_linhas_tabela = 0
    for f_csv in files:
        with open(os.path.join(folder_path, f_csv), "r", encoding=CSV_ENCODING, errors="ignore") as f:
            for _ in f:
                total_linhas_tabela += 1

    print(f"[{table_name.upper()}] Total de linhas: {total_linhas_tabela:,}\n")

    # -----------------------------------------------------------------
    # Monitoramento
    # -----------------------------------------------------------------
    metrics_list = []
    STOP_MONITORING = False
    monitor_thread = Thread(target=monitor_system, args=(metrics_list,))
    monitor_thread.start()

    # -----------------------------------------------------------------
    # SQL
    # -----------------------------------------------------------------
    colunas = TABLE_COLUMNS[table_name]
    placeholders = ", ".join(["%s"] * len(colunas))
    colunas_sql = ", ".join(colunas)
    sql_insert = f"INSERT INTO {table_name} ({colunas_sql}) VALUES ({placeholders})"

    # -----------------------------------------------------------------
    # Contadores
    # -----------------------------------------------------------------
    total_inseridas = 0
    total_erros = 0

    # -----------------------------------------------------------------
    # Conexão
    # -----------------------------------------------------------------
    conn = create_connection()
    cursor = conn.cursor()

    inicio = time.time()
    linhas_desde_ultima_medida = 0

    # -----------------------------------------------------------------
    # Sanitizador para as linhas
    # -----------------------------------------------------------------
    def limpar_valor(valor):
        if valor is None:
            return None

        valor = valor.strip()

        # Remove aspas externas opcionais
        if valor.startswith('"') and valor.endswith('"'):
            valor = valor[1:-1]

        # Aspas duplas internas -> aspas únicas
        valor = valor.replace('""', '"')

        # Remove null byte
        valor = valor.replace('\x00', '')

        # vazio vira None
        if valor == "":
            return None

        return valor

    # -----------------------------------------------------------------
    # Processar arquivos CSV
    # -----------------------------------------------------------------
    lote = []

    for f_csv in files:

        caminho = os.path.join(folder_path, f_csv)

        with open(caminho, "r", encoding=CSV_ENCODING, newline="", errors="replace") as f:
            reader = csv.reader(
                f,
                delimiter=CSV_DELIMITER,
                quotechar='"',
                doublequote=True,
                escapechar=None,
                skipinitialspace=False
            )

            for row in reader:

                # ===============================
                # 1) Sanitizar linha inteira
                # ===============================
                try:
                    linha_limpa = [limpar_valor(campo) for campo in row]
                except Exception:
                    total_erros += 1
                    continue

                # ===============================
                # 2) Validar quantidade de colunas
                # ===============================
                if len(linha_limpa) != len(colunas):
                    total_erros += 1
                    continue

                # ===============================
                # 3) Adicionar ao lote
                # ===============================
                lote.append(linha_limpa)

                # ===============================
                # 4) Se lote chegou a 500 → executemany (LOTE LIMPO)
                # ===============================
                if len(lote) >= BATCH_SIZE:

                    try:
                        cursor.executemany(sql_insert, lote)
                        conn.commit()
                        total_inseridas += len(lote)
                        linhas_desde_ultima_medida += len(lote)
                    except Exception:
                        # Se executemany falhar → lote tem linha ruim ainda
                        # Então descarta linha por linha ruim rapidamente
                        for L in lote:
                            try:
                                cursor.execute(sql_insert, L)
                                conn.commit()
                                total_inseridas += 1
                            except Exception:
                                total_erros += 1

                    lote.clear()

                # ----------------------------
                # LOG a cada 10.000 linhas
                # ----------------------------
                if linhas_desde_ultima_medida >= 10000:

                    tempo_decorrido = time.time() - inicio
                    velocidade = total_inseridas / tempo_decorrido if tempo_decorrido > 0 else 0

                    linhas_restantes = total_linhas_tabela - total_inseridas
                    eta_seg = linhas_restantes / velocidade if velocidade > 0 else 0
                    eta_formatado = time.strftime("%H:%M:%S", time.gmtime(eta_seg))

                    print(f"\n[{table_name.upper()} - BATCH ROBUSTO] {total_inseridas:,} linhas processadas")
                    print(f"Tempo decorrido: {tempo_decorrido:.1f}s")
                    print(f"Velocidade média: {velocidade:,.0f} linhas/s")
                    print(f"ETA restante: {eta_formatado}")
                    print(f"Erros acumulados: {total_erros}")

                    cpu_atual = psutil.cpu_percent(interval=0.1)
                    ram_atual = psutil.virtual_memory().used / (1024 * 1024)
                    print(f"CPU atual: {cpu_atual:.0f}%")
                    print(f"RAM atual: {ram_atual:.0f} MB\n")

                    linhas_desde_ultima_medida = 0

    # -----------------------------------------------------------------
    # Inserir lote restante
    # -----------------------------------------------------------------
    if lote:
        try:
            cursor.executemany(sql_insert, lote)
            conn.commit()
            total_inseridas += len(lote)
        except Exception:
            for L in lote:
                try:
                    cursor.execute(sql_insert, L)
                    conn.commit()
                    total_inseridas += 1
                except Exception:
                    total_erros += 1
        lote.clear()

    # -----------------------------------------------------------------
    # Finalizar monitoramento
    # -----------------------------------------------------------------
    STOP_MONITORING = True
    monitor_thread.join()

    tempo_total = time.time() - inicio

    # -----------------------------------------------------------------
    # Registrar no relatório PDF
    # -----------------------------------------------------------------
    REPORT_DATA[table_name] = {
        "linhas": total_inseridas,
        "erros": total_erros,
        "tempo": tempo_total,
        "metricas": metrics_list
    }

    # -----------------------------------------------------------------
    # Log final
    # -----------------------------------------------------------------
    print("\n------------------------------------------------------------")
    print(f"[RESUMO - {table_name.upper()} - BATCH ROBUSTO]")
    print(f"Linhas inseridas: {total_inseridas:,}")
    print(f"Erros: {total_erros}")
    print(f"Tempo total: {tempo_total:.2f} segundos")
    print("------------------------------------------------------------\n")

    close_connection(conn, cursor)


# =====================================================================
# RELATÓRIO PDF (MODO PAISAGEM)
# =====================================================================
from reportlab.lib.pagesizes import landscape

def gerar_relatorio_pdf(output_path="relatorio_insercao_batch.pdf",
                        inicio_execucao=None,
                        fim_execucao=None):
    """
    GERA RELATÓRIO TÉCNICO EM PDF (MODELO PAISAGEM)
    - RESUMO GERAL
    - TABELA DETALHADA POR TABELA
    - CPU MÉDIA
    - RAM MÉDIA
    - DISCO LIDO / ESCRITO
    """

    styles = getSampleStyleSheet()
    story = []

    # --------------------------------------------
    # TÍTULO
    # --------------------------------------------
    story.append(Paragraph("<b>Relatório Técnico — Inserção em Lotes (Batch Robusto)</b>",
                           styles["Title"]))
    story.append(Paragraph("<br/>", styles["BodyText"]))

    # --------------------------------------------
    # RESUMO GERAL
    # --------------------------------------------
    story.append(Paragraph("<b>Resumo Geral</b>", styles["Heading2"]))

    duracao_total = fim_execucao - inicio_execucao
    total_linhas_geral = sum(d["linhas"] for d in REPORT_DATA.values())
    total_erros_geral = sum(d["erros"] for d in REPORT_DATA.values())
    velocidade_geral = total_linhas_geral / duracao_total if duracao_total > 0 else 0

    resumo = [
        ["Início", time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(inicio_execucao))],
        ["Fim", time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(fim_execucao))],
        ["Duração Total", f"{duracao_total:.2f} s"],
        ["Linhas Inseridas", f"{total_linhas_geral:,}"],
        ["Erros Totais", total_erros_geral],
        ["Velocidade Média", f"{velocidade_geral:,.1f} linhas/s"],
    ]

    resumo_table = Table(resumo, colWidths=[200, 350])
    resumo_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    story.append(resumo_table)
    story.append(Paragraph("<br/><br/>", styles["BodyText"]))

    # --------------------------------------------
    # TABELA DETALHADA POR TABELA
    # --------------------------------------------
    story.append(Paragraph("<b>Estatísticas por Tabela</b>", styles["Heading2"]))

    tabela_detalhada = [
        [
            "Tabela",
            "Linhas",
            "Erros",
            "Tempo (s)",
            "Vel. Média",
            "CPU Média (%)",
            "RAM Média (MB)",
            "Disco Escrito (MB)",
            "Disco Lido (MB)"
        ]
    ]

    for tabela, dados in REPORT_DATA.items():

        metricas = dados["metricas"]

        if len(metricas) > 0:
            cpu_media = sum(m["cpu"] for m in metricas) / len(metricas)
            ram_media = sum(m["ram"] for m in metricas) / len(metricas)
            disco_escrito = (metricas[-1]["write"] - metricas[0]["write"]) / (1024 * 1024)
            disco_lido = (metricas[-1]["read"] - metricas[0]["read"]) / (1024 * 1024)
        else:
            cpu_media = ram_media = disco_escrito = disco_lido = 0

        linhas = dados["linhas"]
        tempo = dados["tempo"]
        erros = dados["erros"]
        vel_media = linhas / tempo if tempo > 0 else 0

        tabela_detalhada.append([
            tabela,
            f"{linhas:,}",
            f"{erros:,}",
            f"{tempo:.2f}",
            f"{vel_media:,.1f}",
            f"{cpu_media:.1f}",
            f"{ram_media:.1f}",
            f"{disco_escrito:.1f}",
            f"{disco_lido:.1f}"
        ])

    detalhada_table = Table(tabela_detalhada, repeatRows=1)

    detalhada_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 0), (-1, -1), 8)
    ]))

    story.append(detalhada_table)

    # --------------------------------------------
    # GERAR PDF EM MODO PAISAGEM
    # --------------------------------------------
    pdf = SimpleDocTemplate(output_path, pagesize=landscape(A4))
    pdf.build(story)
    print(f"[PDF GERADO] Arquivo salvo em: {output_path}\n")

# =====================================================================
# MAIN — EXECUÇÃO COMPLETA DO MÉTODO BATCH ROBUSTO
# =====================================================================
def main():
    print("\n=====================================================================")
    print("IMPORTAÇÃO EM LOTES (BATCH ROBUSTO) INICIADA")
    print("=====================================================================\n")

    inicio_execucao = time.time()

    # PROCESSAR TODAS AS TABELAS
    for tabela, pasta in REFERENCE_TABLES.items():
        insert_batch_for_table(tabela, pasta)

    fim_execucao = time.time()

    # GERAR PDF FINAL (Modo Paisagem)
    gerar_relatorio_pdf(
        inicio_execucao=inicio_execucao,
        fim_execucao=fim_execucao
    )

    print("\n=====================================================================")
    print(f"PROCESSO COMPLETO FINALIZADO EM {fim_execucao - inicio_execucao:.2f} segundos")
    print("=====================================================================\n")


# EXECUÇÃO DIRETA
if __name__ == "__main__":
    main()
