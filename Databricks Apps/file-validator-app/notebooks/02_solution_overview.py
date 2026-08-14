# Databricks notebook source
# MAGIC %md
# MAGIC # File Validator App — Documentação Técnica da Solução
# MAGIC
# MAGIC **Versão:** 2.0 · **Ambiente:** cosin-aws-serverless · **Stack:** React + FastAPI + Pandera + Delta Lake
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 1. Arquitetura Geral
# MAGIC
# MAGIC ```
# MAGIC  USUÁRIO (Browser)
# MAGIC       │
# MAGIC       │  HTTPS
# MAGIC       ▼
# MAGIC ┌─────────────────────────────────────────────────────────────────────┐
# MAGIC │                    DATABRICKS APP                                    │
# MAGIC │  (file-validator-app-7474659847183384.aws.databricksapps.com)        │
# MAGIC │                                                                       │
# MAGIC │  ┌─────────────────────────────┐   ┌──────────────────────────────┐ │
# MAGIC │  │      React Frontend          │   │      FastAPI Backend          │ │
# MAGIC │  │  Vite · TypeScript · Tailwind│   │  Python · Uvicorn · port 8000│ │
# MAGIC │  │                             │   │                              │ │
# MAGIC │  │  Tab 1: File Validator      │◀─▶│  GET  /api/schemas           │ │
# MAGIC │  │    - Dropdown de schemas    │   │  POST /api/schemas           │ │
# MAGIC │  │    - Drag-and-drop upload   │   │  PUT  /api/schemas/{id}      │ │
# MAGIC │  │    - Tabela de erros        │   │  DEL  /api/schemas/{id}      │ │
# MAGIC │  │    - Botão Confirmar Upload │   │  POST /api/validate          │ │
# MAGIC │  │                             │   │  POST /api/upload            │ │
# MAGIC │  │  Tab 2: Schema Manager      │   │           │                  │ │
# MAGIC │  │    - Lista de schemas       │   │           ▼                  │ │
# MAGIC │  │    - Editor de campos       │   │  ┌───────────────────────┐   │ │
# MAGIC │  │      (tipo/tamanho/regra)   │   │  │    validator.py       │   │ │
# MAGIC │  └─────────────────────────────┘   │  │  (Pandera engine)     │   │ │
# MAGIC │                                    │  └───────────────────────┘   │ │
# MAGIC │  Arquivos estáticos servidos pelo  │           │                  │ │
# MAGIC │  FastAPI via StaticFiles           │           ▼                  │ │
# MAGIC │  (frontend/dist → /assets/*)       │  ┌───────────────────────┐   │ │
# MAGIC │                                    │  │      db.py            │   │ │
# MAGIC │                                    │  │ Databricks SQL Conn.  │   │ │
# MAGIC │                                    │  └───────────────────────┘   │ │
# MAGIC │                                    └──────────────────────────────┘ │
# MAGIC └──────────────────────────────────────────────┬──────────────────────┘
# MAGIC                                                │
# MAGIC               ┌────────────────────────────────┼────────────────────────┐
# MAGIC               │            UNITY CATALOG        │                        │
# MAGIC               │   cosin_aws_serverless_catalog  │                        │
# MAGIC               │                                 ▼                        │
# MAGIC               │   schema: file_validator                                 │
# MAGIC               │   ┌─────────────────────────────────────────────────┐   │
# MAGIC               │   │  Δ file_schemas      — definições de validação  │   │
# MAGIC               │   │  Δ uploaded_files    — histórico + amostra      │   │
# MAGIC               │   │  📁 Volume: uploads  — arquivos originais       │   │
# MAGIC               │   └─────────────────────────────────────────────────┘   │
# MAGIC               └─────────────────────────────────────────────────────────┘
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Fluxo Completo — Validação e Upload de Arquivo
# MAGIC
# MAGIC ```
# MAGIC  ┌────────────────────────────────────────────────────────────────────────────┐
# MAGIC  │  TAB "FILE VALIDATOR" (FileValidator.tsx)                                  │
# MAGIC  │                                                                            │
# MAGIC  │  1. Página carrega → GET /api/schemas → preenche dropdown                 │
# MAGIC  │                                                                            │
# MAGIC  │  2. Usuário seleciona schema no dropdown                                   │
# MAGIC  │                                                                            │
# MAGIC  │  3. Usuário arrasta/seleciona arquivo (CSV ou Excel)                       │
# MAGIC  │         │                                                                  │
# MAGIC  │         ▼  dispara imediatamente ao selecionar                             │
# MAGIC  │     POST /api/validate  (multipart: file + schema_id)                     │
# MAGIC  │         │                                                                  │
# MAGIC  │         │  Backend:                                                        │
# MAGIC  │         │  ├─ _read_upload() → pd.read_csv / pd.read_excel (dtype=str)    │
# MAGIC  │         │  ├─ Carrega campos do schema da tabela file_schemas              │
# MAGIC  │         │  ├─ _build_pandera_schema(fields) → pa.DataFrameSchema          │
# MAGIC  │         │  └─ schema.validate(df, lazy=True)                              │
# MAGIC  │         │                                                                  │
# MAGIC  │         ├─── FALHOU ──────────────────────────────────────────────────▶   │
# MAGIC  │         │    Retorna {valid: false, errors: [{row, column, error},...]}    │
# MAGIC  │         │    Frontend: mostra tabela de erros em vermelho                  │
# MAGIC  │         │             botão "Confirmar Upload" DESABILITADO                │
# MAGIC  │         │                                                                  │
# MAGIC  │         └─── PASSOU ──────────────────────────────────────────────────▶   │
# MAGIC  │              Retorna {valid: true, errors: [], row_count: N}              │
# MAGIC  │              Frontend: banner verde "Validação aprovada"                   │
# MAGIC  │                       botão "Confirmar Upload" HABILITADO                  │
# MAGIC  │                                                                            │
# MAGIC  │  4. Usuário clica "Confirmar Upload"                                       │
# MAGIC  │         │                                                                  │
# MAGIC  │         ▼                                                                  │
# MAGIC  │     POST /api/upload  (multipart: file + schema_id)                       │
# MAGIC  │         │                                                                  │
# MAGIC  │         │  Backend:                                                        │
# MAGIC  │         │  ├─ Lê raw_bytes ANTES de parsear (preserva arquivo original)   │
# MAGIC  │         │  ├─ Re-valida com Pandera (segurança)                           │
# MAGIC  │         │  ├─ _upload_to_volume() → PUT /api/2.0/fs/files/Volumes/...     │
# MAGIC  │         │  │    Arquivo original salvo INTACTO no Volume                  │
# MAGIC  │         │  ├─ df.head(10).to_json() → amostra 10 linhas                  │
# MAGIC  │         │  └─ INSERT INTO uploaded_files (sample + volume_path)           │
# MAGIC  │         │                                                                  │
# MAGIC  │         └─── Retorna {upload_id, row_count, volume_path}                  │
# MAGIC  │              Frontend: mensagem de sucesso com contagem de linhas          │
# MAGIC  └────────────────────────────────────────────────────────────────────────────┘
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Fluxo — Cadastro de Schema
# MAGIC
# MAGIC ```
# MAGIC  ┌────────────────────────────────────────────────────────────────────────────┐
# MAGIC  │  TAB "SCHEMA MANAGER" (SchemaManager.tsx)                                  │
# MAGIC  │                                                                            │
# MAGIC  │  Carrega → GET /api/schemas → lista cards com nome/campos/data            │
# MAGIC  │                                                                            │
# MAGIC  │  + Novo Schema                                                             │
# MAGIC  │    │                                                                       │
# MAGIC  │    ▼                                                                       │
# MAGIC  │  Formulário inline na página:                                              │
# MAGIC  │  ┌────────────────────────────────────────────────────────────────┐        │
# MAGIC  │  │  Nome do Schema: [___________________________]                  │        │
# MAGIC  │  │                                                                 │        │
# MAGIC  │  │  Campo │   Tipo    │  Tamanho*  │ Obrig. │  Regra de Validação │        │
# MAGIC  │  │  ──────┼──────────┼────────────┼────────┼────────────────────  │        │
# MAGIC  │  │  [txt] │ [select] │ [select]** │  [✓]   │ [select]***         │        │
# MAGIC  │  │                                                                 │        │
# MAGIC  │  │  * Tamanho: só habilitado para tipo "string"                   │        │
# MAGIC  │  │  ** Opções: 10/20/50/100/200/500/unlimited                    │        │
# MAGIC  │  │  *** Opções filtradas pelo tipo do campo:                      │        │
# MAGIC  │  │       Todos:    NO_NULL, NO_DUPLICATE, Regex customizado       │        │
# MAGIC  │  │       Numeric:  POSITIVE, NON_NEGATIVE, IN_RANGE:min:max       │        │
# MAGIC  │  │       String:   NO_WHITESPACE, UPPERCASE, LOWERCASE, EMAIL     │        │
# MAGIC  │  └────────────────────────────────────────────────────────────────┘        │
# MAGIC  │    │                                                                       │
# MAGIC  │    ▼  Salvar                                                               │
# MAGIC  │  POST /api/schemas  →  INSERT INTO file_schemas                           │
# MAGIC  │  PUT  /api/schemas/{id}  →  UPDATE file_schemas (edição)                  │
# MAGIC  │  DEL  /api/schemas/{id}  →  DELETE FROM file_schemas                      │
# MAGIC  └────────────────────────────────────────────────────────────────────────────┘
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Funções do Backend — Mapa Completo
# MAGIC
# MAGIC ### `server/db.py` — Camada de Dados
# MAGIC
# MAGIC | Função / Constante | Tipo | Descrição |
# MAGIC |---|---|---|
# MAGIC | `CATALOG` | constante | `cosin_aws_serverless_catalog` |
# MAGIC | `DB_SCHEMA` | constante | `file_validator` |
# MAGIC | `SCHEMA_TABLE` | constante | `{CATALOG}.{DB_SCHEMA}.file_schemas` |
# MAGIC | `UPLOAD_TABLE` | constante | `{CATALOG}.{DB_SCHEMA}.uploaded_files` |
# MAGIC | `UPLOAD_VOLUME_PATH` | constante | `/Volumes/{CATALOG}/{DB_SCHEMA}/uploads` |
# MAGIC | `get_connection()` | função | Cria conexão via Databricks SQL Connector usando `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `WAREHOUSE_ID` |
# MAGIC | `execute_query(sql)` | função | Executa SELECT, retorna `list[dict]` |
# MAGIC | `execute_statement(sql)` | função | Executa INSERT/UPDATE/DELETE |
# MAGIC | `init_tables()` | função | Cria volume + tabelas se não existirem; adiciona coluna `volume_path` via ALTER TABLE se necessário |
# MAGIC
# MAGIC ### `server/validator.py` — Motor de Validação (Pandera)
# MAGIC
# MAGIC | Função | Entrada | Saída | Descrição |
# MAGIC |---|---|---|---|
# MAGIC | `_checks_for_field(field)` | `SchemaField` | `list[pa.Check]` | Converte a regra de validação do campo em lista de `pa.Check` do Pandera |
# MAGIC | `_build_pandera_schema(fields)` | `list[SchemaField]` | `pa.DataFrameSchema` | Constrói o schema Pandera completo com todas as colunas e regras |
# MAGIC | `validate_dataframe(df, fields)` | `pd.DataFrame`, `list[SchemaField]` | `list[ValidationError]` | Orquestra a validação: verifica colunas ausentes, normaliza nomes, executa `schema.validate(df, lazy=True)` e converte erros do Pandera para o modelo da API |
# MAGIC
# MAGIC ### `server/routes.py` — Endpoints da API
# MAGIC
# MAGIC | Função | Endpoint | Método | Descrição |
# MAGIC |---|---|---|---|
# MAGIC | `list_schemas()` | `/api/schemas` | GET | Lista todos os schemas do Delta; faz parse do JSON de `fields` |
# MAGIC | `create_schema(body)` | `/api/schemas` | POST | Gera UUID, serializa `fields` como JSON, faz INSERT |
# MAGIC | `update_schema(id, body)` | `/api/schemas/{id}` | PUT | Atualiza nome e campos via UPDATE |
# MAGIC | `delete_schema(id)` | `/api/schemas/{id}` | DELETE | Remove schema via DELETE |
# MAGIC | `validate_file(file, schema_id)` | `/api/validate` | POST | Lê arquivo → DataFrame, carrega schema, executa `validate_dataframe()`, retorna `ValidationResult` |
# MAGIC | `upload_file(file, schema_id)` | `/api/upload` | POST | Lê raw bytes, re-valida, chama `_upload_to_volume()`, grava amostra (10 linhas) no Delta |
# MAGIC | `_upload_to_volume(path, data)` | interno | — | PUT para `/api/2.0/fs/files{path}` com Bearer token; salva arquivo original intacto |
# MAGIC | `_read_upload(file)` | interno | — | `pd.read_csv` ou `pd.read_excel` com `dtype=str, keep_default_na=False` |
# MAGIC | `_sql_escape(value)` | interno | — | Escapa `\` e `'` para embutir strings em SQL |
# MAGIC | `_parse_fields_json(raw)` | interno | — | Parse robusto do JSON de campos (corrige backslashes escapados em excesso) |
# MAGIC | `_serialize_row(row)` | interno | — | Converte `datetime`/`date` para ISO string em dicts retornados pela SQL |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Motor de Validação — Pandera em Detalhe
# MAGIC
# MAGIC ### Pipeline interno de `validate_dataframe()`
# MAGIC
# MAGIC ```
# MAGIC  validate_dataframe(df, fields)
# MAGIC       │
# MAGIC       ├─ 1. Verifica colunas obrigatórias ausentes
# MAGIC       │       ↳ se encontrar: retorna erros imediatamente (row=0)
# MAGIC       │
# MAGIC       ├─ 2. Renomeia colunas do df para nomes canônicos do schema
# MAGIC       │       (case-insensitive: "NOME" → "nome")
# MAGIC       │
# MAGIC       ├─ 3. _build_pandera_schema(present_fields)
# MAGIC       │       │
# MAGIC       │       └─ Para cada campo:
# MAGIC       │            ├─ dtype   = DTYPE_MAP[field.datatype]
# MAGIC       │            ├─ nullable = not field.required
# MAGIC       │            ├─ coerce  = True  ← converte tipos automaticamente
# MAGIC       │            └─ checks  = _checks_for_field(field)
# MAGIC       │                           │
# MAGIC       │                           ├─ size check  (pa.Check: str.len <= n)
# MAGIC       │                           └─ rule check  (mapeado abaixo)
# MAGIC       │
# MAGIC       ├─ 4. schema.validate(df, lazy=True)
# MAGIC       │       ↳ lazy=True: coleta TODOS os erros em uma única passagem
# MAGIC       │         (sem lazy, para no primeiro erro)
# MAGIC       │
# MAGIC       └─ 5. Converte SchemaErrors.failure_cases → list[ValidationError]
# MAGIC                Traduz check names internos do Pandera para PT-BR
# MAGIC ```
# MAGIC
# MAGIC ### Mapeamento de tipos (`DTYPE_MAP`)
# MAGIC
# MAGIC | Campo no app | Pandera dtype | Coerção automática |
# MAGIC |---|---|---|
# MAGIC | `string` | `str` | — (mantém string) |
# MAGIC | `integer` | `pa.Int64` | `"42"` → `42`, `"42.0"` → `42` |
# MAGIC | `decimal` | `pa.Float64` | `"3.14"` → `3.14` |
# MAGIC | `date` | `pa.DateTime` | `"2024-01-15"` → `Timestamp('2024-01-15')` |
# MAGIC | `datetime` | `pa.DateTime` | `"2024-01-15 10:00:00"` → `Timestamp(...)` |
# MAGIC | `boolean` | `pa.Bool` | `"true"/"1"/"yes"` → `True` |
# MAGIC
# MAGIC ### Mapeamento de regras → `pa.Check`
# MAGIC
# MAGIC | Regra (UI) | `pa.Check` gerado | Nível | Tipos |
# MAGIC |---|---|---|---|
# MAGIC | `required=True` ou `NO_NULL` | `nullable=False` na `pa.Column` | coluna | todos |
# MAGIC | `NO_DUPLICATE` | `pa.Check(lambda s: ~s.duplicated(), element_wise=False)` | série | todos |
# MAGIC | `POSITIVE` | `pa.Check.gt(0)` | elemento | integer, decimal |
# MAGIC | `NON_NEGATIVE` | `pa.Check.ge(0)` | elemento | integer, decimal |
# MAGIC | `IN_RANGE:lo:hi` | `pa.Check.in_range(lo, hi)` | elemento | integer, decimal |
# MAGIC | `NO_WHITESPACE` | `pa.Check(lambda s: s == s.str.strip(), ...)` | série | string |
# MAGIC | `UPPERCASE` | `pa.Check(lambda s: s.map(lambda v: v == v.upper()), ...)` | série | string |
# MAGIC | `LOWERCASE` | `pa.Check(lambda s: s.map(lambda v: v == v.lower()), ...)` | série | string |
# MAGIC | `EMAIL` | `pa.Check.str_matches(r"^[\w.%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}$")` | elemento | string |
# MAGIC | `<regex>` | `pa.Check.str_matches(regex)` | elemento | todos |
# MAGIC | `string` + tamanho | `pa.Check(lambda s: s.str.len() <= n, ...)` | série | string |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Modelo de Dados — Tabelas Delta
# MAGIC
# MAGIC ### `file_schemas` — Definições de validação
# MAGIC
# MAGIC | Coluna | Tipo | Descrição |
# MAGIC |---|---|---|
# MAGIC | `schema_id` | STRING | UUID gerado no momento do POST |
# MAGIC | `schema_name` | STRING | Nome exibido no dropdown do app |
# MAGIC | `fields` | STRING | JSON array com definição dos campos (ver abaixo) |
# MAGIC | `created_at` | TIMESTAMP | Criação (UTC) |
# MAGIC | `updated_at` | TIMESTAMP | Última atualização (UTC) |
# MAGIC
# MAGIC **Estrutura do JSON armazenado em `fields`:**
# MAGIC ```json
# MAGIC [
# MAGIC   { "name": "nome",     "datatype": "string",  "size": "50",        "required": true,  "validation_rule": "NO_DUPLICATE" },
# MAGIC   { "name": "idade",    "datatype": "integer", "size": "unlimited", "required": true,  "validation_rule": "NON_NEGATIVE" },
# MAGIC   { "name": "email",    "datatype": "string",  "size": "100",       "required": true,  "validation_rule": "EMAIL"         },
# MAGIC   { "name": "salario",  "datatype": "decimal", "size": "unlimited", "required": false, "validation_rule": "IN_RANGE:0:999999" }
# MAGIC ]
# MAGIC ```
# MAGIC
# MAGIC ### `uploaded_files` — Histórico de uploads
# MAGIC
# MAGIC | Coluna | Tipo | Descrição |
# MAGIC |---|---|---|
# MAGIC | `upload_id` | STRING | UUID único do upload |
# MAGIC | `schema_name` | STRING | Nome do schema usado |
# MAGIC | `file_name` | STRING | Nome original do arquivo |
# MAGIC | `uploaded_at` | TIMESTAMP | Data/hora do upload (UTC) |
# MAGIC | `row_count` | INT | Total de linhas no arquivo |
# MAGIC | `data` | STRING | Amostra das **10 primeiras linhas** em JSON |
# MAGIC | `volume_path` | STRING | Caminho completo do arquivo original no Volume |
# MAGIC
# MAGIC ### Volume `uploads`
# MAGIC
# MAGIC Caminho: `/Volumes/cosin_aws_serverless_catalog/file_validator/uploads/`
# MAGIC
# MAGIC Convenção de nome: `{upload_id}_{nome_original_do_arquivo}`
# MAGIC
# MAGIC Ex: `3f8a1b2c-..._clientes_valido.csv`

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Estrutura de Arquivos do Projeto

