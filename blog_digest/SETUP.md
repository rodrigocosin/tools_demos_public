# Guia de instalação / replicação — Databricks Blog Digest

Como recriar a solução do zero em **qualquer workspace Databricks**. Três caminhos:
**(A) via notebook `setup_deploy`** (recomendado — roda 100% dentro do Databricks),
**(B) via `deploy.sh`** (CLI local) e **(C) manual** passo a passo (para entender/ajustar).

> Visão geral da arquitetura e tabelas: ver `README.md`.

---

## Pré-requisitos

- Um **SQL Warehouse** (serverless de preferência) **ligado** → anote o `warehouse_id`.
- Permissão de **admin do workspace** (para criar Notification Destination).
- Um endpoint de LLM disponível (ex.: `databricks-claude-opus-4-8`).
- Para os caminhos (B)/(C): Databricks CLI autenticado + `python3` na máquina local.

---

## (A) Replicação via notebook (dentro do Databricks) — recomendado

Não precisa de CLI nem máquina local. Tudo roda no workspace.

1. Coloque a pasta `blog_digest/` no workspace (via Git/Repos ou import), com os notebooks
   `00..03` e o `setup_deploy` **na mesma pasta**.
2. Abra o notebook **`setup_deploy`**, edite o bloco **CONFIG** (catálogo, schema,
   `warehouse_id`, endpoint do LLM, crons, e-mails iniciais) e **execute-o** (Run all).
   Ele cria schema+tabelas, a query e o alert legacy, 1 destino por destinatário, os dois
   jobs e aplica o template. No fim imprime `QUERY_ID`, `ALERT_ID`, `SEND_JOB_ID`.
3. Rode o job `blog_digest_diario` (popular) e depois `blog_send_semanal` (enviar).

> Rode o `setup_deploy` **uma vez por ambiente** (ele cria objetos novos a cada execução).

---

## (B) Replicação via CLI local (`deploy.sh`)

1. Edite o bloco **CONFIG** no topo do `deploy.sh` (profile, catálogo, schema,
   `warehouse_id`, caminho dos notebooks, endpoint do LLM, crons, e-mails iniciais).
2. `databricks auth login --host https://<workspace> --profile <perfil>` e rode `bash deploy.sh`.
3. O script faz tudo (inclui upload dos notebooks) e imprime os IDs.
4. Rode o job `blog_digest_diario` e depois `blog_send_semanal`.

---

## (C) Replicação manual (passo a passo)

Defina as variáveis (ajuste aos seus valores):

```bash
PROFILE=meu-profile
CATALOG=meu_catalogo
SCHEMA=blog_digest
WAREHOUSE_ID=xxxxxxxxxxxx
USER_PATH=/Workspace/Users/voce@empresa.com/blog_digest
```

### 1. Schema + tabelas
```bash
PROFILE=$PROFILE WAREHOUSE_ID=$WAREHOUSE_ID python3 run_sql.py sql/01_setup_schema.sql
```
Tabelas criadas: `blog_posts`, `post_summaries`, `email_recipients` (ver `README.md`).

### 2. Seed da lista de e-mails
```sql
INSERT INTO <CATALOG>.<SCHEMA>.email_recipients (email,name,active,added_at)
VALUES ('voce@empresa.com','Você',true,current_timestamp());
```

### 3. Upload dos notebooks
```bash
databricks workspace mkdirs "$USER_PATH" --profile $PROFILE
for nb in 00_preparar_email 01_ingest_and_summarize 02_sync_recipients 03_weekly_log; do
  databricks workspace import "$USER_PATH/$nb" --file notebooks/$nb.py \
    --language PYTHON --format SOURCE --overwrite --profile $PROFILE
done
```

### 4. Notification Destinations (1 por destinatário = e-mails ocultos)
Para enviar a **clientes externos** e manter os destinatários **ocultos** entre si, usamos
**um destination por pessoa** (cada um com 1 endereço). O alerta é inscrito em todos →
o Databricks dispara **um e-mail individual por destino**. Crie um por destinatário inicial:
```bash
databricks notification-destinations create --profile $PROFILE --json \
  '{"display_name":"Blog Digest :: voce@empresa.com","config":{"email":{"addresses":["voce@empresa.com"]}}}'
```
Anote o(s) `id`(s). **Você não precisa criar todos na mão**: o notebook `02_sync_recipients`
(no job diário) cria/atualiza/remove esses destinos a partir da tabela `email_recipients`.
> E-mail "direto" via `user_name` na subscription só funciona para **usuários do workspace**;
> para endereços **externos** (clientes), o Notification Destination é obrigatório.

### 5. Legacy SQL query (fonte do alerta)
Descubra o `data_source_id` do warehouse:
```bash
databricks api get /api/2.0/preview/sql/data_sources --profile $PROFILE
# pegue o id cujo warehouse_id == $WAREHOUSE_ID  -> DS_ID
```
Crie a query (seleciona só posts **não enviados** e monta as colunas usadas no template):
```bash
databricks queries-legacy create --profile $PROFILE --json '{
  "name": "Blog Digest - query semanal",
  "data_source_id": "<DS_ID>",
  "query": "SELECT row_number() OVER (ORDER BY p.published_date DESC) AS n, s.title_pt AS post, s.resumo_html AS resumo_html, p.url AS link FROM <CATALOG>.<SCHEMA>.post_summaries s JOIN <CATALOG>.<SCHEMA>.blog_posts p ON p.url = s.url WHERE coalesce(s.weekly_sent, false) = false ORDER BY p.published_date DESC"
}'
```
Anote o `id` → **QUERY_ID**.

