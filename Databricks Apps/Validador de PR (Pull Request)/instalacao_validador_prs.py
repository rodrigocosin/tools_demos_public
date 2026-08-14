# Databricks notebook source
# MAGIC %md
# MAGIC # Instalação - Validador Automático de PRs
# MAGIC
# MAGIC Este notebook prepara o ambiente Databricks para rodar o app **`validador-prs`**, que valida a conformidade de notebooks Databricks (formato `.py` e `.ipynb`) contra um conjunto de regras parametrizáveis armazenadas em uma tabela Delta.
# MAGIC
# MAGIC O que este notebook faz:
# MAGIC 1. Cria o catálogo, schema e a **tabela de regras** (`tb_validacao_regras`).
# MAGIC 2. Faz a **carga inicial das 25 regras** que estão hoje em produção - o app já sobe pronto para uso.
# MAGIC 3. Explica a estrutura do código fonte do app.
# MAGIC 4. Aponta os componentes principais (tabela, LLM, etc.) para customização.
# MAGIC
# MAGIC ## Arquitetura resumida
# MAGIC
# MAGIC ```
# MAGIC  ┌──────────────────┐    POST /api/validate     ┌──────────────────────┐
# MAGIC  │  Browser (HTML)  │ ─────────────────────────▶│  FastAPI (uvicorn)   │
# MAGIC  └──────────────────┘                           │   app.main:app       │
# MAGIC                                                 └──────────┬───────────┘
# MAGIC                                                            │
# MAGIC                                ┌───────────────────────────┼────────────────────────────┐
# MAGIC                                ▼                           ▼                            ▼
# MAGIC                       ┌────────────────┐         ┌──────────────────┐         ┌────────────────────┐
# MAGIC                       │ notebook_parser│         │  rule_loader     │         │  llm_assistant     │
# MAGIC                       │ (.py / .ipynb) │         │  (cache 5 min)   │         │ Foundation Model   │
# MAGIC                       └────────────────┘         └────────┬─────────┘         │ Claude Sonnet 4.6  │
# MAGIC                                                           │                   └────────────────────┘
# MAGIC                                                           ▼
# MAGIC                                                 ┌──────────────────┐
# MAGIC                                                 │  db_client.py    │
# MAGIC                                                 │  Statement Exec. │
# MAGIC                                                 │  API + Warehouse │
# MAGIC                                                 └────────┬─────────┘
# MAGIC                                                          ▼
# MAGIC                                          tb_validacao_regras (Delta)
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Pré-requisitos
# MAGIC
# MAGIC | Recurso | Necessidade |
# MAGIC |---------|-------------|
# MAGIC | Unity Catalog habilitado | Sim |
# MAGIC | Permissão `CREATE CATALOG` ou catálogo já existente | Sim |
# MAGIC | SQL Warehouse Serverless | Sim - usado pelo app via Statement Execution API |
# MAGIC | Foundation Model `databricks-claude-sonnet-4-6` habilitado | Apenas se for usar geração de regra com IA |
# MAGIC | Databricks App `validador-prs` criado | Sim - para deploy |
# MAGIC
# MAGIC > **Importante:** O Service Principal do app precisa de:
# MAGIC > - `USE CATALOG`, `USE SCHEMA` no catálogo/schema da tabela
# MAGIC > - `SELECT, INSERT, UPDATE, DELETE` na `tb_validacao_regras`
# MAGIC > - `CAN USE` no SQL Warehouse configurado em `SQL_WAREHOUSE_HTTP_PATH`
# MAGIC > - `CAN QUERY` no endpoint `databricks-claude-sonnet-4-6`

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Parâmetros
# MAGIC
# MAGIC Ajuste catálogo, schema e nome da tabela. Os defaults batem com `app.yaml`.

# COMMAND ----------

dbutils.widgets.text("catalog", "cosin_aws_serverless_catalog", "Catálogo")
dbutils.widgets.text("schema", "pr_review", "Schema")
dbutils.widgets.text("table", "tb_validacao_regras", "Tabela de regras")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
TABLE = dbutils.widgets.get("table")

