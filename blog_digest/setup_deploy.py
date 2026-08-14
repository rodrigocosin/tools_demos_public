# Databricks notebook source
# MAGIC %md
# MAGIC # Setup / Deploy — Databricks Blog Digest (rodar DENTRO do Databricks)
# MAGIC
# MAGIC Recria toda a solução **a partir de um notebook no workspace** (sem CLI / sem máquina local):
# MAGIC schema + tabelas, Legacy SQL query, Legacy SQL alert, 1 Notification Destination por
# MAGIC destinatário (e-mails ocultos), os jobs (diário e de envio) e aplica o template do e-mail.
# MAGIC
# MAGIC **Pré-requisitos:** este notebook deve estar na **mesma pasta** dos notebooks
# MAGIC `00_preparar_email`, `01_ingest_and_summarize`, `02_sync_recipients`, `03_weekly_log`
# MAGIC (ex.: `.../blog_digest/`). Rode com um cluster/serverless que tenha acesso ao Unity Catalog.
# MAGIC
# MAGIC > Idempotência: cria objetos novos a cada execução. Rode **uma vez por ambiente**
# MAGIC > (ou apague os objetos antigos antes de repetir).

# COMMAND ----------

# ============================ CONFIG (ajuste) ================================
CATALOG       = "cosin_aws_serverless_catalog"
SCHEMA        = "blog_digest"
WAREHOUSE_ID  = "0c2def7684630e5e"          # SQL Warehouse (serverless) ligado
LLM_ENDPOINT  = "databricks-claude-opus-4-8"
TIMEZONE      = "America/Sao_Paulo"
DAILY_CRON    = "0 0 8 * * ?"               # ingestão + sync: 08:00
SEND_CRON     = "0 0 10 ? * FRI"            # envio: sexta 10:00
SEED_EMAILS   = ["rodrigocosin@gmail.com"]  # lista inicial (1 destino por e-mail)
SA_NAME       = "Rodrigo Cosin"             # SA dono do envio (sync filtra por este sa)
AE_NAME       = "Rodolfo Catharino"         # AE da conta (cadastro)
# ============================================================================

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# Pasta deste notebook = onde estão os notebooks 00..03 (deriva automaticamente)
nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
USER_PATH = nb_path.rsplit("/", 1)[0]
print("Pasta dos notebooks:", USER_PATH)

def api(method, path, body=None):
    return w.api_client.do(method, path, body=body) if body is not None else w.api_client.do(method, path)

# COMMAND ----------

# MAGIC %md ## 1) Schema + tabelas

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA} COMMENT 'Blog Digest da Databricks'")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.blog_posts (
  url STRING NOT NULL, slug STRING, title STRING, category STRING,
  published_date DATE, read_minutes INT, content STRING, content_hash STRING,
  post_resumo_html STRING, scraped_at TIMESTAMP
) USING DELTA COMMENT 'Posts do blog ingeridos incrementalmente'""")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.post_summaries (
  url STRING NOT NULL, title_pt STRING, resumo STRING, resumo_html STRING,
  bullets_json STRING, por_que_importa STRING, disponibilidade STRING,
  links_importantes STRING, model_used STRING, summarized_at TIMESTAMP,
  weekly_sent BOOLEAN, weekly_sent_at TIMESTAMP,
  send_status STRING
) USING DELTA COMMENT 'Resumos PT-BR + controle de envio (send_status: pending/skip/sent)'""")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.email_recipients (
  company STRING, email STRING NOT NULL, name STRING, active BOOLEAN, added_at TIMESTAMP,
  sa STRING, ae STRING,
  CONSTRAINT pk_email_recipients PRIMARY KEY (email)
) USING DELTA COMMENT 'Lista de destinatários (fonte da verdade)'""")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.send_log (
  execution_id STRING, execution_ts TIMESTAMP, batch_idx INT, batches_total INT,
  dest_count INT, emails STRING, sub_run_id STRING, result_state STRING,
  posts_count INT, post_titles STRING, logged_at TIMESTAMP
) USING DELTA COMMENT 'Histórico de execuções de envio (por lote)'""")

print("Schema e tabelas OK.")

# COMMAND ----------

# MAGIC %md ## 2) Seed da lista de destinatários

# COMMAND ----------

for e in SEED_EMAILS:
    spark.sql(f"""
        INSERT INTO {CATALOG}.{SCHEMA}.email_recipients (email,name,active,added_at,sa,ae)
        SELECT '{e}','',true,current_timestamp(),'{SA_NAME}','{AE_NAME}'
        WHERE NOT EXISTS (SELECT 1 FROM {CATALOG}.{SCHEMA}.email_recipients WHERE email='{e}')
    """)
display(spark.sql(f"SELECT * FROM {CATALOG}.{SCHEMA}.email_recipients"))

# COMMAND ----------

# MAGIC %md ## 3) Legacy SQL query (fonte do alerta)

# COMMAND ----------

# data_source_id do warehouse
ds = api("GET", "/api/2.0/preview/sql/data_sources")
ds_list = ds if isinstance(ds, list) else ds.get("results", [])
DS_ID = next(x["id"] for x in ds_list if x.get("warehouse_id") == WAREHOUSE_ID)

QUERY_SQL = (
    "SELECT row_number() OVER (ORDER BY p.published_date DESC) AS n, "
    "s.title_pt AS post, s.resumo_html AS resumo_html, p.url AS link "
    f"FROM {CATALOG}.{SCHEMA}.post_summaries s "
    f"JOIN {CATALOG}.{SCHEMA}.blog_posts p ON p.url = s.url "
    "WHERE coalesce(s.weekly_sent, false) = false ORDER BY p.published_date DESC"
)
QUERY_ID = api("POST", "/api/2.0/preview/sql/queries",
               {"name": "Blog Digest - query semanal", "data_source_id": DS_ID, "query": QUERY_SQL})["id"]
