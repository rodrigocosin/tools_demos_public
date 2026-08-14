# Databricks Blog Digest

Pipeline que acompanha o blog da Databricks, gera resumos em **português (via LLM)** e
envia um **digest semanal por email** para uma lista de destinatários.

Workspace: `https://fevm-cosin-aws-serverless.cloud.databricks.com`
Catálogo/Schema: `cosin_aws_serverless_catalog.blog_digest`
LLM usado nos resumos: **`databricks-claude-opus-4-8`** (melhor disponível no workspace)

> **Para instalar/replicar em outro ambiente, veja [`SETUP.md`](SETUP.md).** Recomendado:
> rodar o notebook **`setup_deploy`** dentro do Databricks (cria tudo). Alternativas: `deploy.sh`
> (CLI local) ou o passo a passo manual. Inclui a criação do alerta + template.

### Estrutura do projeto
- `notebooks/setup_deploy.py` — **deploy completo rodando dentro do Databricks** (schema, query+alerta, destinos, jobs, template)
- `notebooks/00_preparar_email.py` — define assunto (com a data do envio) e o **template** do e-mail (cards) no alerta
- `notebooks/01_ingest_and_summarize.py` — scrape do blog + carga incremental + resumo PT-BR via LLM
- `notebooks/02_sync_recipients.py` — 1 destino por destinatário (e-mails ocultos) + atualiza subscriptions do envio
- `notebooks/04_enviar_lotes.py` — envia o digest em **lotes** (contorna limite do alerta) e grava `send_log`
- `notebooks/03_weekly_log.py` — marca os posts como enviados (`send_status='sent'`)
- `sql/01_setup_schema.sql` — cria schema + tabelas (usado pelo `deploy.sh`; o `setup_deploy` traz o DDL embutido)
- `jobs/*.json` — definições dos jobs (referência)
- `deploy.sh` · `run_sql.py` — caminho de deploy via **CLI local** (alternativa ao `setup_deploy`)
- `BACKLOG.md` — tarefas futuras (ex.: **seção de "Eventos por vir"** no digest semanal)

## Arquitetura

```
                ┌─────────────────────── JOB DIÁRIO (08:00 BRT) ───────────────────────┐
                │  01_ingest_and_summarize                                              │
  blog.com  ──▶ │   • scrape de www.databricks.com/br/blog (PT)                                 │
                │   • MERGE incremental em blog_posts (dedup por URL)                   │
                │   • resumo PT-BR (ai_query Opus 4.8) → post_summaries                 │
                │  02_sync_recipients                                                   │
                │   • 1 Notification Destination por destinatário ATIVO (cria/remove)   │
                │   • atualiza as subscriptions da task de envio (pré-staging p/ sexta) │
                └───────────────────────────────────────────────────────────────────────┘

                ┌─────── JOB DE ENVIO "blog_send_semanal" (sexta 10:00 BRT) ───────────┐
                │  preparar_email (00) — assunto "Resumo semanal — Blog da Databricks  │
                │     (DD/MM/AAAA)" + template (cards, badge categoria, <hr>, 2 disc.) │
                │  tem_conteudo (gate) — só segue se há posts pendentes (send_status=  │
                │     'pending'); se 0 → EXCLUDED (não envia email vazio)              │
                │  enviar_lotes (04) — dispara o Legacy alert em LOTES (ex.: 10/destino│
                │     por vez, com pausa) → 1 email individual por destino (OCULTOS).  │
                │     Grava cada lote em send_log. (Bulk único de 50+ não entrega!)    │
                │  marcar_enviados (03) — send_status='sent' + weekly_sent_at=agora    │
                └───────────────────────────────────────────────────────────────────────┘
```

## Tabelas (`cosin_aws_serverless_catalog.blog_digest`)