# COMMAND ----------

# MAGIC %md
# MAGIC ```
# MAGIC file-validator-app/
# MAGIC │
# MAGIC ├── app.py                   ← FastAPI entry point
# MAGIC │                              Serve React SPA (frontend/dist)
# MAGIC │                              Registra router de /api/*
# MAGIC │                              Chama init_tables() no startup
# MAGIC │
# MAGIC ├── app.yaml                 ← Databricks App: comando uvicorn + env vars
# MAGIC │
# MAGIC ├── requirements.txt         ← fastapi, uvicorn, databricks-sql-connector,
# MAGIC │                              databricks-sdk, pandas, pandera, openpyxl,
# MAGIC │                              pydantic, python-multipart, requests
# MAGIC │
# MAGIC ├── server/
# MAGIC │   ├── db.py                ← Constantes (CATALOG, SCHEMA, tabelas, volume)
# MAGIC │   │                          get_connection() / execute_query() / execute_statement()
# MAGIC │   │                          init_tables() — cria schema/tabelas/volume
# MAGIC │   │
# MAGIC │   ├── models.py            ← Pydantic models:
# MAGIC │   │                          SchemaField(name, datatype, size, required, validation_rule)
# MAGIC │   │                          SchemaCreate / SchemaUpdate
# MAGIC │   │                          ValidationError(row, column, error)
# MAGIC │   │                          ValidationResult(valid, errors, row_count)
# MAGIC │   │
# MAGIC │   ├── routes.py            ← APIRouter com todos os endpoints
# MAGIC │   │                          Helpers: _sql_escape, _parse_fields_json,
# MAGIC │   │                                   _serialize_row, _read_upload,
# MAGIC │   │                                   _upload_to_volume
# MAGIC │   │
# MAGIC │   └── validator.py         ← Motor Pandera:
# MAGIC │                              DTYPE_MAP, EMAIL_PATTERN
# MAGIC │                              _checks_for_field(field) → list[pa.Check]
# MAGIC │                              _build_pandera_schema(fields) → DataFrameSchema
# MAGIC │                              validate_dataframe(df, fields) → list[ValidationError]
# MAGIC │
# MAGIC ├── frontend/
# MAGIC │   ├── src/
# MAGIC │   │   ├── App.tsx           ← Tabs: File Validator (padrão) | Schema Manager
# MAGIC │   │   ├── types.ts          ← SchemaField, FileSchema, ValidationError interfaces
# MAGIC │   │   ├── hooks/useApi.ts   ← useSchemas() hook (CRUD + estado)
# MAGIC │   │   └── components/
# MAGIC │   │       ├── FileValidator.tsx   ← Upload + validação + confirmar
# MAGIC │   │       └── SchemaManager.tsx   ← CRUD + editor de campos inline
# MAGIC │   │
# MAGIC │   └── dist/                ← Build de produção (npm run build)
# MAGIC │                              Servido pelo FastAPI em /* (SPA fallback)
# MAGIC │
# MAGIC ├── notebooks/
# MAGIC │   ├── 01_setup_environment.py  ← Cria infra (schema/tabelas/volume/app)
# MAGIC │   └── 02_solution_overview.py  ← Este notebook
# MAGIC │
# MAGIC └── test-files/              ← Arquivos de exemplo para testes
# MAGIC     ├── clientes_valido.csv
# MAGIC     ├── clientes_valido.xlsx
# MAGIC     ├── clientes_erros.csv   ← contém 7 erros propositais
# MAGIC     ├── clientes_erros.xlsx
# MAGIC     ├── produtos_valido.xlsx
# MAGIC     └── produtos_erros.csv   ← contém 5 erros propositais
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Dados Ativos — Estado Atual do Ambiente