print("QUERY_ID =", QUERY_ID)

# COMMAND ----------

# MAGIC %md ## 4) Legacy SQL alert (template aplicado depois pelo notebook 00)

# COMMAND ----------

ALERT_ID = api("POST", "/api/2.0/preview/sql/alerts", {
    "name": "Databricks Blog Digest - Semanal",
    "query_id": QUERY_ID,
    "rearm": 1,
    "options": {
        "column": "n", "op": ">", "value": "0",
        "empty_result_state": "ok",
        "custom_subject": "Databricks Blog — Resumo da semana",
        "custom_body": "(definido pelo notebook 00_preparar_email)",
    },
})["id"]
print("ALERT_ID =", ALERT_ID)

# COMMAND ----------

# MAGIC %md ## 5) Notification Destination por destinatário (e-mails ocultos)

# COMMAND ----------

subscriptions = []
for e in SEED_EMAILS:
    did = api("POST", "/api/2.0/notification-destinations",
              {"display_name": f"Blog Digest :: {e}", "config": {"email": {"addresses": [e]}}})["id"]
    subscriptions.append({"destination_id": did})
    print(f"  {e} -> {did}")

# COMMAND ----------

# MAGIC %md ## 6) Jobs (envio primeiro, depois o diário que aponta para ele)

# COMMAND ----------

# Job de ENVIO: preparar_email -> tem_conteudo (gate) -> enviar_digest -> marcar_enviados
send_job = api("POST", "/api/2.1/jobs/create", {
    "name": "blog_send_semanal",
    "tags": {"projeto": "databricks_blog_digest"},
    "max_concurrent_runs": 1,
    "tasks": [
        {"task_key": "preparar_email",
         "notebook_task": {"notebook_path": f"{USER_PATH}/00_preparar_email", "source": "WORKSPACE",
                           "base_parameters": {"alert_id": ALERT_ID, "query_id": QUERY_ID}}},
        {"task_key": "tem_conteudo", "depends_on": [{"task_key": "preparar_email"}],
         "condition_task": {"op": "GREATER_THAN",
                            "left": "{{tasks.preparar_email.values.pendentes}}", "right": "0"}},
        {"task_key": "enviar_lotes", "depends_on": [{"task_key": "tem_conteudo", "outcome": "true"}],
         "notebook_task": {"notebook_path": f"{USER_PATH}/04_enviar_lotes", "source": "WORKSPACE",
                           "base_parameters": {"alert_id": ALERT_ID, "warehouse_id": WAREHOUSE_ID,
                                               "sa_filter": SA_NAME, "batch_size": "10", "pause_seconds": "20"}}},
        {"task_key": "marcar_enviados", "depends_on": [{"task_key": "enviar_lotes"}],
         "notebook_task": {"notebook_path": f"{USER_PATH}/03_weekly_log", "source": "WORKSPACE"}},
    ],
    "schedule": {"quartz_cron_expression": SEND_CRON, "timezone_id": TIMEZONE, "pause_status": "UNPAUSED"},
    "queue": {"enabled": True},
})
SEND_JOB_ID = send_job["job_id"]
print("blog_send_semanal job_id =", SEND_JOB_ID)

# Job DIÁRIO: ingest_and_summarize -> sync_recipients (mantém destinos + subscriptions do envio)
daily_job = api("POST", "/api/2.1/jobs/create", {
    "name": "blog_digest_diario",
    "tags": {"projeto": "databricks_blog_digest"},
    "max_concurrent_runs": 1,
    "tasks": [
        {"task_key": "ingest_and_summarize",
         "notebook_task": {"notebook_path": f"{USER_PATH}/01_ingest_and_summarize", "source": "WORKSPACE"}},
        {"task_key": "sync_recipients", "depends_on": [{"task_key": "ingest_and_summarize"}],
         "notebook_task": {"notebook_path": f"{USER_PATH}/02_sync_recipients", "source": "WORKSPACE",
                           "base_parameters": {"weekly_job_id": str(SEND_JOB_ID), "enviar_task_key": "enviar_digest", "sa_filter": SA_NAME}}},
    ],
    "schedule": {"quartz_cron_expression": DAILY_CRON, "timezone_id": TIMEZONE, "pause_status": "UNPAUSED"},
    "queue": {"enabled": True},
})
print("blog_digest_diario job_id =", daily_job["job_id"])

# COMMAND ----------

# MAGIC %md ## 7) Aplica o template do e-mail (roda o notebook 00 com os IDs criados)

# COMMAND ----------

dbutils.notebook.run(f"{USER_PATH}/00_preparar_email", 600,
                     {"alert_id": ALERT_ID, "query_id": QUERY_ID})
print("Template aplicado no alerta.")

# COMMAND ----------

# MAGIC %md ## Pronto!

# COMMAND ----------

print("================ DEPLOY OK ================")
print("CATALOG/SCHEMA :", f"{CATALOG}.{SCHEMA}")
print("QUERY_ID       :", QUERY_ID)
print("ALERT_ID       :", ALERT_ID)
print("SEND_JOB_ID    :", SEND_JOB_ID, "(blog_send_semanal)")
print("Próximos passos:")
print("  1) Rode o job 'blog_digest_diario' (popula posts + cria destinos/subscriptions)")
print("  2) Rode o job 'blog_send_semanal' (envia)")
print(f"  Gerencie a lista em {CATALOG}.{SCHEMA}.email_recipients")