| Tabela | Conteúdo |
|---|---|
| `blog_posts` | Posts ingeridos (fonte da verdade p/ dedup incremental por URL) |
| `post_summaries` | Resumo PT-BR por post: `title_pt`, `resumo` (texto plano ~700 chars), `resumo_html` (bullets p/ email), `bullets_json` (estrutura crua p/ re-derivar sem LLM), `disponibilidade`, `links_importantes`, e o controle de envio `weekly_sent` / `weekly_sent_at` |
| `email_recipients` | **Lista de destinatários** (fonte da verdade): `company`, `email` (PK), `name`, `active`, `added_at`, `sa` (Solutions Architect), `ae` (Account Executive). |
| `send_log` | **Auditoria de envios** — 1 linha por LOTE: `execution_id`, `batch_idx`/`batches_total`, `dest_count`, `emails`, `result_state`, `posts_count`, `post_titles`. |

> `post_summaries.send_status`: **`pending`** (vai no próximo envio), **`skip`** (omitido de propósito), **`sent`** (já enviado). É o que controla o que entra no digest.
> O envio aos clientes é **multi-SA**: o sync e o envio filtram por `sa` (cada SA manda só para seus contatos).

## Destinatários ocultos (1 destino por pessoa)

Para enviar a **clientes externos** (não-usuários do workspace) e manter cada destinatário
**oculto** dos demais, usamos **um Notification Destination por destinatário** (cada um com
um único endereço). O alerta é inscrito em todos → o Databricks dispara **um e-mail
individual por destino**. O `02_sync_recipients` cria/atualiza/remove esses destinos a
partir da tabela e ajusta as subscriptions da task de envio. (E-mail "direto" via `user_name`
só funcionaria para usuários do workspace — não serve para clientes externos.)

## Recursos no workspace

- Notebooks: `/Workspace/Users/rodrigo.cosin@databricks.com/tools_demos_public/blog_digest/{00,01,02,03}_*`
- Job diário: `blog_digest_diario` (id 72615450561326) — ingestão + resumo + sync de destinos/subscriptions
- Job de envio: `blog_send_semanal` (id 696804447163687) — prepara → gate → envia (oculto) → marca
- Legacy SQL alert: `Databricks Blog Digest - Semanal` (id b5a63e41-6b3e-4cd7-aaa9-eb55701d95a5)
- Legacy query: `Blog Digest - query semanal` (id bd628f7a-bfad-4a3c-9ac9-e9e8c2104b25)
- Notification Destinations: um por destinatário, nomeados `Blog Digest :: <email>`

## Como gerenciar a lista de emails

A lista vive na tabela `email_recipients`. Para adicionar/remover, basta inserir linhas ou
mudar o campo `active`. O **job diário** sincroniza tudo: cria/remove o destino de cada pessoa
e atualiza as subscriptions do envio. (Para remover alguém, `active=false` ou apague a linha.)

```sql
-- adicionar
INSERT INTO cosin_aws_serverless_catalog.blog_digest.email_recipients
  (email, name, company, active, added_at)
VALUES ('novo@cliente.com', 'Nome', 'Empresa', true, current_timestamp());
-- remover (para de receber no próximo sync)
UPDATE cosin_aws_serverless_catalog.blog_digest.email_recipients
SET active = false WHERE email = 'saiu@cliente.com';
```

## Por que email via SQL Alert (legacy) disparado por job?

O ambiente não permite App Password de SMTP, então o envio usa o mecanismo nativo do Databricks
(SQL alert → Notification Destination de email). Para que o **envio fosse executado por um job**
(`sql_task`), usamos um **Legacy SQL alert** — os tasks de job só disparam alertas do tipo legacy
(o "SQL alert" v2 não é resolvido pela API de jobs nesta versão). O template é em PT-BR, em cards,
com disclaimer de que o conteúdo é **gerado por IA** e **não é comunicação oficial** da Databricks,
com link para cada artigo.

## Operação

- **Rodar tudo manualmente agora:** execute o job `blog_digest_diario` (popula/atualiza + sync)
  e depois `blog_send_semanal` (envia + marca).
- **Reenvio:** o digest só inclui posts com `weekly_sent = false`. Para reenviar um post,
  faça `UPDATE post_summaries SET weekly_sent = false WHERE url = '...'`.
- **Editar o texto/visual do email:** ajuste `subject`/`body` no `notebooks/00_preparar_email.py`
  e rode o notebook (ou o job de envio) — ele reaplica o template no alerta.
