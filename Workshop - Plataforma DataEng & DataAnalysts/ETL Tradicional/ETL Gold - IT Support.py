# Databricks notebook source
# DBTITLE 1,ETL Gold - Introdução
# MAGIC %md
# MAGIC # ETL Gold - IT Support
# MAGIC
# MAGIC **Camada Gold**: Dados agregados e prontos para consumo em dashboards e relatórios.
# MAGIC
# MAGIC Este notebook cria as seguintes tabelas a partir da camada Silver:
# MAGIC 1. **gold_support_kpis** — KPIs gerais de suporte (total tickets, tempo médio, SLA, satisfação)
# MAGIC 2. **gold_tickets_by_country** — Métricas agregadas por país
# MAGIC 3. **gold_agent_performance** — Performance individual de cada atendente
# MAGIC 4. **gold_sla_compliance** — Conformidade de SLA por prioridade e país
# MAGIC
# MAGIC **Source/Target:** Configurados via `00_Config` (catalog e schema)

# COMMAND ----------

# DBTITLE 1,Configuração
# --------------------------------------------------
# Configuração do ETL (herda catalog/schema do 00_Config)
# --------------------------------------------------
# MAGIC %run ../00_Config

# COMMAND ----------

# DBTITLE 1,Leitura das tabelas Silver
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- Visualização das tabelas Silver (fonte)
# MAGIC -- --------------------------------------------------
# MAGIC SELECT 'silver_tickets_full' AS tabela, COUNT(*) AS registros FROM silver_tickets_full
# MAGIC UNION ALL
# MAGIC SELECT 'silver_comments_enriched', COUNT(*) FROM silver_comments_enriched;

# COMMAND ----------

# DBTITLE 1,Gold - Support KPIs
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- gold_support_kpis
# MAGIC -- KPIs gerais consolidados do suporte
# MAGIC -- --------------------------------------------------
# MAGIC CREATE OR REPLACE TABLE gold_support_kpis AS
# MAGIC SELECT
# MAGIC     COUNT(ticket_id) AS total_tickets,
# MAGIC     COUNT(DISTINCT agent_name) AS total_agents,
# MAGIC     ROUND(AVG(resolution_hours), 2) AS avg_resolution_hours,
# MAGIC     ROUND(AVG(first_response_hours), 2) AS avg_first_response_hours,
# MAGIC     ROUND(AVG(survey_results), 2) AS avg_survey_score,
# MAGIC     ROUND(SUM(CASE WHEN sla_resolution_met = TRUE THEN 1 ELSE 0 END) / COUNT(ticket_id) * 100, 2) AS sla_resolution_pct,
# MAGIC     ROUND(SUM(CASE WHEN sla_first_response_met = TRUE THEN 1 ELSE 0 END) / COUNT(ticket_id) * 100, 2) AS sla_first_response_pct,
# MAGIC     SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) AS open_tickets,
# MAGIC     SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) AS closed_tickets,
# MAGIC     ROUND(AVG(agent_interactions), 2) AS avg_interactions_per_ticket,
# MAGIC     CURRENT_TIMESTAMP() AS etl_timestamp
# MAGIC FROM silver_tickets_full;

# COMMAND ----------

# DBTITLE 1,Preview - gold_support_kpis
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- Preview da tabela gold_support_kpis
# MAGIC -- --------------------------------------------------
# MAGIC SELECT * FROM gold_support_kpis;

# COMMAND ----------

# DBTITLE 1,Gold - Tickets por País
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- gold_tickets_by_country
# MAGIC -- Métricas agregadas por país
# MAGIC -- --------------------------------------------------
# MAGIC CREATE OR REPLACE TABLE gold_tickets_by_country AS
# MAGIC SELECT
# MAGIC     country,
# MAGIC     COUNT(ticket_id) AS total_tickets,
# MAGIC     ROUND(AVG(resolution_hours), 2) AS avg_resolution_hours,
# MAGIC     ROUND(AVG(survey_results), 2) AS avg_survey_score,
# MAGIC     ROUND(SUM(CASE WHEN sla_resolution_met = TRUE THEN 1 ELSE 0 END) / COUNT(ticket_id) * 100, 2) AS sla_compliance_pct,
# MAGIC     COUNT(DISTINCT agent_name) AS agents_count,
# MAGIC     SUM(CASE WHEN priority = 'Critical' THEN 1 ELSE 0 END) AS critical_tickets,
# MAGIC     SUM(CASE WHEN priority = 'High' THEN 1 ELSE 0 END) AS high_tickets,
# MAGIC     CURRENT_TIMESTAMP() AS etl_timestamp
# MAGIC FROM silver_tickets_full
# MAGIC GROUP BY country
# MAGIC ORDER BY total_tickets DESC;