### 6. Legacy SQL alert (o "enviador")
> **Por que LEGACY?** Os jobs (`sql_task`) só executam alertas do tipo *legacy*; o
> alerta "SQL alert" v2 não é resolvido pela API de jobs. O alerta legacy também é o
> que suporta o **template Mustache** (`{{#QUERY_RESULT_ROWS}}` / `{{{coluna}}}`).

Crie o alerta (mínimo — o **template completo é aplicado pelo notebook 00**):
```bash
databricks alerts-legacy create --profile $PROFILE --json '{
  "name": "Databricks Blog Digest - Semanal",
  "query_id": "<QUERY_ID>",
  "rearm": 1,
  "options": {
    "column": "n", "op": ">", "value": "0",
    "empty_result_state": "ok",
    "custom_subject": "Databricks Blog — Resumo da semana",
    "custom_body": "(definido pelo notebook 00)"
  }
}'
```
Anote o `id` → **ALERT_ID**.

**Detalhes que importam no alerta:**
- `column=n, op=>, value=0` + **sem agregação** → o alerta avalia o *primeiro valor*
  da coluna `n` (row_number). Assim o e-mail mostra **as linhas** (cards), não um agregado.
- `empty_result_state="ok"` → resultado vazio **não** dispara (reforça o gate do job).
- `rearm=1` → o alerta "rearma" e **re-notifica a cada execução** (com `rearm=0` ele
  notificaria só na 1ª transição e ficaria mudo nas semanas seguintes).
- O **template** (assunto com a data do envio + corpo em cards com `<hr>` e disclaimer
  de IA) é (re)aplicado a cada execução pelo notebook **00_preparar_email** — é a
  **fonte da verdade** do visual do e-mail. Para mudar o layout, edite o `body` lá.

### 7. Jobs
Use o `deploy.sh` (seções 7 e 8) como referência, ou crie via UI/CLI.

- **`blog_digest_diario`** (cron diário) — 2 tasks:
  1. `ingest_and_summarize` (notebook 01)
  2. `sync_recipients` (notebook 02, depends 1) — `base_parameters`: `weekly_job_id=<SEND_JOB_ID>`, `enviar_task_key=enviar_digest`.
     Cria/remove 1 destino por destinatário ativo **e** atualiza as `subscriptions` da task
     de envio (pré-staging — precisa rodar **antes** do envio de sexta).
- **`blog_send_semanal`** (cron sexta) — 4 tasks:
  1. `preparar_email` (notebook 00) — `base_parameters`: `alert_id=<ALERT_ID>`, `query_id=<QUERY_ID>`
  2. `tem_conteudo` (condition_task) — `GREATER_THAN`, `left={{tasks.preparar_email.values.pendentes}}`, `right=0`
  3. `enviar_digest` (sql_task → alert, depends `tem_conteudo` outcome **true**) —
     `alert_id=<ALERT_ID>`, `subscriptions=[{destination_id=...}]` (1 por destinatário; **mantidas pelo sync**)
  4. `marcar_enviados` (notebook 03, depends `enviar_digest`)

> **Ordem importa:** o `sync_recipients` roda no job **diário** porque as `subscriptions` do
> `sql_task` precisam estar definidas **antes** do run de envio (editar no meio do run não
> afeta o run atual). Como o diário roda toda manhã, na sexta a lista já está correta.

---

## Operação

- **Gerenciar destinatários:** insira linhas em `email_recipients` ou mude `active`.
  O **job diário** sincroniza os destinos e as subscriptions automaticamente.
- **Forçar reenvio de um post:** `UPDATE post_summaries SET weekly_sent=false WHERE url='...'`.
- **Mudar o texto/visual do e-mail:** edite `body`/`subject` em `notebooks/00_preparar_email.py`
  e rode o notebook (ou o job de envio) para reaplicar.
- **Rodar manualmente:** `databricks jobs run-now <job_id> --profile $PROFILE`.

## Por que cada salvaguarda existe (lições aprendidas)

| Sintoma | Causa | Correção |
|---|---|---|
| E-mail mostrava `count=10` em vez dos posts | condição com **agregação** | usar `column=n` **sem** agregação |
| Não reenviava nas semanas seguintes | `rearm=0` (notifica só 1x) | `rearm=1` |
| Enviou e-mail **vazio** (0 posts) | resultado vazio disparava | `empty_result_state=ok` + **condition_task** (gate) no job |
| Link "sumia" no Gmail | botão com fundo colorido (Gmail remove) | link com **borda** + texto vermelho |
| Destinatários se viam (todos no "Para") | 1 destino com vários e-mails | **1 destino por pessoa** + alerta inscrito em todos |