# COMMAND ----------

CATALOG = "cosin_aws_serverless_catalog"
SCHEMA  = "file_validator"

# COMMAND ----------

# DBTITLE 1,Estrutura das tabelas Delta
print("=" * 60)
print(f"TABELA: {CATALOG}.{SCHEMA}.file_schemas")
print("=" * 60)
spark.sql(f"DESCRIBE TABLE {CATALOG}.{SCHEMA}.file_schemas").show(truncate=False)

print("=" * 60)
print(f"TABELA: {CATALOG}.{SCHEMA}.uploaded_files")
print("=" * 60)
spark.sql(f"DESCRIBE TABLE {CATALOG}.{SCHEMA}.uploaded_files").show(truncate=False)

# COMMAND ----------

# DBTITLE 1,Schemas de validação cadastrados
import json

schemas = spark.sql(f"""
  SELECT schema_id, schema_name, fields, created_at, updated_at
  FROM {CATALOG}.{SCHEMA}.file_schemas
  ORDER BY schema_name
""").collect()

print(f"Total de schemas cadastrados: {len(schemas)}\n")
for s in schemas:
    fields = json.loads(s["fields"]) if s["fields"] else []
    print(f"{'─' * 60}")
    print(f"📋  {s['schema_name']}   [{s['schema_id'][:8]}...]")
    print(f"    Criado: {s['created_at']} | Atualizado: {s['updated_at']}")
    print(f"    {'Campo':<22} {'Tipo':<10} {'Tam':<12} {'Obrig':<6}  Regra")
    print(f"    {'─'*22} {'─'*10} {'─'*12} {'─'*6}  {'─'*25}")
    for f in fields:
        obrig = "✅ Sim" if f.get("required") else "   Não"
        regra = f.get("validation_rule") or "—"
        tam   = f.get("size", "unlimited") if f.get("datatype") == "string" else "N/A"
        print(f"    {f['name']:<22} {f['datatype']:<10} {tam:<12} {obrig}  {regra}")
    print()

