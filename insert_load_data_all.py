# =====================================================================
# ARQUIVO: insert_load_data_all.py
# OBJETIVO: INSERÇÃO USANDO LOAD DATA LOCAL INFILE
# COMPARAÇÃO DIRETA COM LINE-BY-LINE E BATCH
# RELATÓRIO PDF IDENTICO + MONITORAMENTO CPU/RAM/DISCO
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

# CONEXÃO PADRÃO (já precisa estar com allow_local_infile=True)
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

# DADOS PARA RELATÓRIO FINAL
REPORT_DATA = {}

# FLAG PARA ENCERRAR MONITORAMENTO
STOP_MONITORING = False

# =====================================================================
# MAPEAMENTO DAS PASTAS POR TABELA
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
# COLUNAS DE CADA TABELA (EXATAMENTE IGUAIS AO MÉTODO LINE/BATCH)
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
# MONITORAMENTO CPU/RAM/DISCO — MESMA FUNÇÃO DOS OUTROS MÉTODOS
# =====================================================================
def monitor_system(metrics_list):
    """
    MONITORA CPU, RAM E DISCO A CADA 0.1s.
    A primeira leitura de cpu_percent SEMPRE é 0, então ignoramos ela.
    """

    global STOP_MONITORING
    process = psutil.Process(os.getpid())

    # A PRIMEIRA CHAMADA SEMPRE RETORNA 0.0
    psutil.cpu_percent(interval=None)

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
# FUNÇÃO: INSERIR DADOS USANDO LOAD DATA LOCAL INFILE
# =====================================================================
def insert_load_data_for_table(table_name, folder_path):
    """
    INSERE OS CSVs DE UMA TABELA USANDO LOAD DATA LOCAL INFILE.
    - Muito mais rápido
    - Mesmo estilo visual dos outros métodos
    - CPU/RAM/ETA em tempo real
    - Compatível com o relatório PDF
    """

    global STOP_MONITORING

    print(f"\n=====================================================================")
    print(f"[INÍCIO - LOAD DATA] TABELA: {table_name.upper()}")
    print("=====================================================================\n")

    # -----------------------------------------------------------------
    # VERIFICAÇÃO DA PASTA
    # -----------------------------------------------------------------
    if not os.path.isdir(folder_path):
        print(f"[ERRO] Pasta não existe: {folder_path}")
        return

    files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(".csv")])

    print(f"[INFO] {len(files)} arquivos CSV encontrados para {table_name}")

    # -----------------------------------------------------------------
    # CONTAR TOTAL DE LINHAS (PARA ETA)
    # -----------------------------------------------------------------
    print(f"[{table_name.upper()}] Contando total de linhas...")

    total_linhas_tabela = 0
    for f_csv in files:
        with open(os.path.join(folder_path, f_csv), "r", encoding=CSV_ENCODING, errors="ignore") as f:
            for _ in f:
                total_linhas_tabela += 1

    print(f"[{table_name.upper()}] Total de linhas: {total_linhas_tabela}\n")

    # -----------------------------------------------------------------
    # MONITORAMENTO
    # -----------------------------------------------------------------
    metrics_list = []
    STOP_MONITORING = False
    monitor_thread = Thread(target=monitor_system, args=(metrics_list,))
    monitor_thread.start()

    # -----------------------------------------------------------------
    # COLUNAS E SQL
    # -----------------------------------------------------------------
    colunas = TABLE_COLUMNS[table_name]
    colunas_sql = ", ".join(colunas)

    # MySQL LOAD DATA LOCAL — IMPORTANTE:
    # FIELDS TERMINATED BY ';'  → separador
    # LINES TERMINATED BY '\n' → cada linha
    # IGNORE 0 LINES           → sem cabeçalho
    template_sql = f"""
        LOAD DATA LOCAL INFILE %s
        INTO TABLE {table_name}
        CHARACTER SET latin1
        FIELDS TERMINATED BY '{CSV_DELIMITER}'
        OPTIONALLY ENCLOSED BY '"'
        LINES TERMINATED BY '\\n'
        ({colunas_sql});
    """

    # -----------------------------------------------------------------
    # CONTADORES
    # -----------------------------------------------------------------
    total_inseridas = 0
    total_erros = 0
    

    # -----------------------------------------------------------------
    # CONEXÃO
    # -----------------------------------------------------------------
    conn = create_connection()
    cursor = conn.cursor()

    inicio = time.time()
    ultima_medida = inicio
    linhas_desde_ultima_medida = 0

    # -----------------------------------------------------------------
    # PROCESSAR CADA CSV SEPARADAMENTE
    # -----------------------------------------------------------------
    for f_csv in files:

        caminho_csv = os.path.join(folder_path, f_csv)

        # Contar linhas deste arquivo (para ETA do arquivo)
        total_linhas_arquivo = sum(1 for _ in open(caminho_csv, "r", encoding=CSV_ENCODING, errors="ignore"))

        print(f"[{table_name.upper()}] Importando {f_csv} ({total_linhas_arquivo:,} linhas)")

        try:
            cursor.execute(template_sql, (caminho_csv,))
            conn.commit()
            total_inseridas += total_linhas_arquivo
            linhas_desde_ultima_medida += total_linhas_arquivo

        except Exception as e:
            total_erros += total_linhas_arquivo
            print(f"[ERRO LOAD DATA] {e}")

        # -----------------------------------------------------------------
        # Contar warnings = linhas descartadas
        # -----------------------------------------------------------------
        cursor.execute("SHOW WARNINGS")
        warnings = cursor.fetchall()
        warnings_count = len(warnings)

        if warnings_count > 0:
            print(f"[LOAD DATA] Linhas descartadas neste arquivo: {warnings_count}")

        total_erros += warnings_count
        
        # -----------------------------------------------------------------
        # LOGS PERIÓDICOS (igual aos outros métodos)
        # -----------------------------------------------------------------
        if linhas_desde_ultima_medida >= 10000:

            tempo_decorrido = time.time() - inicio
            velocidade = total_inseridas / tempo_decorrido if tempo_decorrido > 0 else 0

            linhas_restantes = total_linhas_tabela - total_inseridas
            eta_seg = linhas_restantes / velocidade if velocidade > 0 else 0
            eta_formatado = time.strftime("%H:%M:%S", time.gmtime(eta_seg))

            print(f"\n[{table_name.upper()} - LOAD] {total_inseridas:,} linhas processadas")
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
    # FINALIZAR MONITORAMENTO
    # -----------------------------------------------------------------
    STOP_MONITORING = True
    monitor_thread.join()

    tempo_total = time.time() - inicio

    # -----------------------------------------------------------------
    # SALVAR MÉTRICAS PARA RELATÓRIO PDF
    # -----------------------------------------------------------------
    REPORT_DATA[table_name] = {
        "linhas": total_inseridas,
        "erros": total_erros,
        "tempo": tempo_total,
        "metricas": metrics_list
    }

    # -----------------------------------------------------------------
    # FECHAR CONEXÃO
    # -----------------------------------------------------------------
    close_connection(conn, cursor)

    print(f"\n[FINALIZADO - LOAD] {table_name.upper()} — "
          f"{total_inseridas:,} linhas inseridas, "
          f"{total_erros} erros, "
          f"tempo total {tempo_total:.2f}s\n")

    # -----------------------------------------------------------------
    # LOG FINAL (MESMO PADRÃO DOS OUTROS MÉTODOS)
    # -----------------------------------------------------------------
    print("------------------------------------------------------------")
    print(f"[RESUMO - {table_name.upper()} - LOAD DATA]")
    print(f"Linhas inseridas: {total_inseridas:,}")
    print(f"Erros: {total_erros}")
    print(f"Tempo total: {tempo_total:.2f} segundos")

    velocidade_final = total_inseridas / tempo_total if tempo_total > 0 else 0
    print(f"Velocidade média: {velocidade_final:,.0f} linhas/s")

    linhas_restantes = max(total_linhas_tabela - total_inseridas, 0)
    print(f"Linhas restantes: {linhas_restantes:,}")

    print("------------------------------------------------------------\n")


