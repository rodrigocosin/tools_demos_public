# Databricks notebook source
# MAGIC %md
# MAGIC # Sync de destinatários (1 destino por pessoa = e-mails ocultos)
# MAGIC
# MAGIC **Fonte da verdade** da lista: tabela `email_recipients`.
# MAGIC
# MAGIC Para que cada destinatário receba um e-mail **individual** (sem ver os outros no
# MAGIC campo "Para"), usamos **um Notification Destination por pessoa**. Este notebook:
# MAGIC 1. Garante 1 destination por destinatário **ativo** (cria/atualiza; remove os de quem saiu)
# MAGIC 2. Atualiza as **subscriptions** da task de envio do job semanal com esses destinos
# MAGIC
# MAGIC Roda no **job diário** porque as subscriptions do `sql_task` precisam estar
# MAGIC definidas **antes** do run de envio (edição no meio do run não vale para o run atual).
# MAGIC Como o diário roda toda manhã, na sexta a lista já está correta.

# COMMAND ----------

CATALOG = "cosin_aws_serverless_catalog"   # <<< ajuste para seu ambiente
SCHEMA = "blog_digest"
PREFIX = "Blog Digest :: "                 # convenção de nome dos destinos por pessoa

# IDs/keys parametrizáveis (defaults = ambiente atual)
dbutils.widgets.text("weekly_job_id", "696804447163687")
dbutils.widgets.text("enviar_task_key", "enviar_digest")
dbutils.widgets.text("sa_filter", "Rodrigo Cosin")   # envia só os contatos deste SA
WEEKLY_JOB_ID = int(dbutils.widgets.get("weekly_job_id"))
ENVIAR_TASK_KEY = dbutils.widgets.get("enviar_task_key")
SA_FILTER = dbutils.widgets.get("sa_filter").strip()

# COMMAND ----------

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# 1) Destinatários ativos do SA (filtra por sa quando sa_filter informado)
recips = [
    r["email"].strip()
    for r in spark.sql(f"""
        SELECT DISTINCT email FROM {CATALOG}.{SCHEMA}.email_recipients
        WHERE active = true AND email IS NOT NULL AND trim(email) <> ''
          AND ('{SA_FILTER.replace("'", "''")}' = '' OR sa = '{SA_FILTER.replace("'", "''")}')
    """).collect()
]
print(f"Destinatários ativos (SA='{SA_FILTER}'): {len(recips)} -> {recips}")
if not recips:
    raise ValueError("Nenhum destinatário ativo — abortando para não zerar o envio.")

wanted = {PREFIX + e: e for e in recips}   # nome_do_destino -> email

# COMMAND ----------

# 2) Lista destinos existentes com nosso prefixo (com PAGINAÇÃO — a API pagina em ~20)
res = []
_token = None
while True:
    _path = "/api/2.0/notification-destinations?page_size=100" + (f"&page_token={_token}" if _token else "")
    _r = w.api_client.do("GET", _path)
    res += _r.get("results", [])
    _token = _r.get("next_page_token")
    if not _token:
        break
by_name = {d["display_name"]: d for d in res if d.get("display_name", "").startswith(PREFIX)}

dest_ids = []
for name, email in wanted.items():
    body = {"display_name": name, "config": {"email": {"addresses": [email]}}}
    if name in by_name:
        did = by_name[name]["id"]
        w.api_client.do("PATCH", f"/api/2.0/notification-destinations/{did}", body=body)
    else:
        did = w.api_client.do("POST", "/api/2.0/notification-destinations", body=body)["id"]
        print("criado destino:", name)
    dest_ids.append(did)

# Remove destinos (com nosso prefixo) de quem não está mais ativo
for name, d in by_name.items():
    if name not in wanted:
        w.api_client.do("DELETE", f"/api/2.0/notification-destinations/{d['id']}")
        print("removido destino:", name)

print(f"Destinos mantidos: {len(dest_ids)} (1 por destinatário ativo).")

# NOTA: com o envio em LOTES (04_enviar_lotes), o sync NÃO atualiza mais as
# subscriptions do job — o notebook 04 monta os destinos por lote diretamente da
# tabela. Aqui basta manter 1 Notification Destination por destinatário ativo.