# COMMAND ----------

# DBTITLE 1,Histórico de uploads
display(spark.sql(f"""
  SELECT
    upload_id,
    schema_name,
    file_name,
    uploaded_at,
    row_count,
    SUBSTRING(volume_path, LENGTH(volume_path) - 50) AS volume_path_short
  FROM {CATALOG}.{SCHEMA}.uploaded_files
  ORDER BY uploaded_at DESC
  LIMIT 20
"""))

# COMMAND ----------

# DBTITLE 1,Amostra do upload mais recente
import json

row = spark.sql(f"""
  SELECT upload_id, schema_name, file_name, row_count, data, volume_path
  FROM {CATALOG}.{SCHEMA}.uploaded_files
  ORDER BY uploaded_at DESC
  LIMIT 1
""").collect()

if row:
    r = row[0]
    print(f"upload_id  : {r['upload_id']}")
    print(f"schema     : {r['schema_name']}")
    print(f"arquivo    : {r['file_name']}  ({r['row_count']} linhas no total)")
    print(f"volume     : {r['volume_path']}")
    print(f"\nAmostra armazenada (primeiras 10 linhas):")
    sample = json.loads(r["data"])
    for i, linha in enumerate(sample, 1):
        print(f"  [{i:02d}] {linha}")
else:
    print("Nenhum upload registrado ainda.")