# =====================================================================
# PARTE 4 — RELATÓRIO PDF (MESMO PADRÃO DOS OUTROS MÉTODOS)
# =====================================================================
def gerar_relatorio_pdf(output_path="relatorio_insercao_load_data.pdf",
                        inicio_execucao=None,
                        fim_execucao=None):
    """
    GERA RELATÓRIO TÉCNICO EM PDF COM:
    - RESUMO GERAL
    - ESTATÍSTICAS POR TABELA
    - CPU MÉDIA
    - RAM MÉDIA
    - DISCO LIDO/ESCRITO
    - VELOCIDADE MÉDIA
    """

    styles = getSampleStyleSheet()
    story = []

    # ======================
    # TÍTULO
    # ======================
    story.append(Paragraph("<b>Relatório Técnico — LOAD DATA INFILE</b>",
                           styles["Title"]))
    story.append(Paragraph("<br/>", styles["BodyText"]))

    # ======================
    # RESUMO GERAL
    # ======================
    story.append(Paragraph("<b>Resumo Geral</b>", styles["Heading2"]))

    duracao_total = fim_execucao - inicio_execucao
    total_linhas_geral = sum(d["linhas"] for d in REPORT_DATA.values())
    total_erros_geral = sum(d["erros"] for d in REPORT_DATA.values())

    vel_geral = total_linhas_geral / duracao_total if duracao_total > 0 else 0

    resumo = [
        ["Início da Execução", time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(inicio_execucao))],
        ["Fim da Execução", time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(fim_execucao))],
        ["Duração Total", f"{duracao_total:.2f} s"],
        ["Linhas Inseridas no Total", f"{total_linhas_geral:,}"],
        ["Erros Totais", total_erros_geral],
        ["Velocidade Média Geral", f"{vel_geral:,.1f} linhas/s"]
    ]

    tabela_resumo = Table(resumo, colWidths=[250, 250])
    tabela_resumo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    story.append(tabela_resumo)
    story.append(Paragraph("<br/><br/>", styles["BodyText"]))

    # ======================
    # TABELA DETALHADA
    # ======================
    story.append(Paragraph("<b>Estatísticas por Tabela</b>", styles["Heading2"]))

    tabela_detalhada = [
        [
            "Tabela",
            "Linhas",
            "Erros",
            "Tempo (s)",
            "Vel. Média",
            "CPU Média",
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
            linhas,
            erros,
            f"{tempo:.2f}",
            f"{vel_media:.1f}",
            f"{cpu_media:.1f}%",
            f"{ram_media:.1f}",
            f"{disco_escrito:.1f}",
            f"{disco_lido:.1f}"
        ])

    tabela_pdf = Table(tabela_detalhada, repeatRows=1)
    tabela_pdf.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
    ]))

    story.append(tabela_pdf)

    # ======================
    # GERAR PDF
    # ======================
    pdf = SimpleDocTemplate(output_path, pagesize=landscape(A4))
    pdf.build(story)

    print(f"[PDF GERADO] Salvo em: {output_path}\n")


# =====================================================================
# PARTE 5 — MAIN COMPLETO
# =====================================================================
def main():
    print("\n=====================================================================")
    print("IMPORTAÇÃO USANDO LOAD DATA LOCAL INFILE INICIADA")
    print("=====================================================================\n")

    inicio_execucao = time.time()

    # PROCESSAR TODAS AS TABELAS
    for tabela, pasta in REFERENCE_TABLES.items():
        insert_load_data_for_table(tabela, pasta)

    fim_execucao = time.time()

    # GERAR PDF DE RELATÓRIO (MESMO PADRÃO DOS OUTROS)
    gerar_relatorio_pdf(
        inicio_execucao=inicio_execucao,
        fim_execucao=fim_execucao
    )

    print("\n=====================================================================")
    print(f"PROCESSO COMPLETO FINALIZADO EM {fim_execucao - inicio_execucao:.2f} segundos")
    print("=====================================================================\n")


# EXECUÇÃO
if __name__ == "__main__":
    main()
