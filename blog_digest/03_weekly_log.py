# Databricks notebook source
# MAGIC %md
# MAGIC # Marca os posts enviados (roda após a task de envio)
# MAGIC
# MAGIC No **job semanal**, esta é a 2ª task e só executa se a task de **envio**
# MAGIC (Legacy alert via `sql_task`) tiver concluído com sucesso. Portanto, tudo que
# MAGIC estava pendente (`weekly_sent = false`) acabou de ser enviado e pode ser marcado.
# MAGIC
# MAGIC O histórico de envios (quais posts, quando) fica na própria `post_summaries`
# MAGIC via `weekly_sent_at` — sem tabelas de controle separadas.

# COMMAND ----------

CATALOG = "cosin_aws_serverless_catalog"
SCHEMA = "blog_digest"

# COMMAND ----------

pendentes = spark.sql(f"""
    SELECT p.published_date, s.title_pt
    FROM {CATALOG}.{SCHEMA}.post_summaries s
    JOIN {CATALOG}.{SCHEMA}.blog_posts p ON p.url = s.url
    WHERE s.send_status = 'pending'
    ORDER BY p.published_date DESC
""").collect()

print(f"Posts que acabaram de ser enviados (a marcar): {len(pendentes)}")
for r in pendentes:
    print(f"  [{r['published_date']}] {r['title_pt']}")

# COMMAND ----------

if pendentes:
    spark.sql(f"""
        UPDATE {CATALOG}.{SCHEMA}.post_summaries
        SET send_status = 'sent', weekly_sent = true, weekly_sent_at = current_timestamp()
        WHERE send_status = 'pending'
    """)
    print(f"{len(pendentes)} posts marcados como enviados (send_status='sent').")
else:
    print("Nada pendente para marcar (nenhum email novo foi enviado nesta semana).")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Histórico de envios (derivado de `post_summaries.weekly_sent_at`)

# COMMAND ----------

display(spark.sql(f"""
    SELECT date(weekly_sent_at) AS data_envio, count(*) AS qtd_posts, collect_list(title_pt) AS posts
    FROM {CATALOG}.{SCHEMA}.post_summaries
    WHERE send_status = 'sent'
    GROUP BY date(weekly_sent_at)
    ORDER BY data_envio DESC
"""))