FQN = f"{CATALOG}.{SCHEMA}.{TABLE}"
print(f"Tabela alvo: {FQN}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Criar catálogo e schema (idempotente)

# COMMAND ----------

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Catálogo e schema prontos: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. CREATE TABLE - `tb_validacao_regras`
# MAGIC
# MAGIC Esquema lido diretamente de `app/db_client.py` (funções `insert_rule`, `update_rule`, `list_*_rules`).
# MAGIC
# MAGIC **Significado das colunas:**
# MAGIC
# MAGIC | Coluna | Tipo | Descrição |
# MAGIC |--------|------|-----------|
# MAGIC | `rule_id` | STRING | Identificador único, snake_case, 3-80 chars (validado em `app/main.py` por `_SAFE_ID_PATTERN`) |
# MAGIC | `rule_type` | STRING | Um dos 13 tipos válidos (ver `VALID_RULE_TYPES` em `app/llm_assistant.py`) |
# MAGIC | `category` | STRING | Categoria livre exibida no relatório (ex: "Nomenclatura", "Cabeçalho") |
# MAGIC | `severity` | STRING | `erro` ou `aviso` |
# MAGIC | `message_ok` | STRING | Mensagem quando a regra passa (opcional) |
# MAGIC | `message_fail` | STRING | Mensagem quando a regra falha (obrigatório) |
# MAGIC | `details_fail` | STRING | Texto de detalhe/dica para correção |
# MAGIC | `params` | STRING | **JSON** com parâmetros específicos do `rule_type` |
# MAGIC | `enabled` | BOOLEAN | Se `false`, regra é ignorada |
# MAGIC | `priority` | INT | Ordem de execução (menor primeiro) - usado em `ORDER BY` |
# MAGIC | `created_at` | TIMESTAMP | Preenchido automaticamente |
# MAGIC | `updated_at` | TIMESTAMP | Atualizado a cada `UPDATE` |

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {FQN} (
    rule_id      STRING    NOT NULL,
    rule_type    STRING    NOT NULL,
    category     STRING    NOT NULL,
    severity     STRING    NOT NULL,
    message_ok   STRING,
    message_fail STRING    NOT NULL,
    details_fail STRING,
    params       STRING,
    enabled      BOOLEAN   NOT NULL DEFAULT TRUE,
    priority     INT       NOT NULL DEFAULT 100,
    created_at   TIMESTAMP NOT NULL DEFAULT current_timestamp(),
    updated_at   TIMESTAMP NOT NULL DEFAULT current_timestamp(),
    CONSTRAINT pk_validacao_regras PRIMARY KEY (rule_id),
    CONSTRAINT chk_severity        CHECK (severity IN ('erro', 'aviso')),
    CONSTRAINT chk_rule_type       CHECK (rule_type IN (
        'regex_must_exist', 'regex_must_not_exist', 'conditional_warning',
        'conditional_compound', 'notebook_name_pattern', 'table_prefix_check',
        'view_prefix_check', 'field_prefix_check', 'required_column_check',
        'comment_format_check', 'tag_value_check', 'tag_uppercase_check',
        'masking_check'
    ))
)
USING DELTA
COMMENT 'Regras dinâmicas do app validador-prs. Carregadas em cache de 5 min por app/validators/rule_loader.py'
TBLPROPERTIES (
    'delta.feature.allowColumnDefaults' = 'enabled',
    'delta.columnMapping.mode' = 'name'
)
""")

print(f"Tabela criada: {FQN}")
display(spark.sql(f"DESCRIBE TABLE {FQN}"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Carga inicial das 25 regras de produção
# MAGIC
# MAGIC As regras abaixo refletem o estado atual da tabela em produção
# MAGIC (`cosin_aws_serverless_catalog.pr_review.tb_validacao_regras`) no momento da geração deste notebook.
# MAGIC
# MAGIC Como a tabela está vazia ao instalar o app, a carga é feita com um `INSERT INTO` direto -
# MAGIC sem `MERGE`. **Não rode esta seção duas vezes** (vai duplicar). Se precisar reinstalar do zero,
# MAGIC trunque a tabela antes: `TRUNCATE TABLE <fqn>`.

# COMMAND ----------

import json

# Carga inicial: 25 regras agrupadas por categoria/priority crescente.
# Cada item: (rule_id, rule_type, category, severity, message_ok, message_fail, details_fail, params, enabled, priority)
RULES_SEED = [
    # --- Cabeçalho ---
    ("header_funcionalidade", "regex_must_exist", "Cabeçalho", "erro",
     "Célula Funcionalidade e objetivo encontrada.",
     "Célula Funcionalidade e objetivo NÃO encontrada.",
     "O notebook deve conter uma célula de cabeçalho com Funcionalidade e objetivo.",
     {"pattern": "funcionalidade\\s+e\\s+objetivo", "flags": "IGNORECASE", "search_scope": "full_code"},
     True, 10),
    ("header_versoes", "regex_must_exist", "Cabeçalho", "erro",
     "Célula Versões encontrada.",
     "Célula Versões NÃO encontrada.",
     "O notebook deve conter uma célula de cabeçalho com tabela de Versões.",
     {"pattern": "vers[õo]es", "flags": "IGNORECASE", "search_scope": "full_code"},
     True, 11),
    ("header_versoes_warning", "conditional_warning", "Cabeçalho", "aviso",
     None,
     "Validar se houve atualização da versão do cabeçalho do notebook.",
     None,
     {"condition_pattern": "vers[õo]es", "flags": "IGNORECASE"},
     True, 12),

    # --- Informações Iniciais ---
    ("header_no_ddl", "regex_must_not_exist", "Informações Iniciais", "erro",
     "Nenhuma DDL CREATE OR REPLACE TABLE encontrada.",
     "Encontrada DDL CREATE OR REPLACE TABLE no notebook.",
     "Não deve constar DDL de criação de tabela no notebook.",
     {"pattern": "\\bCREATE\\s+OR\\s+REPLACE\\s+TABLE\\b", "flags": "IGNORECASE", "search_scope": "full_code"},
     True, 20),
    ("header_show_create", "regex_must_exist", "Informações Iniciais", "erro",
     "Comando SHOW CREATE TABLE encontrado.",
     "Comando SHOW CREATE TABLE NÃO encontrado.",
     "O notebook deve conter uma célula com o comando SHOW CREATE TABLE.",
     {"pattern": "\\bSHOW\\s+CREATE\\s+TABLE\\b", "flags": "IGNORECASE", "search_scope": "full_code"},
     True, 21),
    ("header_no_sandbox", "regex_must_not_exist", "Informações Iniciais", "erro",
     "Nenhuma referência ao catálogo 3_prd_sandbox.",
     "Referência ao catálogo 3_prd_sandbox encontrada.",
     "Não deve conter tabelas do catálogo 3_prd_sandbox no notebook.",
     {"pattern": "\\b3_prd_sandbox\\b", "flags": "IGNORECASE", "search_scope": "full_code"},
     True, 22),
    ("header_no_ingestao_in_ref_rel", "conditional_compound", "Informações Iniciais", "erro",
     "Notebook de schemas 3_ref/4_rel sem referências indevidas a 3_prd_ingestao.",
     "Referência a 3_prd_ingestao em notebook de schemas 3_ref/4_rel do catálogo lakehouse.",
     "Não deve conter tabelas do catálogo 3_prd_ingestao em notebooks de criação de tabelas dos schemas 3_ref e 4_rel.",
     {"conditions": [
         {"pattern": "\\b3_prd_lakehouse(?:_rwd)?\\b", "flags": "IGNORECASE"},
         {"pattern": "\\b(3_ref|4_rel)\\b", "flags": "IGNORECASE"},
         {"pattern": "\\b3_prd_ingestao\\b", "flags": "IGNORECASE"},
     ], "operator": "AND"},
     True, 23),

    # --- Localização do Notebook ---
    ("location_ingestao", "conditional_warning", "Localização do Notebook", "aviso",
     None,
     "Notebook referencia catálogo 3_prd_ingestao.",
     ("Se atentar quanto a localização do notebook, conforme classificação:\n"
      "  - 0_feature: notebooks parametrizáveis que podem ser aplicados para diversos sistemas, "
      "como integrações via API e arquivos Sharepoint;\n"
      "  - 1_raw: notebooks específicos e aplicados para ou por determinado sistema, "
      "como provenientes do TASY ou Forcare, por exemplo."),
     {"condition_pattern": "\\b3_prd_ingestao\\b", "flags": "IGNORECASE"},
     True, 30),
    ("location_ingestao_tag", "conditional_warning", "Localização do Notebook", "aviso",
     None,
     "Para novos schemas no catálogo 3_prd_ingestao, deverá haver a inclusão da Tag Governada tipo sistema.",
     None,
     {"condition_pattern": "\\b3_prd_ingestao\\b", "flags": "IGNORECASE"},
     True, 31),
    ("location_lakehouse", "conditional_warning", "Localização do Notebook", "aviso",
     None,
     "Notebook referencia catálogo lakehouse.",
     ("Se atentar quanto a localização do notebook, conforme classificação:\n"
      "  - Schemas iniciados com 2_tru: Notebook de criação de tabela de segunda camada;\n"
      "  - Schema 3_ref: Notebook de criação de tabela fato e dimensão;\n"
      "  - Schema 4_rel: Notebook de criação relatório;\n"
      "  - Schemas iniciados com 5_srv: Notebook de criação de tabela para terceiros ou parceiros. "
      "Validar com a liderança;\n"
      "  - Schema 6_ext: Notebook de criação de tabela para terceiros ou parceiros. "
      "Validar com a liderança."),
     {"condition_pattern": "\\b3_prd_lakehouse(?:_rwd)?\\b", "flags": "IGNORECASE"},
     True, 32),

    # --- Nomenclatura de Notebook ---
    ("naming_nb_ingestao", "notebook_name_pattern", "Nomenclatura de Notebook", "erro",
     "Nome do notebook segue o padrão para ingestão (nb_ingestao_[sistema]_[tabela]).",
     "Nome do notebook NÃO segue o padrão para ingestão.",
     "Para notebooks do catálogo 3_prd_ingestao, o nome deve seguir: nb_ingestao_[nome do sistema de origem]_[nome da tabela].",
     {"condition_pattern": "3_prd_ingestao", "name_prefix": "nb_ingestao_", "flags": "IGNORECASE"},
     True, 40),
    ("naming_nb_lakehouse", "notebook_name_pattern", "Nomenclatura de Notebook", "erro",
     "Nome do notebook segue o padrão para lakehouse (nb_[sistema]_[tabela]).",
     "Nome do notebook NÃO segue o padrão para lakehouse.",
     "Para notebooks dos catálogos 3_prd_lakehouse/3_prd_lakehouse_rwd, o nome deve seguir: nb_[nome do sistema de origem]_[nome da tabela].",
     {"condition_pattern": "3_prd_lakehouse", "name_prefix": "nb_", "name_exclude_prefix": "nb_ingestao_", "flags": "IGNORECASE"},
     True, 41),

    # --- Nomenclatura de Tabelas / Views / Campos ---
    ("naming_table_prefix", "table_prefix_check", "Nomenclatura de Tabelas", "erro",
     None,
     "Tabela não segue o prefixo correto para o schema.",
     None,
     {"catalog_pattern": "3_prd_lakehouse(_rwd)?",
      "schema_prefix_map": {"2_tru": ["tbl_tru_"], "3_ref": ["fat_", "dim_"], "4_rel": ["rel_"]}},
     True, 50),
    ("naming_view_prefix", "view_prefix_check", "Nomenclatura de Views", "erro",
     None,
     "View não segue o prefixo correto.",
     None,
     {"required_prefix": "vie_"},
     True, 60),
    ("naming_field_prefix", "field_prefix_check", "Nomenclatura de Campos", "erro",
     None,
     "Campo(s) não seguem os prefixos obrigatórios.",
     None,
     {"valid_prefixes": ["ano_", "cod_", "dat_", "dsc_", "dia_", "flg_", "grp_",
                          "mes_", "nom_", "num_", "prc_", "qtd_", "sgl_", "vlr_", "xml_"],
      "skip_if_only_catalog": "3_prd_ingestao"},
     True, 70),

    # --- Campos / Registros Obrigatórios ---
    ("required_fat_columns", "required_column_check", "Campos Obrigatórios", "erro",
     "Tabela fat_: campos obrigatórios dat_carga e sk_sistema_origem encontrados.",
     "Tabela fat_: campo(s) obrigatório(s) ausente(s).",
     "Para tabelas com prefixo fat_, devem constar as colunas dat_carga e sk_sistema_origem.",
     {"table_pattern": "\\bfat_\\w+", "required_columns": ["dat_carga", "sk_sistema_origem"], "flags": "IGNORECASE"},
     True, 80),
    ("required_dim_columns", "required_column_check", "Campos Obrigatórios", "erro",
     "Tabela dim_: campo obrigatório dat_carga encontrado.",
     "Tabela dim_: campo obrigatório dat_carga ausente.",
     "Para tabelas com prefixo dim_, deve constar a coluna dat_carga.",
     {"table_pattern": "\\bdim_\\w+", "required_columns": ["dat_carga"], "flags": "IGNORECASE"},
     True, 81),
    ("required_dim_record", "conditional_warning", "Registros Obrigatórios", "aviso",
     None,
     "Validar a presença do registro obrigatório -1.",
     ("Para tabelas dim_, deve existir o registro obrigatório:\n"
      "  CÓDIGO: -1 | DESCRIÇÃO: Não identificado | DESCRIÇÃO ABREVIADA: NI"),
     {"condition_pattern": "\\bdim_\\w+", "flags": "IGNORECASE"},
     True, 82),

    # --- Descrições ---
    ("descriptions_format", "comment_format_check", "Descrições", "erro",
     None,
     "Descrição(ões) não seguem o padrão (letra maiúscula + ponto final).",
     "Tabelas, views e campos devem conter descrição (COMMENT) com início em letra maiúscula e ponto final.",
     {"require_uppercase_start": True, "require_period_end": True},
     True, 90),

    # --- Tagueamento ---
    ("tags_value_check", "tag_value_check", "Tagueamento", "erro",
     None,
     "Tag com valor incorreto.",
     None,
     {"expected_table_values": {"PII": "CONTEM_PII", "PHI": "CONTEM_PHI", "ESTRATEGICA": "CONTEM_ESTRATEGICA"},
      "na_masking_value": "N/A_MASKING",
      "field_tag_pattern": "^[A-Z]+_[A-Z_]+$"},
     True, 100),
    ("tags_uppercase", "tag_uppercase_check", "Tagueamento", "erro",
     None,
     "Tag ou valor não está em letras maiúsculas.",
     "Todas as tags e valores devem estar em letras maiúsculas.",
     {},
     True, 101),

    # --- Mascaramento ---
    ("masking_nomenclature", "masking_check", "Mascaramento", "erro",
     None,
     "Função de mascaramento não segue o padrão.",
     "Padrão esperado: oc_mask_[grupo]_[informação mascarada]. Exemplo: oc_mask_paciente_nome.",
     {"function_pattern": "\\boc_mask_(\\w+)", "min_parts": 2, "default_schema": "3_prd_lakehouse.default"},
     True, 110),
    ("masking_evidence_warning", "conditional_warning", "Mascaramento", "aviso",
     None,
     'Será necessário a evidência com "De Acordo" dos responsáveis.',
     "Responsáveis: solicitante, líder imediato e Thiago Jordão.",
     {"condition_pattern": "\\boc_mask_\\w+", "flags": "IGNORECASE"},
     True, 111),
    ("masking_groups_warning", "conditional_warning", "Mascaramento", "aviso",
     None,
     "Será necessário validar a criação dos grupos de acesso.",
     ("Os grupos de acesso devem seguir o padrão de nomenclatura mask_[grupo]_[informação mascarada] "
      "e a inclusão dos usuários. Exemplo: mask_paciente_nome."),
     {"condition_pattern": "\\boc_mask_\\w+", "flags": "IGNORECASE"},
     True, 112),
    ("masking_tag_correspondence", "masking_check", "Mascaramento", "aviso",
     None,
     "Tag de mascaramento sem função correspondente.",
     "Verifique se a função de mascaramento correspondente está definida.",
     {"check_correspondence": True},
     True, 113),
]

assert len(RULES_SEED) == 25, f"Esperado 25 regras, encontrado {len(RULES_SEED)}"
print(f"Regras a inserir: {len(RULES_SEED)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.1 - Executa os 25 INSERTs
# MAGIC
# MAGIC Itera a lista `RULES_SEED` e roda um `INSERT INTO` por regra.
# MAGIC `params` vai serializado como JSON; `created_at` e `updated_at` ficam com `current_timestamp()`.

# COMMAND ----------

for r in RULES_SEED:
    spark.sql(
        f"""
        INSERT INTO {FQN} (
            rule_id, rule_type, category, severity, message_ok, message_fail,
            details_fail, params, enabled, priority, created_at, updated_at
        ) VALUES (
            :rule_id, :rule_type, :category, :severity, :message_ok, :message_fail,
            :details_fail, :params, :enabled, :priority, current_timestamp(), current_timestamp()
        )
        """,
        args={
            "rule_id":      r[0],
            "rule_type":    r[1],
            "category":     r[2],
            "severity":     r[3],
            "message_ok":   r[4],
            "message_fail": r[5],
            "details_fail": r[6],
            "params":       json.dumps(r[7], ensure_ascii=False),
            "enabled":      r[8],
            "priority":     r[9],
        },
    )

print(f"{len(RULES_SEED)} regras inseridas em {FQN}.")

display(spark.sql(f"""
    SELECT category, count(*) AS qtd, sum(CASE WHEN enabled THEN 1 ELSE 0 END) AS habilitadas
    FROM {FQN}
    GROUP BY category
    ORDER BY min(priority)
"""))

display(spark.sql(f"SELECT rule_id, rule_type, category, severity, enabled, priority FROM {FQN} ORDER BY priority"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Estrutura do código fonte
# MAGIC
# MAGIC ```
# MAGIC app/
# MAGIC ├── main.py                          ← FastAPI: rotas HTTP + servir UI
# MAGIC ├── db_client.py                     ← CRUD da tabela via Statement Execution API
# MAGIC ├── llm_assistant.py                 ← Geração de regras via Foundation Model API
# MAGIC ├── static/
# MAGIC │   └── index.html                   ← UI single-page (upload + listar regras + form)
# MAGIC ├── parser/
# MAGIC │   └── notebook_parser.py           ← Parser de .py (Databricks export) e .ipynb
# MAGIC └── validators/
# MAGIC     ├── engine.py                    ← Orquestrador: dinâmico → fallback estático
# MAGIC     ├── rule_loader.py               ← Cache TTL (5 min) das regras do Delta
# MAGIC     ├── dynamic_handlers.py          ← Roda regras vindas da tabela
# MAGIC     ├── extractors.py                ← Extração de tabelas/views/colunas/tags do código
# MAGIC     ├── models.py                    ← ValidationResult, ValidationReport, Severity
# MAGIC     └── (header.py, location.py, naming.py, descriptions.py,
# MAGIC          required_fields.py, tags.py, masking.py)  ← Validadores estáticos (fallback)
# MAGIC app.yaml                              ← Config do Databricks App: comando + env vars
# MAGIC requirements.txt                      ← fastapi, uvicorn, databricks-sdk, requests
# MAGIC ```
# MAGIC
# MAGIC ### 6.1 - O que cada arquivo faz
# MAGIC
# MAGIC | Arquivo | Responsabilidade |
# MAGIC |---------|------------------|
# MAGIC | **`app.yaml`** | Define como o Databricks App inicia: `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Declara `SQL_WAREHOUSE_HTTP_PATH` e `RULES_TABLE` como env vars. |
# MAGIC | **`app/main.py`** | Endpoints FastAPI: `/` (UI), `/api/validate` (upload notebook), `/api/rules` (CRUD), `/api/generate-rule` (LLM), `/api/health`. Sanitiza output com `html.escape` antes de devolver. |
# MAGIC | **`app/db_client.py`** | Acessa a tabela Delta via `WorkspaceClient().statement_execution.execute_statement(...)`. **Não usa f-string em valores** - usa `StatementParameterListItem` para evitar SQL injection. Polling de até 30s por execução. |
# MAGIC | **`app/llm_assistant.py`** | Chama `POST /serving-endpoints/{endpoint}/invocations` com prompt detalhado. Valida que o `rule_type` retornado está em `VALID_RULE_TYPES` antes de devolver - **defesa contra prompt injection**. |
# MAGIC | **`app/parser/notebook_parser.py`** | Parser puro (sem `eval`/`exec`). Para `.py`, usa `# COMMAND ----------` como separador de células e `# MAGIC %sql/%md` para detectar linguagem. Para `.ipynb`, usa `json.loads`. Limite de 5 MB. |
# MAGIC | **`app/validators/engine.py`** | Tenta `get_rules()`. Se vier `None` (ex: warehouse off), cai para `_STATIC_VALIDATORS` para garantir que o app sempre devolve algo. |
# MAGIC | **`app/validators/rule_loader.py`** | Cache em memória (`_cache = {"rules": ..., "ts": ...}`) com TTL de 5 min. `invalidate_cache()` é chamado depois de cada `INSERT/UPDATE/DELETE` em `main.py`. |
# MAGIC | **`app/validators/dynamic_handlers.py`** | Despachante por `rule_type`. Compila regex com whitelist de flags (`IGNORECASE`, `MULTILINE`, `DOTALL` apenas) - bloqueia regex perigosos. |
# MAGIC | **`app/validators/extractors.py`** | Funções puras de regex que extraem tabelas, views, colunas, tags e funções de masking do código. Reutilizadas pelos handlers dinâmicos e validadores estáticos. |
# MAGIC | **`app/validators/models.py`** | `Severity` (`erro`/`aviso`/`ok`), `ValidationResult`, `ValidationReport.to_dict()` para serialização JSON. |
# MAGIC | **`app/static/index.html`** | UI única (sem build). Faz `fetch` nos endpoints `/api/*`. |

# COMMAND ----------

# MAGIC %md
# MAGIC ### 6.2 - Componentes principais (onde está o quê)
# MAGIC
# MAGIC #### Onde a tabela de regras é definida
# MAGIC
# MAGIC - **Nome configurável**: variável de ambiente `RULES_TABLE` em `app.yaml`
# MAGIC   - Default: `cosin_aws_serverless_catalog.pr_review.tb_validacao_regras`
# MAGIC - **Resolução em código**: `app/db_client.py` → função `_get_rules_table()` (linha ~28)
# MAGIC   - Aplica regex `^\w+\.\w+\.\w+$` antes de usar - **defesa contra SQL injection no nome da tabela**
# MAGIC - **Warehouse usado nas queries**: variável `SQL_WAREHOUSE_HTTP_PATH` em `app.yaml`
# MAGIC   - O ID é extraído de `_get_warehouse_id()` em `db_client.py`
# MAGIC
# MAGIC Para apontar para outra tabela, **edite `app.yaml` e redeploy** - não é preciso mudar código.
# MAGIC
# MAGIC #### Onde o LLM é definido
# MAGIC
# MAGIC - **Endpoint**: constante `_MODEL_ENDPOINT` em `app/llm_assistant.py` linha 17
# MAGIC   - Valor: `"databricks-claude-sonnet-4-6"`
# MAGIC - **Como é chamado**: `requests.post()` direto contra `{host}/serving-endpoints/{endpoint}/invocations` (linha ~167)
# MAGIC - **Auth**: `WorkspaceClient().config.authenticate()` - usa o Service Principal do app automaticamente
# MAGIC - **System prompt**: `_SYSTEM_PROMPT` em `app/llm_assistant.py` linha 53
# MAGIC   - Documenta os 13 `rule_type`s e dá exemplos de input → output
# MAGIC - **Validação de saída** (linha ~196): se `rule_type` retornado pelo LLM não estiver em `VALID_RULE_TYPES`, retorna `None`. **Nunca confiar cegamente no output do LLM**.
# MAGIC
# MAGIC Para trocar de modelo (ex: Opus, Llama), basta mudar `_MODEL_ENDPOINT` e garantir `CAN QUERY` no novo endpoint para o SP do app.
# MAGIC
# MAGIC #### Outros pontos importantes
# MAGIC
# MAGIC - **Cache TTL** (`app/validators/rule_loader.py` linha 11): `_TTL = 300` segundos. Mudanças em regras só refletem após 5 min, **a menos que** se chame `POST /api/reload-rules` ou se a mutação venha pelo próprio app (que já invalida).
# MAGIC - **Fallback estático** (`app/validators/engine.py`): se a tabela estiver inacessível, o app não quebra - usa os validadores hardcoded em `validators/*.py`.
# MAGIC - **Limite de upload**: `MAX_FILE_SIZE = 5 MB` em `app/parser/notebook_parser.py`.
# MAGIC - **Sanitização**: `_sanitize_dict` em `main.py` aplica `html.escape` em todo output JSON - evita XSS no front.

# COMMAND ----------

# MAGIC %md
# MAGIC ### 6.3 - Catálogo de `rule_type` e seus `params`
# MAGIC
# MAGIC Extraído de `app/llm_assistant.py`. Use como referência ao popular a tabela manualmente.
# MAGIC
# MAGIC | `rule_type` | Quando usar | Estrutura de `params` (JSON) |
# MAGIC |-------------|-------------|--------------------------------|
# MAGIC | `regex_must_exist` | Padrão **deve** aparecer no código | `{"pattern": "...", "flags": "IGNORECASE", "search_scope": "full_code"}` |
# MAGIC | `regex_must_not_exist` | Padrão **não pode** aparecer | mesmo formato acima |
# MAGIC | `conditional_warning` | Se aparecer, emite aviso | `{"condition_pattern": "...", "flags": "IGNORECASE"}` |
# MAGIC | `conditional_compound` | AND de várias condições | `{"conditions": [{"pattern": "...", "flags": "..."}], "operator": "AND"}` |
# MAGIC | `notebook_name_pattern` | Se gatilho aparecer, nome do arquivo precisa de prefixo | `{"condition_pattern": "...", "name_prefix": "nb_...", "flags": "..."}` |
# MAGIC | `table_prefix_check` | Tabelas em schema X precisam de prefixo Y | `{"catalog_pattern": "...", "schema_prefix_map": {"schema": ["pref_"]}}` |
# MAGIC | `view_prefix_check` | Views precisam de prefixo | `{"required_prefix": "vie_"}` |
# MAGIC | `field_prefix_check` | Campos precisam de prefixos válidos | `{"valid_prefixes": ["ano_", "cod_"], "skip_if_only_catalog": "..."}` |
# MAGIC | `required_column_check` | Tabela tipo X precisa de colunas Y | `{"table_pattern": "...", "required_columns": [...], "flags": "..."}` |
# MAGIC | `comment_format_check` | Formato de COMMENTs SQL | `{"require_uppercase_start": true, "require_period_end": true}` |
# MAGIC | `tag_value_check` | Valores específicos para tags | `{"expected_table_values": {...}, "na_masking_value": "...", "field_tag_pattern": "..."}` |
# MAGIC | `tag_uppercase_check` | Tags e valores em UPPERCASE | `{}` |
# MAGIC | `masking_check` | Funções `oc_mask_*` válidas | `{"function_pattern": "...", "min_parts": 2, "default_schema": "..."}` |
# MAGIC
# MAGIC > **Flags permitidas em regex** (whitelist em `dynamic_handlers.py`): `IGNORECASE`, `MULTILINE`, `DOTALL`. Outras são silenciosamente ignoradas.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Próximos passos - deploy do app
# MAGIC
# MAGIC 1. **Criar o app** (uma vez):
# MAGIC    ```bash
# MAGIC    databricks apps create validador-prs \
# MAGIC      --description "Validador Automático de PRs para Notebooks Databricks" \
# MAGIC      -p <seu-profile>
# MAGIC    ```
# MAGIC
# MAGIC 2. **Subir o código** (do diretório do projeto local):
# MAGIC    ```bash
# MAGIC    databricks sync . /Workspace/Users/<seu-email>/apps/validador-prs \
# MAGIC      --exclude ".DS_Store" --exclude "__pycache__" --exclude ".venv" \
# MAGIC      --exclude "notebooks_teste" --full -p <seu-profile>
# MAGIC    ```
# MAGIC
# MAGIC 3. **Editar `app.yaml`** com o seu warehouse e tabela:
# MAGIC    ```yaml
# MAGIC    env:
# MAGIC      - name: SQL_WAREHOUSE_HTTP_PATH
# MAGIC        value: "/sql/1.0/warehouses/<warehouse-id>"
# MAGIC      - name: RULES_TABLE
# MAGIC        value: "<catalog>.<schema>.<tabela>"
# MAGIC    ```
# MAGIC
# MAGIC 4. **Conceder permissões ao Service Principal do app** (em SQL):
# MAGIC    ```sql
# MAGIC    GRANT USE CATALOG ON CATALOG <catalog> TO `<sp-client-id>`;
# MAGIC    GRANT USE SCHEMA ON SCHEMA <catalog>.<schema> TO `<sp-client-id>`;
# MAGIC    GRANT SELECT, MODIFY ON TABLE <catalog>.<schema>.<tabela> TO `<sp-client-id>`;
# MAGIC    ```
# MAGIC    O `sp-client-id` está em `databricks apps get validador-prs` no campo `service_principal_client_id`.
# MAGIC
# MAGIC 5. **Deploy**:
# MAGIC    ```bash
# MAGIC    databricks apps deploy validador-prs \
# MAGIC      --source-code-path /Workspace/Users/<seu-email>/apps/validador-prs \
# MAGIC      -p <seu-profile>
# MAGIC    ```
# MAGIC
# MAGIC 6. **Verificar**: abra a URL retornada por `databricks apps get validador-prs`. Logs em `<url>/logz`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Validação rápida pós-instalação
# MAGIC
# MAGIC Smoke test: confirma que a tabela existe, está populada e que o app consegue lê-la depois do deploy.

# COMMAND ----------

count = spark.sql(f"SELECT count(*) AS total, sum(CASE WHEN enabled THEN 1 ELSE 0 END) AS habilitadas FROM {FQN}").collect()[0]
print(f"Tabela {FQN}")
print(f"  Total de regras:        {count['total']}")
print(f"  Regras habilitadas:     {count['habilitadas']}")
print()
print("Próximo passo: chame GET <url-do-app>/api/health - deve retornar:")
print('  {"status":"ok","rules_source":"dynamic","rules_count": ' + str(count['habilitadas']) + '}')
