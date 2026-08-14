# Databricks notebook source
# MAGIC %md
# MAGIC # File Validator App — Setup de Ambiente
# MAGIC
# MAGIC Este notebook cria toda a infraestrutura necessária para o **File Validator App** em um novo workspace Databricks.
# MAGIC
# MAGIC **O que será criado:**
# MAGIC - Schema `file_validator` no catálogo escolhido
# MAGIC - Tabela Delta `file_schemas` (definições de schema)
# MAGIC - Tabela Delta `uploaded_files` (histórico de uploads com amostra de 10 linhas)
# MAGIC - Volume `uploads` (arquivos originais enviados pelo usuário)
# MAGIC - App Databricks `file-validator-app`
# MAGIC
# MAGIC **Pré-requisitos:**
# MAGIC - Unity Catalog habilitado
# MAGIC - Permissão de `CREATE SCHEMA` no catálogo alvo
# MAGIC - Permissão de `CAN MANAGE` em Apps

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Parâmetros — configure aqui antes de executar

# COMMAND ----------

# DBTITLE 1,Configuração
# ============================================================
# ALTERE ESTAS VARIÁVEIS PARA O SEU AMBIENTE
# ============================================================

TARGET_CATALOG = "cosin_aws_serverless_catalog"   # Catálogo onde criar as tabelas
TARGET_SCHEMA  = "file_validator"                  # Schema a ser criado
APP_NAME       = "file-validator-app"              # Nome do Databricks App
WORKSPACE_PATH = "/Users/rodrigo.cosin@databricks.com/file-validator-app"  # Path no workspace

# Warehouse para execução de queries no app
WAREHOUSE_ID   = "0c2def7684630e5e"

print(f"Catálogo : {TARGET_CATALOG}")
print(f"Schema   : {TARGET_SCHEMA}")
print(f"App      : {APP_NAME}")
print(f"Warehouse: {WAREHOUSE_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Criar Schema

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {TARGET_CATALOG}.{TARGET_SCHEMA}")
print(f"✅ Schema `{TARGET_CATALOG}.{TARGET_SCHEMA}` criado (ou já existe).")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Criar Volume para arquivos originais

# COMMAND ----------

spark.sql(f"CREATE VOLUME IF NOT EXISTS {TARGET_CATALOG}.{TARGET_SCHEMA}.uploads")
print(f"✅ Volume `/Volumes/{TARGET_CATALOG}/{TARGET_SCHEMA}/uploads` criado.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Criar Tabela — Schemas de Validação

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {TARGET_CATALOG}.{TARGET_SCHEMA}.file_schemas (
  schema_id   STRING    COMMENT 'UUID único do schema',
  schema_name STRING    COMMENT 'Nome amigável do schema',
  fields      STRING    COMMENT 'JSON array com definição dos campos',
  created_at  TIMESTAMP COMMENT 'Data/hora de criação',
  updated_at  TIMESTAMP COMMENT 'Data/hora da última atualização'
)
USING DELTA
COMMENT 'Schemas de validação cadastrados pelos usuários'
""")
print(f"✅ Tabela `{TARGET_CATALOG}.{TARGET_SCHEMA}.file_schemas` criada.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Criar Tabela — Histórico de Uploads

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {TARGET_CATALOG}.{TARGET_SCHEMA}.uploaded_files (
  upload_id   STRING    COMMENT 'UUID único do upload',
  schema_name STRING    COMMENT 'Nome do schema usado na validação',
  file_name   STRING    COMMENT 'Nome original do arquivo enviado',
  uploaded_at TIMESTAMP COMMENT 'Data/hora do upload',
  row_count   INT       COMMENT 'Total de linhas no arquivo',
  data        STRING    COMMENT 'Amostra das 10 primeiras linhas em JSON',
  volume_path STRING    COMMENT 'Caminho do arquivo original no Volume'
)
USING DELTA
COMMENT 'Histórico de arquivos validados e enviados'
""")
print(f"✅ Tabela `{TARGET_CATALOG}.{TARGET_SCHEMA}.uploaded_files` criada.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Verificar estrutura criada

# COMMAND ----------

print("=" * 60)
print(f"CATÁLOGO  : {TARGET_CATALOG}")
print(f"SCHEMA    : {TARGET_SCHEMA}")
print("=" * 60)

tables = spark.sql(f"SHOW TABLES IN {TARGET_CATALOG}.{TARGET_SCHEMA}").collect()
print(f"\nTabelas ({len(tables)}):")
for t in tables:
    print(f"  - {t['tableName']}")

volumes = spark.sql(f"SHOW VOLUMES IN {TARGET_CATALOG}.{TARGET_SCHEMA}").collect()
print(f"\nVolumes ({len(volumes)}):")
for v in volumes:
    print(f"  - {v['volume_name']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Deploy do App (via Databricks CLI)
# MAGIC
# MAGIC Execute os comandos abaixo no terminal (fora deste notebook) após fazer o upload do código-fonte para o workspace.
# MAGIC
# MAGIC ```bash
# MAGIC # 1. Sincronizar código para o workspace
# MAGIC databricks sync /local/path/file-validator-app \
# MAGIC   /Users/<seu-email>/file-validator-app \
# MAGIC   --exclude node_modules --exclude .venv --exclude __pycache__ \
# MAGIC   --exclude .git --exclude "frontend/src" --exclude "frontend/public" \
# MAGIC   -p <seu-profile>
# MAGIC
# MAGIC # 2. Criar o app (apenas na primeira vez)
# MAGIC databricks apps create file-validator-app \
# MAGIC   --description "File validation with schema management" \
# MAGIC   -p <seu-profile>
# MAGIC
# MAGIC # 3. Deploy
# MAGIC databricks apps deploy file-validator-app \
# MAGIC   --source-code-path /Workspace/Users/<seu-email>/file-validator-app \
# MAGIC   -p <seu-profile>
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Configurar variáveis de ambiente do App
# MAGIC
# MAGIC No Databricks UI:
# MAGIC `Compute → Apps → file-validator-app → Edit`
# MAGIC
# MAGIC Adicione as variáveis:
# MAGIC
# MAGIC | Variável | Valor |
# MAGIC |---|---|
# MAGIC | `DATABRICKS_HOST` | `<workspace-host>` (sem https://) |
# MAGIC | `WAREHOUSE_ID` | ID do SQL Warehouse |
# MAGIC
# MAGIC O token é injetado automaticamente pelo runtime do App via Service Principal.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Consultas úteis pós-setup

# COMMAND ----------

# DBTITLE 1,Ver schemas cadastrados
display(spark.sql(f"SELECT schema_id, schema_name, updated_at FROM {TARGET_CATALOG}.{TARGET_SCHEMA}.file_schemas ORDER BY updated_at DESC"))

# COMMAND ----------

# DBTITLE 1,Ver histórico de uploads
display(spark.sql(f"""
SELECT
  upload_id,
  schema_name,
  file_name,
  uploaded_at,
  row_count,
  volume_path
FROM {TARGET_CATALOG}.{TARGET_SCHEMA}.uploaded_files
ORDER BY uploaded_at DESC
"""))

# COMMAND ----------

# DBTITLE 1,Listar arquivos no Volume
files = dbutils.fs.ls(f"/Volumes/{TARGET_CATALOG}/{TARGET_SCHEMA}/uploads/")
print(f"Arquivos no Volume ({len(files)}):")
for f in files:
    size_kb = f.size / 1024
    print(f"  {f.name:60s}  {size_kb:.1f} KB")
