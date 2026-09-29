# Databricks notebook source
# DBTITLE 1,ETL Silver - Introdução
# MAGIC %md
# MAGIC # ETL Silver - IT Support
# MAGIC
# MAGIC **Camada Silver**: Dados limpos, enriquecidos e prontos para análise.
# MAGIC
# MAGIC Este notebook realiza as seguintes transformações:
# MAGIC 1. **silver_tickets_full** — Join de `tb_tickets` + `tb_agents` + `tb_sla` com campos calculados (tempo de resolução, flags de SLA)
# MAGIC 2. **silver_comments_enriched** — Join de `tb_tickets_comments` + `tb_tickets` com contexto do ticket
# MAGIC
# MAGIC **Source/Target:** Configurados via `00_Config` (catalog e schema)

# COMMAND ----------

# DBTITLE 1,Configuração
# --------------------------------------------------
# Configuração do ETL (herda catalog/schema do 00_Config)
# --------------------------------------------------
# MAGIC %run ../00_Config

# COMMAND ----------

# DBTITLE 1,Leitura das tabelas Bronze
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- Visualização das tabelas fonte (Bronze/Clean)
# MAGIC -- --------------------------------------------------
# MAGIC SELECT 'tb_tickets' AS tabela, COUNT(*) AS registros FROM tb_tickets
# MAGIC UNION ALL
# MAGIC SELECT 'tb_agents', COUNT(*) FROM tb_agents
# MAGIC UNION ALL
# MAGIC SELECT 'tb_sla', COUNT(*) FROM tb_sla
# MAGIC UNION ALL
# MAGIC SELECT 'tb_tickets_comments', COUNT(*) FROM tb_tickets_comments;

# COMMAND ----------

# DBTITLE 1,Silver - Tickets Full (Enriquecido)
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- silver_tickets_full
# MAGIC -- Join: tickets + agents + sla com campos calculados
# MAGIC -- --------------------------------------------------
# MAGIC CREATE OR REPLACE TABLE silver_tickets_full AS
# MAGIC SELECT
# MAGIC     t.ticket_id,
# MAGIC     t.status,
# MAGIC     t.priority,
# MAGIC     t.source,
# MAGIC     t.topic,
# MAGIC     t.created_time,
# MAGIC     t.close_time,
# MAGIC     t.product_group,
# MAGIC     t.support_level,
# MAGIC     t.country,
# MAGIC     t.latitude,
# MAGIC     t.longitude,
# MAGIC
# MAGIC     -- Dados do atendente
# MAGIC     a.agent_name,
# MAGIC     a.agent_group,
# MAGIC     a.agent_interactions,
# MAGIC
# MAGIC     -- Dados de SLA
# MAGIC     s.expected_sla_to_resolve,
# MAGIC     s.expected_sla_to_first_response,
# MAGIC     s.first_response_time,
# MAGIC     s.sla_for_first_response,
# MAGIC     s.resolution_time,
# MAGIC     s.sla_for_resolution,
# MAGIC     s.survey_results,
# MAGIC
# MAGIC     -- Campos calculados
# MAGIC     ROUND((UNIX_TIMESTAMP(t.close_time) - UNIX_TIMESTAMP(t.created_time)) / 3600, 2) AS resolution_hours,
# MAGIC     ROUND((UNIX_TIMESTAMP(s.first_response_time) - UNIX_TIMESTAMP(t.created_time)) / 3600, 2) AS first_response_hours,
# MAGIC     CASE WHEN t.close_time <= s.expected_sla_to_resolve THEN TRUE ELSE FALSE END AS sla_resolution_met,
# MAGIC     CASE WHEN s.first_response_time <= s.expected_sla_to_first_response THEN TRUE ELSE FALSE END AS sla_first_response_met,
# MAGIC     CURRENT_TIMESTAMP() AS etl_timestamp
# MAGIC
# MAGIC FROM tb_tickets t
# MAGIC LEFT JOIN tb_agents a ON t.ticket_id = a.ticket_id
# MAGIC LEFT JOIN tb_sla s ON t.ticket_id = s.ticket_id;

# COMMAND ----------

# DBTITLE 1,Preview - silver_tickets_full
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- Preview da tabela silver_tickets_full
# MAGIC -- --------------------------------------------------
# MAGIC SELECT * FROM silver_tickets_full LIMIT 10;

# COMMAND ----------

# DBTITLE 1,Silver - Comments Enriquecido
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- silver_comments_enriched
# MAGIC -- Join: comments + tickets (contexto do ticket)
# MAGIC -- --------------------------------------------------
# MAGIC CREATE OR REPLACE TABLE silver_comments_enriched AS
# MAGIC SELECT
# MAGIC     c.ticket_id,
# MAGIC     c.comments,
# MAGIC     LENGTH(c.comments) AS comment_length,
# MAGIC
# MAGIC     -- Contexto do ticket
# MAGIC     t.status,
# MAGIC     t.priority,
# MAGIC     t.topic,
# MAGIC     t.country,
# MAGIC     t.product_group,
# MAGIC     t.support_level,
# MAGIC     t.created_time,
# MAGIC     CURRENT_TIMESTAMP() AS etl_timestamp
# MAGIC
# MAGIC FROM tb_tickets_comments c
# MAGIC LEFT JOIN tb_tickets t ON c.ticket_id = t.ticket_id;

# COMMAND ----------

# DBTITLE 1,Preview - silver_comments_enriched
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- Preview da tabela silver_comments_enriched
# MAGIC -- --------------------------------------------------
# MAGIC SELECT * FROM silver_comments_enriched LIMIT 10;

# COMMAND ----------

# DBTITLE 1,Validação Final
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- Validação: Contagem das tabelas Silver criadas
# MAGIC -- --------------------------------------------------
# MAGIC SELECT 'silver_tickets_full' AS tabela, COUNT(*) AS registros FROM silver_tickets_full
# MAGIC UNION ALL
# MAGIC SELECT 'silver_comments_enriched', COUNT(*) FROM silver_comments_enriched;
