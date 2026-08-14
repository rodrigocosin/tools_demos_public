# Databricks notebook source
# MAGIC %md
# MAGIC # Envio em LOTES (contorna o limite de notificação em massa do alerta)
# MAGIC
# MAGIC O SQL Alert não entrega de forma confiável quando inscrito em muitos destinos de uma vez
# MAGIC (ex.: 53). Aqui dividimos os destinatários em **lotes pequenos** e disparamos o alerta
# MAGIC **um lote por vez** (cada lote = um run avulso de `sql_task` com as subscriptions daquele
# MAGIC lote), com **pausa** entre eles. Mantém 1 destino por pessoa (e-mails ocultos).
# MAGIC
# MAGIC Roda como task do job de envio, **depois do gate** `tem_conteudo` e **antes** do
# MAGIC `marcar_enviados` (os posts seguem `pending` até o fim, então todo lote envia o mesmo digest).

# COMMAND ----------

CATALOG = "cosin_aws_serverless_catalog"   # <<< ajuste para seu ambiente
SCHEMA = "blog_digest"
PREFIX = "Blog Digest :: "

dbutils.widgets.text("alert_id", "b5a63e41-6b3e-4cd7-aaa9-eb55701d95a5")
dbutils.widgets.text("warehouse_id", "0c2def7684630e5e")
dbutils.widgets.text("sa_filter", "Rodrigo Cosin")
dbutils.widgets.text("batch_size", "10")     # destinos por lote
dbutils.widgets.text("pause_seconds", "20")  # pausa entre lotes

ALERT_ID = dbutils.widgets.get("alert_id")
WAREHOUSE_ID = dbutils.widgets.get("warehouse_id")
SA_FILTER = dbutils.widgets.get("sa_filter").strip()
BATCH_SIZE = max(1, int(dbutils.widgets.get("batch_size")))
PAUSE = int(dbutils.widgets.get("pause_seconds"))

# COMMAND ----------

import time
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# 1) Destinatários ativos do SA
recips = [r["email"].strip() for r in spark.sql(f"""
    SELECT DISTINCT email FROM {CATALOG}.{SCHEMA}.email_recipients
    WHERE active = true AND email IS NOT NULL AND trim(email) <> ''
      AND ('{SA_FILTER.replace("'", "''")}' = '' OR sa = '{SA_FILTER.replace("'", "''")}')
""").collect()]
print(f"Destinatários ativos (SA='{SA_FILTER}'): {len(recips)}")
if not recips:
    dbutils.notebook.exit("Nenhum destinatário ativo — nada a enviar.")

# 2) Mapeia email -> destination_id (lista paginada de notification destinations)
res, tok = [], None
while True:
    r = w.api_client.do("GET", "/api/2.0/notification-destinations?page_size=100" + (f"&page_token={tok}" if tok else ""))
    res += r.get("results", [])
    tok = r.get("next_page_token")
    if not tok:
        break
by_name = {d["display_name"]: d["id"] for d in res if d.get("display_name", "").startswith(PREFIX)}

dest_ids, faltando = [], []
for e in recips:
    did = by_name.get(PREFIX + e)
    (dest_ids if did else faltando).append(did or e)
if faltando:
    print(f"AVISO: {len(faltando)} destinatários sem destino (rode o sync 02 antes): {faltando[:5]}")
print(f"Destinos a enviar: {len(dest_ids)} | lote={BATCH_SIZE} | pausa={PAUSE}s")

# COMMAND ----------

# 2b) Contexto da execução + posts do digest (para o log)
import datetime as dt
exec_ts = dt.datetime.now()
execution_id = exec_ts.strftime("%Y%m%d-%H%M%S")

_posts = spark.sql(f"""
    SELECT title_pt FROM {CATALOG}.{SCHEMA}.post_summaries WHERE send_status = 'pending'
""").collect()
posts_count = len(_posts)
post_titles = " | ".join(r["title_pt"] for r in _posts if r["title_pt"])
# mapeia destino_id -> email (para logar quem recebeu em cada lote)
id_to_email = {v: k[len(PREFIX):] for k, v in by_name.items()}
print(f"Execução {execution_id} | posts no digest: {posts_count}")

def log_batch(idx, total, batch_ids, sub_run_id, result_state):
    emails = ", ".join(id_to_email.get(d, d) for d in batch_ids)
    spark.sql(f"""
        INSERT INTO {CATALOG}.{SCHEMA}.send_log VALUES
        (:eid, :ets, {idx}, {total}, {len(batch_ids)}, :emails, :srid, :res, {posts_count}, :titles, current_timestamp())
    """, args={"eid": execution_id, "ets": exec_ts.isoformat(sep=" "),
               "emails": emails, "srid": str(sub_run_id), "res": result_state, "titles": post_titles})

# COMMAND ----------

# 3) Dispara o alerta em lotes (um run avulso de sql_task por lote)
batches = [dest_ids[i:i + BATCH_SIZE] for i in range(0, len(dest_ids), BATCH_SIZE)]
print(f"Total de lotes: {len(batches)}")

falhas = 0
for idx, batch in enumerate(batches, 1):
    body = {
        "run_name": f"digest lote {idx}/{len(batches)}",
        "tasks": [{
            "task_key": "send",
            "sql_task": {
                "warehouse_id": WAREHOUSE_ID,
                "alert": {
                    "alert_id": ALERT_ID,
                    "subscriptions": [{"destination_id": d} for d in batch],
                },
            },
        }],
    }
    sub = w.api_client.do("POST", "/api/2.1/jobs/runs/submit", body=body)
    run_id = sub["run_id"]
    # aguarda o run terminar
    while True:
        st = w.api_client.do("GET", f"/api/2.1/jobs/runs/get?run_id={run_id}")
        life = st.get("state", {}).get("life_cycle_state")
        if life in ("TERMINATED", "INTERNAL_ERROR", "SKIPPED"):
            result = st.get("state", {}).get("result_state")
            break
        time.sleep(5)
    ok = (result == "SUCCESS")
    if not ok:
        falhas += 1
    log_batch(idx, len(batches), batch, run_id, result)   # grava no send_log
    print(f"  lote {idx}/{len(batches)} ({len(batch)} destinos) -> {result}")
    if idx < len(batches):
        time.sleep(PAUSE)

print(f"\nConcluído: {len(batches)} lotes, {falhas} com falha.")

# COMMAND ----------

# Log desta execução
display(spark.sql(f"""
    SELECT batch_idx, dest_count, result_state, emails
    FROM {CATALOG}.{SCHEMA}.send_log WHERE execution_id = '{execution_id}'
    ORDER BY batch_idx
"""))

if falhas:
    raise RuntimeError(f"{falhas} lote(s) falharam — verifique o send_log antes de marcar como enviado.")

