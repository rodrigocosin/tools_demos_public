# Databricks notebook source
# MAGIC %md
# MAGIC # 🏥 Exames Clínicos — Análise com IA
# MAGIC ## Arquitetura da Solução & Guia de Arquivos
# MAGIC ---
# MAGIC > **Workspace:** fevm-cosin-aws-serverless
# MAGIC > **App:** https://exames-clinicos-7474659847183384.aws.databricksapps.com
# MAGIC > **Catalog:** `cosin_aws_serverless_catalog.exames_clinicos`
# MAGIC > **Dashboard AI/BI:** `01f118f425471937b8e9d41ccce94d47`

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Visão Geral da Arquitetura
# MAGIC
# MAGIC ```
# MAGIC ┌──────────────────────────────────────────────────────────────────────────────────┐
# MAGIC │                              DATABRICKS APP                                      │
# MAGIC │                                                                                  │
# MAGIC │  ┌──────────────────────────┐          ┌───────────────────────────────────────┐ │
# MAGIC │  │    FRONTEND (React)      │          │          BACKEND (FastAPI)            │ │
# MAGIC │  │                          │  HTTP    │                                       │ │
# MAGIC │  │  • Upload Page           │◄────────►│  /api/upload          → upload.py     │ │
# MAGIC │  │  • Exames Page           │          │  /api/exames          → exames.py     │ │
# MAGIC │  │  • Pacientes Page        │          │  /api/pacientes       → pacientes.py  │ │
# MAGIC │  │  • Dashboard             │          │  /api/stats           → exames.py     │ │
# MAGIC │  │    ├─ Aba Resumo         │          │  /api/reset           → reset.py      │ │
# MAGIC │  │    └─ Aba Analytics      │          │  /api/dashboard-token → app.py        │ │
# MAGIC │  │       (AI/BI embed)      │          │                                       │ │
# MAGIC │  └──────────────────────────┘          └───────────────────────────────────────┘ │
# MAGIC │            │                                           │                         │
# MAGIC └────────────┼───────────────────────────────────────────┼─────────────────────────┘
# MAGIC              │                                           │
# MAGIC              │                              ┌────────────▼──────────────┐
# MAGIC              │                              │   UNITY CATALOG VOLUME    │
# MAGIC              │                              │  uploads_volume/          │
# MAGIC              │                              │  └── 20260305_abc.pdf     │
# MAGIC              │                              └────────────┬──────────────┘
# MAGIC              │                                           │
# MAGIC              │                              ┌────────────▼──────────────┐
# MAGIC              │                              │   PROCESSAMENTO LLM       │
# MAGIC              │                              │                           │
# MAGIC              │                              │  1. PyPDF2 → texto        │
# MAGIC              │                              │  2. LLaMA 3.3 70B         │
# MAGIC              │                              │     ├─ Cabeçalho (1 call) │
# MAGIC              │                              │     └─ Exames (por chunk) │
# MAGIC              │                              └────────────┬──────────────┘
# MAGIC              │                                           │
# MAGIC              │                              ┌────────────▼──────────────┐
# MAGIC              │                              │   DELTA TABLES            │
# MAGIC              │                              │  📋 pacientes (CPF PK)    │
# MAGIC              │                              │  📁 uploads               │
# MAGIC              │                              │  🧪 exames                │
# MAGIC              │                              └────────────┬──────────────┘
# MAGIC              │                                           │
# MAGIC              └───────────────────────────────────────────┘
# MAGIC                       (queries via SQL Statement API)
# MAGIC   ┌──────────────────────────────────────────────────────┐
# MAGIC   │  AI/BI DASHBOARD (Lakeview) — embed via iframe       │
# MAGIC   │  Autenticação: cookie de sessão do Databricks App    │
# MAGIC   │  SDK: @databricks/aibi-client                        │
# MAGIC   └──────────────────────────────────────────────────────┘
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Configuração — Catálogo, Schema e Warehouse
# MAGIC
# MAGIC Há **dois lugares** onde o catálogo/schema são configurados. Ambos precisam estar alinhados:
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 📄 `app.yaml` — variáveis de ambiente do Databricks App
# MAGIC
# MAGIC Este arquivo fica na raiz do projeto e define as env vars injetadas no runtime da app.
# MAGIC Edite aqui para apontar para um catálogo/schema diferente:
# MAGIC
# MAGIC ```yaml
# MAGIC env:
# MAGIC   - name: CATALOG
# MAGIC     value: cosin_aws_serverless_catalog   # ← mude aqui
# MAGIC   - name: SCHEMA
# MAGIC     value: exames_clinicos                 # ← mude aqui
# MAGIC   - name: SERVING_ENDPOINT
# MAGIC     value: databricks-meta-llama-3-3-70b-instruct
# MAGIC ```
# MAGIC
# MAGIC Após editar o `app.yaml`, execute `./deploy.sh` para redeployar.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 📄 `server/config.py` — leitura das env vars (com fallback local)
# MAGIC
# MAGIC ```python
# MAGIC CATALOG  = os.environ.get("CATALOG",  "cosin_aws_serverless_catalog")
# MAGIC SCHEMA   = os.environ.get("SCHEMA",   "exames_clinicos")
# MAGIC
# MAGIC def get_warehouse_id() -> str:
# MAGIC     return os.environ.get("DATABRICKS_WAREHOUSE_ID", "0c2def7684630e5e")
# MAGIC ```
# MAGIC
# MAGIC O fallback (segundo argumento do `get`) é usado em desenvolvimento local.
# MAGIC Em produção (Databricks App), o valor vem das env vars do `app.yaml`.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 📄 `app.py` — Dashboard ID embeddado
# MAGIC
# MAGIC O ID do dashboard AI/BI está hardcoded no endpoint `/api/dashboard-token`:
# MAGIC
# MAGIC ```python
# MAGIC DASHBOARD_ID = "01f118f425471937b8e9d41ccce94d47"   # ← mude aqui para trocar o dashboard
# MAGIC WORKSPACE_ID = "7474659847183384"
# MAGIC ```
# MAGIC
# MAGIC O dashboard precisa estar **publicado** (`Publish` no menu do AI/BI) com `embed_credentials: true`.
# MAGIC Verifique com:
# MAGIC ```bash
# MAGIC curl -s "https://SEU_WORKSPACE/api/2.0/lakeview/dashboards/SEU_DASHBOARD_ID/published" \
# MAGIC   -H "Authorization: Bearer SEU_TOKEN"
# MAGIC # deve retornar: {"embed_credentials": true, ...}
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Setup — Criar Catálogo, Schema, Volume e Tabelas
# MAGIC
# MAGIC Execute a célula abaixo para criar toda a infraestrutura necessária do zero.
# MAGIC **Ajuste as variáveis no topo antes de rodar.**

