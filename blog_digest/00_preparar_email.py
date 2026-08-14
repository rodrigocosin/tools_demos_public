# Databricks notebook source
# MAGIC %md
# MAGIC # Prepara o email do digest (assunto dinâmico + template)
# MAGIC
# MAGIC Roda como 1ª task do **job semanal**, antes do envio. Atualiza o Legacy SQL alert:
# MAGIC - **Assunto** com o ano-mês do envio: `Databricks Blog — Resumo da semana YYYY-MM (gerado por IA)`
# MAGIC - **Corpo** (cards em PT-BR, com `<hr>` separando cada post, + disclaimer de IA)
# MAGIC
# MAGIC Assim o template fica versionado em código e o assunto sempre reflete o mês do envio.

# COMMAND ----------

# IDs específicos do ambiente (Legacy SQL alert e sua query).
# Em produção atual usam estes defaults; em outro ambiente, o job passa via
# base_parameters (widgets) os IDs criados pelo deploy.sh / setup.
dbutils.widgets.text("alert_id", "b5a63e41-6b3e-4cd7-aaa9-eb55701d95a5")
dbutils.widgets.text("query_id", "bd628f7a-bfad-4a3c-9ac9-e9e8c2104b25")
ALERT_ID = dbutils.widgets.get("alert_id")
QUERY_ID = dbutils.widgets.get("query_id")

# COMMAND ----------

import datetime as dt

data_envio = dt.date.today().strftime("%d/%m/%Y")  # data do envio (formato BR)
subject = f"Resumo semanal — Blog da Databricks ({data_envio})"

# Corpo em cards. Mustache: {{#QUERY_RESULT_ROWS}}...{{/QUERY_RESULT_ROWS}};
# {{post}}/{{link}} (escapados) e {{{resumo_html}}} (HTML cru). <hr> separa cada post.
body = (
    '<div style="font-family:Arial,Helvetica,sans-serif;max-width:640px;color:#1b1b1b">'
    '<p>Olá! Aqui estão os posts mais recentes do blog da Databricks:</p>'
    '<div style="background:#fff8e1;border:1px solid #ffe082;border-radius:6px;padding:10px 14px;font-size:12px;color:#7a5d00;margin-bottom:8px">'
    '⚠️ Os resumos são os do próprio blog da Databricks; o campo <strong>"Por que importa" é gerado por IA</strong> e pode conter imprecisões. '
    'Este e-mail não é um comunicado oficial — para o conteúdo completo, acesse o link de cada post.</div>'
    '<div style="background:#eef4ff;border:1px solid #b9d2ff;border-radius:6px;padding:10px 14px;font-size:12px;color:#234b8a;margin-bottom:8px">'
    '🌐 <strong>Disponibilidade não garantida</strong> — funcionalidades podem variar conforme Cloud (AWS, Azure, GCP), '
    'região e fase de lançamento (Preview/GA). Confirme se está disponível no seu provedor e região antes de planejar o uso.</div>'
    '<div style="height:32px;line-height:32px;font-size:0">&nbsp;</div>'
    '<hr style="border:none;border-top:2px solid #FF3621;margin:0 0 18px">'
    '{{#QUERY_RESULT_ROWS}}'
    '<div style="padding:2px 0 8px">'
    '<div style="height:16px;line-height:16px;font-size:0">&nbsp;</div>'
    '<span style="display:inline-block;border:1.5px solid #1B3139;color:#1B3139;font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:.4px;padding:2px 9px;border-radius:4px">{{categoria}}</span>'
    '<h3 style="margin:8px 0 8px;color:#1B3139;font-size:18px">{{post}}</h3>'
    '{{{resumo_html}}}'
    '{{#por_que}}<p style="margin:10px 0 0;font-size:14px;color:#444444"><strong style="color:#1B3139">Por que importa:</strong> {{por_que}}</p>{{/por_que}}'
    '<p style="margin:12px 0 0">'
    '<a href="{{link}}" style="display:inline-block;padding:7px 16px;border:1.5px solid #FF3621;border-radius:6px;color:#FF3621;text-decoration:none;font-weight:bold;font-size:14px">Ler artigo completo &rarr;</a>'
    '</p>'
    '</div>'
    '<hr style="border:none;border-top:1px solid #d9d9d9;margin:18px 0">'
    '{{/QUERY_RESULT_ROWS}}'
    '<p style="font-size:12px;color:#888888;margin-top:16px;border-top:1px solid #e6e6e6;padding-top:12px">'
    'Não deseja mais receber este e-mail? Entre em contato com o seu <strong>SA</strong> ou <strong>AE</strong> '
    'da conta Databricks para ser removido da lista.</p>'
    '<p style="font-size:11px;color:#aaaaaa">Databricks Blog Digest · resumo automático semanal · gerado por IA</p>'
    '</div>'
)

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

w.api_client.do(
    "PUT",
    f"/api/2.0/preview/sql/alerts/{ALERT_ID}",
    body={
        "name": "Databricks Blog Digest - Semanal",
        "query_id": QUERY_ID,
        # rearm pequeno: o alert "rearma" e volta a notificar a cada execucao do job.
        # Com rearm=0 ele notificaria so na 1a transicao OK->TRIGGERED e ficaria mudo
        # nas execucoes seguintes enquanto continuasse disparado.
        "rearm": 1,
        "options": {
            "column": "n",
            "op": ">",
            "value": "0",
            "empty_result_state": "ok",  # resultado vazio NAO dispara o alerta
            "custom_subject": subject,
            "custom_body": body,
        },
    },
)
print("Alert atualizado.")
print("Assunto:", subject)

# COMMAND ----------

# Confirma
chk = w.api_client.do("GET", f"/api/2.0/preview/sql/alerts/{ALERT_ID}")
print("custom_subject:", chk["options"]["custom_subject"])
print("tem <hr> no corpo:", "<hr" in chk["options"]["custom_body"])

# COMMAND ----------

# Conta posts pendentes e expõe como TASK VALUE -> o job só envia se houver conteúdo
CATALOG = "cosin_aws_serverless_catalog"
SCHEMA = "blog_digest"

pendentes = spark.sql(f"""
    SELECT count(*) AS n
    FROM {CATALOG}.{SCHEMA}.post_summaries
    WHERE coalesce(weekly_sent, false) = false
""").collect()[0]["n"]

print("Posts pendentes para envio:", pendentes)
dbutils.jobs.taskValues.set(key="pendentes", value=int(pendentes))