# COMMAND ----------

# DBTITLE 1,Arquivos no Volume
try:
    files = dbutils.fs.ls(f"/Volumes/{CATALOG}/{SCHEMA}/uploads/")
    print(f"Volume: /Volumes/{CATALOG}/{SCHEMA}/uploads/")
    print(f"{'─' * 75}")
    print(f"  {'Arquivo':<55}  {'Tamanho':>10}  Modificado")
    print(f"  {'─'*55}  {'─'*10}  {'─'*20}")
    total = 0
    for f in sorted(files, key=lambda x: x.modificationTime, reverse=True):
        from datetime import datetime
        ts = datetime.fromtimestamp(f.modificationTime / 1000).strftime("%Y-%m-%d %H:%M")
        size_kb = f.size / 1024
        total += f.size
        print(f"  {f.name:<55}  {size_kb:>9.1f}K  {ts}")
    print(f"  {'─'*55}  {'─'*10}")
    print(f"  {'Total (' + str(len(files)) + ' arquivo(s))':<55}  {total/1024:>9.1f}K")
except Exception as e:
    print(f"Volume vazio ou não encontrado: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Demonstração — Validação Programática com Pandera
# MAGIC
# MAGIC O bloco abaixo replica exatamente o que o app faz internamente ao chamar `POST /api/validate`.

# COMMAND ----------

# DBTITLE 1,Simular validação de um arquivo de teste
import sys
sys.path.insert(0, "/Workspace/Users/rodrigo.cosin@databricks.com/file-validator-app")

import pandas as pd
import pandera as pa
from server.validator import _build_pandera_schema
from server.models import SchemaField

# Schema de exemplo: Clientes
fields = [
    SchemaField(name="nome",            datatype="string",  size="50",        required=True,  validation_rule="NO_DUPLICATE"),
    SchemaField(name="idade",           datatype="integer", size="unlimited", required=True,  validation_rule="NON_NEGATIVE"),
    SchemaField(name="email",           datatype="string",  size="100",       required=True,  validation_rule="EMAIL"),
    SchemaField(name="data_nascimento", datatype="date",    size="unlimited", required=True,  validation_rule=""),
    SchemaField(name="ativo",           datatype="boolean", size="unlimited", required=True,  validation_rule=""),
    SchemaField(name="salario",         datatype="decimal", size="unlimited", required=False, validation_rule="POSITIVE"),
]

# Mostre o schema Pandera gerado
schema = _build_pandera_schema(fields)
print("DataFrameSchema gerado pelo app:")
print(schema)

# COMMAND ----------

# DBTITLE 1,Testar com dados inválidos
from server.validator import validate_dataframe

df_erros = pd.DataFrame({
    "nome":            ["Ana",       "",            "Carla",           "Ana"],          # duplicado + vazio
    "idade":           ["30",        "45",          "vinte",           "52"],            # tipo inválido
    "email":           ["a@b.com",   "b@c.com",     "email-invalido",  "d@e.com"],      # email inválido
    "data_nascimento": ["1994-05-12","1979-11-03",  "1996-03-22",      "1972-08-15"],
    "ativo":           ["true",      "true",        "false",           "talvez"],       # bool inválido
    "salario":         ["4500.00",   "8200.50",     "3100.00",         "-100"],         # salario negativo
})

errors = validate_dataframe(df_erros, fields)
print(f"Erros encontrados: {len(errors)}\n")
for e in errors:
    print(f"  Linha {e.row:>3} | {e.column:<20} | {e.error}")

# COMMAND ----------

# DBTITLE 1,Testar com dados válidos
df_valido = pd.DataFrame({
    "nome":            ["Ana Silva", "Bruno Costa", "Carla Mendes"],
    "idade":           ["30",        "45",          "28"],
    "email":           ["ana@email.com", "bruno@email.com", "carla@email.com"],
    "data_nascimento": ["1994-05-12", "1979-11-03", "1996-03-22"],
    "ativo":           ["true",       "true",       "false"],
    "salario":         ["4500.00",    "8200.50",    "3100.00"],
})

errors = validate_dataframe(df_valido, fields)
if not errors:
    print("✅ Validação aprovada! 0 erros encontrados.")
else:
    print(f"❌ {len(errors)} erro(s) encontrado(s).")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Consultas Analíticas

# COMMAND ----------

# DBTITLE 1,Uploads por schema (volume e frequência)
display(spark.sql(f"""
  SELECT
    schema_name,
    COUNT(*)            AS total_uploads,
    SUM(row_count)      AS total_linhas,
    AVG(row_count)      AS media_linhas,
    MIN(uploaded_at)    AS primeiro_upload,
    MAX(uploaded_at)    AS ultimo_upload,
    DATEDIFF(MAX(uploaded_at), MIN(uploaded_at)) AS dias_em_uso
  FROM {CATALOG}.{SCHEMA}.uploaded_files
  GROUP BY schema_name
  ORDER BY total_uploads DESC
"""))

# COMMAND ----------

# DBTITLE 1,Tamanho físico das tabelas Delta
for table in ["file_schemas", "uploaded_files"]:
    result = spark.sql(f"DESCRIBE DETAIL {CATALOG}.{SCHEMA}.{table}").collect()[0]
    size_mb = (result["sizeInBytes"] or 0) / (1024 * 1024)
    n_files = result["numFiles"] or 0
    print(f"  Δ {table:<30}  {size_mb:.3f} MB  ({n_files} arquivo(s) Parquet)")

# COMMAND ----------

# DBTITLE 1,Ler arquivo original do Volume como DataFrame
try:
    files = dbutils.fs.ls(f"/Volumes/{CATALOG}/{SCHEMA}/uploads/")
    csv_files = [f for f in files if ".csv" in f.name.lower()]
    if csv_files:
        latest = sorted(csv_files, key=lambda x: x.modificationTime, reverse=True)[0]
        print(f"Lendo: {latest.path}")
        df_original = spark.read.option("header", "true").csv(latest.path)
        print(f"Shape: {df_original.count()} linhas × {len(df_original.columns)} colunas")
        display(df_original)
    else:
        print("Nenhum CSV no Volume ainda.")
except Exception as e:
    print(f"Erro: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Referências e Links
# MAGIC
# MAGIC | Recurso | URL |
# MAGIC |---|---|
# MAGIC | App (produção) | https://file-validator-app-7474659847183384.aws.databricksapps.com |
# MAGIC | Logs do App | https://file-validator-app-7474659847183384.aws.databricksapps.com/logz |
# MAGIC | Pandera Docs | https://pandera.readthedocs.io/en/stable/ |
# MAGIC | Databricks Apps Docs | https://docs.databricks.com/en/dev-tools/databricks-apps/index.html |
# MAGIC | Databricks Files API | https://docs.databricks.com/api/workspace/files |
# MAGIC | Código-fonte (Workspace) | /Users/rodrigo.cosin@databricks.com/file-validator-app/ |