# COMMAND ----------

# DBTITLE 1,⚙️ Configuração — edite aqui antes de rodar
CATALOG       = "cosin_aws_serverless_catalog"   # ← seu catalog
SCHEMA        = "exames_clinicos"                 # ← seu schema
VOLUME        = "uploads_volume"                  # ← nome do volume para PDFs
WAREHOUSE_ID  = "0c2def7684630e5e"               # ← SQL warehouse ID

print(f"Configuração:")
print(f"  Catalog  : {CATALOG}")
print(f"  Schema   : {SCHEMA}")
print(f"  Volume   : {VOLUME}")
print(f"  Warehouse: {WAREHOUSE_ID}")
print(f"\nTabelas completas:")
print(f"  {CATALOG}.{SCHEMA}.pacientes")
print(f"  {CATALOG}.{SCHEMA}.uploads")
print(f"  {CATALOG}.{SCHEMA}.exames")
print(f"  /Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/")

# COMMAND ----------

# DBTITLE 1,🏗️ Criar infraestrutura (catalog, schema, volume, tabelas)
# Execute esta célula para criar tudo do zero.
# IF NOT EXISTS garante idempotência — seguro rodar mais de uma vez.

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.pacientes (
    cpf                STRING   NOT NULL,
    nome               STRING,
    data_nascimento    DATE,
    idade              INT,
    sexo               STRING,
    medico_solicitante STRING,
    criado_em          TIMESTAMP
)
USING DELTA
""")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.uploads (
    upload_id      STRING NOT NULL,
    cpf            STRING,
    nome_arquivo   STRING,
    caminho_volume STRING,
    data_upload    TIMESTAMP,
    status         STRING,
    total_exames   INT
)
USING DELTA
""")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.exames (
    exame_id         STRING NOT NULL,
    upload_id        STRING,
    cpf              STRING,
    tipo_exame       STRING,
    categoria        STRING,
    nome_exame       STRING,
    valor_resultado  STRING,
    unidade          STRING,
    valor_referencia STRING,
    status_resultado STRING,
    parecer_llm      STRING,
    data_exame       DATE,
    processado_em    TIMESTAMP
)
USING DELTA
""")

print("✅ Infraestrutura criada com sucesso!")
print(f"\nVolume path: /Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Token do Dashboard Embeddado — Como Configurar
# MAGIC
# MAGIC O AI/BI dashboard é embeddado via iframe no frontend usando o SDK `@databricks/aibi-client`.
# MAGIC A autenticação funciona de **duas formas**, dependendo do contexto:
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### ✅ Modo atual: Cookie de sessão (Databricks Apps)
# MAGIC
# MAGIC Quando a app roda dentro do Databricks Apps, o usuário já está autenticado.
# MAGIC O iframe usa o cookie de sessão automaticamente — **sem precisar de token**.
# MAGIC
# MAGIC ```python
# MAGIC # app.py — endpoint atual
# MAGIC @app.get("/api/dashboard-token")
# MAGIC async def dashboard_token():
# MAGIC     return {
# MAGIC         "instanceUrl": get_workspace_host(),
# MAGIC         "workspaceId": "7474659847183384",
# MAGIC         "dashboardId": "01f118f425471937b8e9d41ccce94d47",
# MAGIC         # token NÃO é retornado → iframe usa cookie de sessão
# MAGIC     }
# MAGIC ```
# MAGIC
# MAGIC ```tsx
# MAGIC // DatabricksDashboardEmbed.tsx — frontend atual
# MAGIC dashboard = new DatabricksDashboard({
# MAGIC   instanceUrl, workspaceId, dashboardId,
# MAGIC   token: undefined,   // ← sem token = usa cookie
# MAGIC   colorScheme: 'light',
# MAGIC   config: { version: 1 },
# MAGIC })
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 🔑 Modo externo: Token PAT + OAuth (fora do Databricks Apps)
# MAGIC
# MAGIC Se quiser embeddar o dashboard em um site externo (fora do Databricks Apps),
# MAGIC o SDK precisa de um **token OAuth com escopo específico para o dashboard** — um PAT simples **não funciona**
# MAGIC (erro: *"Dashboard ID is missing in token claim"*).
# MAGIC
# MAGIC **Opção A — Token OAuth via M2M (machine-to-machine):**
# MAGIC Use o Databricks SDK para gerar um token OAuth com o escopo correto:
# MAGIC ```python
# MAGIC from databricks.sdk import WorkspaceClient
# MAGIC from databricks.sdk.service.oauth2 import CreateCustomAppIntegration
# MAGIC
# MAGIC w = WorkspaceClient()
# MAGIC # Obtenha o token OAuth via w.config.authenticate() dentro do app
# MAGIC token = w.config.authenticate().get("Authorization", "").replace("Bearer ", "")
# MAGIC ```
# MAGIC
# MAGIC **Opção B — Personal Access Token do usuário:**
# MAGIC Peça ao usuário que gere um PAT com permissão de leitura no dashboard
# MAGIC e passe como parâmetro. Cuidado: o PAT ficará exposto no browser.
# MAGIC
# MAGIC **Opção C — Databricks Apps (recomendado):**
# MAGIC Mantenha a app dentro do Databricks Apps — o cookie de sessão cuida de tudo,
# MAGIC sem exposição de token e com controle de acesso nativo.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Fluxo de Processamento de um PDF
# MAGIC
# MAGIC ```
# MAGIC  Usuário faz upload do PDF
# MAGIC          │
# MAGIC          ▼
# MAGIC  ┌─────────────────┐
# MAGIC  │  FastAPI recebe │  POST /api/upload   (upload.py)
# MAGIC  └────────┬────────┘
# MAGIC           │
# MAGIC           ▼
# MAGIC  ┌─────────────────┐
# MAGIC  │ Salva no Volume │  volume.py → PUT /api/2.0/fs/files/Volumes/...
# MAGIC  └────────┬────────┘
# MAGIC           │
# MAGIC           ▼
# MAGIC  ┌─────────────────┐
# MAGIC  │ INSERT uploads  │  status = 'pendente' — resposta imediata ao usuário
# MAGIC  │ (background)    │
# MAGIC  └────────┬────────┘
# MAGIC           │
# MAGIC           ▼
# MAGIC  ┌─────────────────┐
# MAGIC  │ PyPDF2 extrai   │  _extract_pdf_text() — todas as páginas concatenadas
# MAGIC  │ texto do PDF    │
# MAGIC  └────────┬────────┘
# MAGIC           │
# MAGIC           ▼
# MAGIC  ┌─────────────────────────────────────────────────────────┐
# MAGIC  │  STEP 1 — LLM: cabeçalho (paciente/médico/datas)       │
# MAGIC  │  Entrada: primeiros 6.000 chars                         │
# MAGIC  │  temperature=0.0 — máxima consistência                  │
# MAGIC  │  Retorna: { nome, medico_solicitante,                   │
# MAGIC  │             data_nascimento, data_exame, cpf }           │
# MAGIC  └────────────────────────────┬────────────────────────────┘
# MAGIC                               │
# MAGIC                               ▼
# MAGIC  ┌─────────────────────────────────────────────────────────┐
# MAGIC  │  STEP 2 — LLM: exames em chunks                        │
# MAGIC  │  ≤ 20.000 chars → 1 chunk                               │
# MAGIC  │  > 20.000 chars → chunks de 20k com overlap de 1.5k    │
# MAGIC  │  Por chunk → array JSON de exames                       │
# MAGIC  │  Deduplicação por nome_exame entre chunks               │
# MAGIC  └────────────────────────────┬────────────────────────────┘
# MAGIC                               │
# MAGIC                               ▼
# MAGIC  ┌─────────────────┐
# MAGIC  │ MERGE pacientes │  upsert por CPF
# MAGIC  └────────┬────────┘
# MAGIC           │
# MAGIC           ▼
# MAGIC  ┌─────────────────────────────────────────────────────────┐
# MAGIC  │  STEP 3 — LLM: parecer clínico (generate_parecer)      │
# MAGIC  │  temperature=0.3 — max 3 parágrafos em português        │
# MAGIC  └────────────────────────────┬────────────────────────────┘
# MAGIC                               │
# MAGIC                               ▼
# MAGIC  ┌─────────────────┐
# MAGIC  │ INSERT exames   │  um registro por exame (com parecer)
# MAGIC  └────────┬────────┘
# MAGIC           │
# MAGIC           ▼
# MAGIC  ┌─────────────────┐
# MAGIC  │ UPDATE uploads  │  status = 'concluido', total_exames = N
# MAGIC  └─────────────────┘
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Estratégia LLM de Extração do Cabeçalho
# MAGIC
# MAGIC O PDF do laboratório Fleury (e similares) é lido pelo PyPDF2 com as colunas **fora de ordem**:
# MAGIC
# MAGIC ```
# MAGIC DR. ANDRE JAIME CRM 87719SP     ← médico aparece ANTES dos labels
# MAGIC Cliente:                         ← label SEM valor na mesma linha
# MAGIC Data de Nascimento:              ← label SEM valor na mesma linha
# MAGIC Médico:                          ← label SEM valor na mesma linha
# MAGIC RODRIGO QUINELATO COSIN          ← paciente aparece APÓS o label "Médico:"!
# MAGIC 16/05/1983 Ficha:                ← data de nascimento + outro label
# MAGIC Data da Ficha:
# MAGIC 04/09/2025
# MAGIC ```
# MAGIC
# MAGIC **Solução:** o prompt `_PATIENT_SYSTEM` em `server/llm.py` explica explicitamente esse formato ao LLM:
# MAGIC - `nome` = paciente (nunca o médico, nunca um label, nunca uma data)
# MAGIC - `medico_solicitante` = identificado por Dr./Dra., CRM ou label "Médico Solicitante" — título e CRM removidos
# MAGIC - `data_nascimento` = geralmente a mais antiga
# MAGIC - `data_exame` = procurar labels "Data da Ficha", "Data do Exame", "Data de Coleta"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Componentes Utilizados por Etapa
# MAGIC
# MAGIC | Etapa | Componente | Detalhes |
# MAGIC |-------|-----------|----------|
# MAGIC | **Hospedagem** | Databricks Apps | Runtime Python + FastAPI + React estático |
# MAGIC | **Armazenamento de PDFs** | Unity Catalog Volume | `/Volumes/{CATALOG}/{SCHEMA}/uploads_volume/` |
# MAGIC | **Banco de dados** | Delta Tables | `pacientes`, `uploads`, `exames` |
# MAGIC | **Acesso ao banco** | SQL Statement Execution API | `/api/2.0/sql/statements` |
# MAGIC | **Extração de texto** | PyPDF2 | Leitura em memória (BytesIO), sem disco |
# MAGIC | **IA — Cabeçalho** | `databricks-meta-llama-3-3-70b-instruct` | 1 call, temp=0.0 |
# MAGIC | **IA — Exames** | `databricks-meta-llama-3-3-70b-instruct` | N calls (1 por chunk), temp=0.05 |
# MAGIC | **IA — Parecer** | `databricks-meta-llama-3-3-70b-instruct` | 1 call, temp=0.3 |
# MAGIC | **Dashboard embed** | `@databricks/aibi-client` v1.0.1-alpha | SDK npm, iframe via cookie de sessão |
# MAGIC | **Frontend** | React 19 + Vite + TailwindCSS v4 | Build estático servido pelo FastAPI |
# MAGIC | **Roteamento** | React Router v7 | SPA: `/`, `/upload`, `/exames`, `/pacientes` |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Principais Arquivos — Guia de Edição
# MAGIC
# MAGIC ### 📁 Backend (`/server/`)
# MAGIC
# MAGIC | Arquivo | O que faz | Quando editar |
# MAGIC |---------|-----------|---------------|
# MAGIC | `server/llm.py` | `_PATIENT_SYSTEM` (prompt cabeçalho), chunked exam extraction, `generate_parecer()` | Ajustar prompt, melhorar parecer, mudar modelo |
# MAGIC | `server/routes/upload.py` | Recebe PDF, extrai texto, chama LLM, salva volume e tabelas | Adicionar campos, mudar deduplicação |
# MAGIC | `server/routes/exames.py` | API de listagem, filtros e stats | Adicionar filtros, novos endpoints |
# MAGIC | `server/routes/pacientes.py` | API de pacientes e detalhe por CPF | Adicionar campos |
# MAGIC | `server/routes/reset.py` | Apaga todos os dados (demo) | Ajustar o que é apagado |
# MAGIC | `server/db.py` | SQL via Statement Execution API | Raramente — só se mudar warehouse |
# MAGIC | `server/config.py` | Lê env vars: CATALOG, SCHEMA, WAREHOUSE_ID | Mudar valores de fallback local |
# MAGIC | `server/volume.py` | Upload/download de arquivos no Volume | Mudar caminho do volume |
# MAGIC
# MAGIC ### 📁 Frontend (`/frontend/src/`)
# MAGIC
# MAGIC | Arquivo | O que faz | Quando editar |
# MAGIC |---------|-----------|---------------|
# MAGIC | `pages/Dashboard.tsx` | 2 abas: Resumo (KPIs) e Analytics (AI/BI embed) | Adicionar métricas, trocar dashboard |
# MAGIC | `components/DatabricksDashboardEmbed.tsx` | Inicializa iframe do AI/BI via SDK | Mudar token, colorScheme, dashboard ID |
# MAGIC | `pages/UploadPage.tsx` | Drag-and-drop de PDFs | Mudar UI de upload |
# MAGIC | `pages/ExamesPage.tsx` | Tabela com filtros | Adicionar colunas, filtros |
# MAGIC | `pages/PacientesPage.tsx` | Lista de pacientes | Adicionar campos |
# MAGIC | `pages/UploadDetailPage.tsx` | Detalhe do upload + exames + parecer | Mostrar mais detalhes |
# MAGIC | `pages/PacienteDetailPage.tsx` | Histórico de exames por paciente | Adicionar gráficos |
# MAGIC | `App.tsx` | Sidebar, navegação, modal de reset | Adicionar páginas |
# MAGIC
# MAGIC ### 📁 Raiz do projeto
# MAGIC
# MAGIC | Arquivo | O que faz | Quando editar |
# MAGIC |---------|-----------|---------------|
# MAGIC | `app.py` | Entry point FastAPI + endpoint `/api/dashboard-token` | Adicionar routers, trocar dashboard ID |
# MAGIC | `app.yaml` | **Env vars do Databricks App: CATALOG, SCHEMA, SERVING_ENDPOINT** | ← **Aqui para trocar catálogo/schema** |
# MAGIC | `deploy.sh` | Build + sync + deploy em um comando | Ajustar perfil CLI |
# MAGIC | `setup_tables.py` | Cria tabelas Delta e volume (CLI Python) | Recriar tabelas, mudar schema |
# MAGIC | `requirements.txt` | Dependências Python | Adicionar pacotes |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Como Fazer Alterações Comuns
# MAGIC
# MAGIC ### Mudar para outro catálogo/schema
# MAGIC ```
# MAGIC 1. app.yaml → altere CATALOG e SCHEMA nas env vars
# MAGIC 2. Execute as células de setup deste notebook (Seção 3) no novo catalog/schema
# MAGIC 3. ./deploy.sh
# MAGIC ```
# MAGIC
# MAGIC ### Trocar o dashboard embeddado
# MAGIC ```
# MAGIC 1. Publique o novo dashboard no Databricks AI/BI (botão Publish)
# MAGIC 2. Verifique: GET /api/2.0/lakeview/dashboards/{ID}/published → embed_credentials: true
# MAGIC 3. app.py → mude DASHBOARD_ID em dashboard_token()
# MAGIC 4. ./deploy.sh
# MAGIC ```
# MAGIC
# MAGIC ### Ajustar o prompt de extração do cabeçalho
# MAGIC ```
# MAGIC Edite: server/llm.py
# MAGIC Constante: _PATIENT_SYSTEM  (topo do arquivo)
# MAGIC ```
# MAGIC
# MAGIC ### Melhorar extração de exames
# MAGIC ```
# MAGIC Edite: server/llm.py
# MAGIC Variável: exam_system  (dentro de extract_exam_data)
# MAGIC ```
# MAGIC
# MAGIC ### Adicionar um novo campo de exame
# MAGIC ```
# MAGIC 1. Seção 3 deste notebook → ALTER TABLE exames ADD COLUMN novo_campo STRING
# MAGIC 2. server/llm.py          → adicione no exam_system prompt
# MAGIC 3. server/routes/upload.py → inclua no INSERT INTO exames
# MAGIC 4. frontend/ExamesPage.tsx → adicione a coluna na tabela
# MAGIC 5. ./deploy.sh
# MAGIC ```
# MAGIC
# MAGIC ### Redeployar após qualquer mudança
# MAGIC ```bash
# MAGIC cd ~/exames-clinicos-app
# MAGIC ./deploy.sh
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Consultas Úteis nas Tabelas

# COMMAND ----------

# DBTITLE 1,Resumo Geral
# MAGIC %sql
# MAGIC SELECT
# MAGIC   (SELECT COUNT(*) FROM cosin_aws_serverless_catalog.exames_clinicos.pacientes) AS total_pacientes,
# MAGIC   (SELECT COUNT(*) FROM cosin_aws_serverless_catalog.exames_clinicos.uploads)   AS total_uploads,
# MAGIC   (SELECT COUNT(*) FROM cosin_aws_serverless_catalog.exames_clinicos.exames)    AS total_exames,
# MAGIC   (SELECT COUNT(*) FROM cosin_aws_serverless_catalog.exames_clinicos.exames WHERE status_resultado = 'critico')  AS criticos,
# MAGIC   (SELECT COUNT(*) FROM cosin_aws_serverless_catalog.exames_clinicos.exames WHERE status_resultado = 'alterado') AS alterados

# COMMAND ----------

# DBTITLE 1,Exames por Categoria e Status
# MAGIC %sql
# MAGIC SELECT categoria, status_resultado, COUNT(*) as qtd
# MAGIC FROM cosin_aws_serverless_catalog.exames_clinicos.exames
# MAGIC GROUP BY categoria, status_resultado
# MAGIC ORDER BY categoria, qtd DESC

# COMMAND ----------

# DBTITLE 1,Histórico de Uploads com Status
# MAGIC %sql
# MAGIC SELECT u.nome_arquivo, u.status, u.total_exames, u.data_upload,
# MAGIC        p.nome AS paciente, p.cpf, p.medico_solicitante
# MAGIC FROM cosin_aws_serverless_catalog.exames_clinicos.uploads u
# MAGIC LEFT JOIN cosin_aws_serverless_catalog.exames_clinicos.pacientes p ON u.cpf = p.cpf
# MAGIC ORDER BY u.data_upload DESC

# COMMAND ----------

# DBTITLE 1,Exames Críticos com Parecer
# MAGIC %sql
# MAGIC SELECT p.nome, e.nome_exame, e.valor_resultado, e.unidade,
# MAGIC        e.valor_referencia, e.data_exame, e.parecer_llm
# MAGIC FROM cosin_aws_serverless_catalog.exames_clinicos.exames e
# MAGIC JOIN cosin_aws_serverless_catalog.exames_clinicos.pacientes p ON e.cpf = p.cpf
# MAGIC WHERE e.status_resultado = 'critico'
# MAGIC ORDER BY e.processado_em DESC

# COMMAND ----------

# DBTITLE 1,Uploads com Erro (para debug)
# MAGIC %sql
# MAGIC SELECT upload_id, nome_arquivo, data_upload, status
# MAGIC FROM cosin_aws_serverless_catalog.exames_clinicos.uploads
# MAGIC WHERE status = 'erro'
# MAGIC ORDER BY data_upload DESC