# COMMAND ----------

# DBTITLE 1,Preview - gold_tickets_by_country
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- Preview da tabela gold_tickets_by_country
# MAGIC -- --------------------------------------------------
# MAGIC SELECT * FROM gold_tickets_by_country;

# COMMAND ----------

# DBTITLE 1,Gold - Agent Performance
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- gold_agent_performance
# MAGIC -- Métricas individuais por atendente
# MAGIC -- --------------------------------------------------
# MAGIC CREATE OR REPLACE TABLE gold_agent_performance AS
# MAGIC SELECT
# MAGIC     agent_name,
# MAGIC     agent_group,
# MAGIC     COUNT(ticket_id) AS total_tickets,
# MAGIC     ROUND(AVG(resolution_hours), 2) AS avg_resolution_hours,
# MAGIC     ROUND(AVG(first_response_hours), 2) AS avg_first_response_hours,
# MAGIC     ROUND(AVG(survey_results), 2) AS avg_survey_score,
# MAGIC     ROUND(SUM(CASE WHEN sla_resolution_met = TRUE THEN 1 ELSE 0 END) / COUNT(ticket_id) * 100, 2) AS sla_compliance_pct,
# MAGIC     ROUND(AVG(agent_interactions), 2) AS avg_interactions,
# MAGIC     COUNT(DISTINCT country) AS countries_served,
# MAGIC     CURRENT_TIMESTAMP() AS etl_timestamp
# MAGIC FROM silver_tickets_full
# MAGIC WHERE agent_name IS NOT NULL
# MAGIC GROUP BY agent_name, agent_group
# MAGIC ORDER BY total_tickets DESC;

# COMMAND ----------

# DBTITLE 1,Preview - gold_agent_performance
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- Preview da tabela gold_agent_performance
# MAGIC -- --------------------------------------------------
# MAGIC SELECT * FROM gold_agent_performance LIMIT 10;

# COMMAND ----------

# DBTITLE 1,Gold - SLA Compliance
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- gold_sla_compliance
# MAGIC -- Conformidade de SLA por prioridade e país
# MAGIC -- --------------------------------------------------
# MAGIC CREATE OR REPLACE TABLE gold_sla_compliance AS
# MAGIC SELECT
# MAGIC     priority,
# MAGIC     country,
# MAGIC     COUNT(ticket_id) AS total_tickets,
# MAGIC     SUM(CASE WHEN sla_resolution_met = TRUE THEN 1 ELSE 0 END) AS tickets_within_sla,
# MAGIC     SUM(CASE WHEN sla_resolution_met = FALSE THEN 1 ELSE 0 END) AS tickets_breached_sla,
# MAGIC     ROUND(SUM(CASE WHEN sla_resolution_met = TRUE THEN 1 ELSE 0 END) / COUNT(ticket_id) * 100, 2) AS sla_compliance_pct,
# MAGIC     ROUND(AVG(resolution_hours), 2) AS avg_resolution_hours,
# MAGIC     ROUND(AVG(survey_results), 2) AS avg_survey_score,
# MAGIC     CURRENT_TIMESTAMP() AS etl_timestamp
# MAGIC FROM silver_tickets_full
# MAGIC GROUP BY priority, country
# MAGIC ORDER BY priority, total_tickets DESC;

# COMMAND ----------

# DBTITLE 1,Validação Final
# MAGIC %sql
# MAGIC -- --------------------------------------------------
# MAGIC -- Validação: Contagem das tabelas Gold criadas
# MAGIC -- --------------------------------------------------
# MAGIC SELECT 'gold_support_kpis' AS tabela, COUNT(*) AS registros FROM gold_support_kpis
# MAGIC UNION ALL
# MAGIC SELECT 'gold_tickets_by_country', COUNT(*) FROM gold_tickets_by_country
# MAGIC UNION ALL
# MAGIC SELECT 'gold_agent_performance', COUNT(*) FROM gold_agent_performance
# MAGIC UNION ALL
# MAGIC SELECT 'gold_sla_compliance', COUNT(*) FROM gold_sla_compliance;
