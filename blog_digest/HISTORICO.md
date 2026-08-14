# Histórico da construção — Databricks Blog Digest

Registro da sessão (Claude Code) que construiu a solução, para **retomar no futuro**.
Inclui objetivo, decisões, arquitetura final, IDs dos recursos, lições aprendidas e o
passo a passo de tudo que foi pedido/ajustado.

> Documentos vivos: `README.md` (visão geral) e `SETUP.md` (replicação). Este arquivo é o
> **diário** da construção — por que as coisas são como são.

---

## 1. Objetivo

Manter clientes atualizados sobre os posts do blog da Databricks
(`https://www.databricks.com/br/blog` — versão PT), com resumos ainda mais enxutos:

- Ingestão **diária** dos posts recentes, com **carga incremental** (sem duplicar dias anteriores).
- **Resumo em português** de cada post (via LLM), com visão geral, por que importa,
  disponibilidade e **link** para o artigo oficial.
- **Envio semanal por e-mail** (sexta-feira) para uma lista que vive em **tabela**.
- Disclaimers: conteúdo **gerado por IA / não oficial** e **disponibilidade não garantida**
  (varia por Cloud/região/fase).

---

## 2. Ambiente

| Item | Valor |
|---|---|
| Workspace | `https://fevm-cosin-aws-serverless.cloud.databricks.com` (FEVM, AWS serverless) |
| Profile CLI | `fe-vm-cosin-aws-serverless` |
| Catálogo / Schema | `cosin_aws_serverless_catalog.blog_digest` |
| SQL Warehouse | `0c2def7684630e5e` (Serverless Starter, data_source `ef7e6858-aa3d-44ee-a8b8-2ef5408c9027`) |
| LLM (resumos) | `databricks-claude-opus-4-8` (melhor disponível no workspace) |
| Pasta dos notebooks | `/Workspace/Users/rodrigo.cosin@databricks.com/tools_demos_public/blog_digest/` |

---

## 3. Arquitetura final

```
JOB DIÁRIO  "blog_digest_diario"  (08:00 BRT)
  ├─ 01_ingest_and_summarize : scrape do blog → MERGE incremental (dedup por URL)
  │                            → resumo PT-BR (ai_query Opus 4.8) → post_summaries
  └─ 02_sync_recipients      : 1 Notification Destination por destinatário ATIVO
                               (cria/atualiza/remove) + atualiza as subscriptions
                               da task de envio do job semanal (pré-staging p/ sexta)

JOB DE ENVIO  "blog_send_semanal"  (sexta 10:00 BRT)
  ├─ preparar_email   (00) : assunto "Databricks Blog — Resumo da semana YYYY-MM-DD"
  │                          + aplica o template (cards, <hr>, 2 disclaimers);
  │                          expõe taskValue "pendentes"
  ├─ tem_conteudo (gate)   : só segue se pendentes > 0 (senão envio/marcação = EXCLUDED)
  ├─ enviar_digest (sql)   : Legacy SQL alert → 1 e-mail INDIVIDUAL por destino (ocultos)
  └─ marcar_enviados  (03) : weekly_sent=true + weekly_sent_at=agora
```

**Por que e-mail via Legacy SQL alert disparado por job?**
- SMTP/App Password não é permitido no ambiente → usa o envio nativo (alert → destination).
- Para o **envio rodar dentro de um job** (`sql_task`), precisa ser **alert LEGACY**
  (o "SQL alert" v2 não é resolvido pela API de jobs nesta versão do CLI).
- O alert legacy também é o que suporta o **template Mustache** (`{{#QUERY_RESULT_ROWS}}` / `{{{coluna}}}`).

---

## 4. Tabelas (`cosin_aws_serverless_catalog.blog_digest`)

- **`blog_posts`** — posts ingeridos (fonte da verdade p/ dedup por URL).
- **`post_summaries`** — `title_pt`, `resumo` (texto plano ~700 chars, com sub-pontos),
  `resumo_html` (bullets HTML p/ e-mail), `bullets_json` (estrutura crua p/ re-derivar sem LLM),
  `disponibilidade`, `links_importantes`, `model_used`, `summarized_at`,
  **`weekly_sent` / `weekly_sent_at`** (controle e histórico de envio).
- **`email_recipients`** — lista de destinatários (campo `active`). Fonte da verdade.

> Não há tabelas de controle separadas: o histórico de envios sai de `post_summaries.weekly_sent_at`.

---

## 5. Recursos no workspace (IDs deste ambiente)

| Recurso | Nome / ID |
|---|---|
| Job diário | `blog_digest_diario` — `72615450561326` |
| Job de envio | `blog_send_semanal` — `696804447163687` |
| Legacy SQL alert | `Databricks Blog Digest - Semanal` — `b5a63e41-6b3e-4cd7-aaa9-eb55701d95a5` |
| Legacy SQL query | `Blog Digest - query semanal` — `bd628f7a-bfad-4a3c-9ac9-e9e8c2104b25` |
| Notification Destinations | um por destinatário, nome `Blog Digest :: <email>` |

Notebooks: `00_preparar_email`, `01_ingest_and_summarize`, `02_sync_recipients`,
`03_weekly_log`, `setup_deploy`. Arquivos de apoio: `README.md`, `SETUP.md`, `deploy.sh`,
`run_sql.py`, `sql/01_setup_schema.sql`, `jobs/*.json`.

Destinatários atuais: `rodrigocosin@gmail.com` (ativo), `rodrigo.cosin@databricks.com` (ativo),
`rodolfo.catharino@databricks.com` (inativo — desativado em teste).

---

## 6. Decisões e lições aprendidas (o "porquê")

| Tema | Decisão / problema | Solução final |
|---|---|---|
| Mostrar posts no e-mail | condição com **agregação** mostrava `count=10` em vez das linhas | `column=n` (row_number) **sem agregação** → mostra as linhas |
| Layout | tabela ficava larga e confusa | **cards** via Mustache (`{{#QUERY_RESULT_ROWS}}` + `{{{resumo_html}}}`) |
| Link some no Gmail | botão com fundo colorido (Gmail remove) | link com **borda vermelha** + texto vermelho |
| Título x link iguais | ambos vermelhos | título em **azul-escuro `#1B3139`**, link vermelho `#FF3621` |
| Resumo extenso | parágrafos longos | LLM gera **bullets concisos** (~700 chars) com sub-pontos opcionais |
| Não reenviava | `rearm=0` (notifica só na 1ª transição) | **`rearm=1`** (re-notifica a cada execução) |
| Enviou e-mail vazio | resultado vazio disparava | **`empty_result_state=ok`** + **condition_task** (gate) no job |
| Critério de envio | janela de 7 dias | **`weekly_sent=false`** (só o que ainda não foi enviado) |
| Destinatários se viam | 1 destino com vários e-mails (todos no "Para") | **1 destino por pessoa** + alerta inscrito em todos → e-mails individuais/ocultos |
| Subscriptions do envio | vêm do `sql_task` (estáticas, snapshot no início do run) | sync roda no **job diário** (pré-staging), atualiza as subscriptions do job semanal |
| E-mail externo | `user_name` só serve p/ usuário do workspace | clientes externos exigem **Notification Destination** |
| Tabelas de controle | `weekly_send_log` / `weekly_send_items` redundantes | removidas (e depois reintroduzida `send_log` p/ auditoria de lotes) |
| Assunto threadava no Gmail | "(gerado por IA)" + mesma data | **"Resumo semanal — Blog da Databricks (DD/MM/AAAA)"**; "gerado por IA" só no disclaimer |
| Resumo = trabalho do LLM redundante | LLM resumia o que já tinha resumo no post | resumo passou a ser o **OFICIAL do post** (`post_resumo_html`); LLM gera só **"por que importa"** |
| Categoria do post | não exibida / badge invisível (fundo removido pelo Gmail) | badge com **borda** + texto escuro; categoria capturada do topo do post |
| **Envio a 50+ destinos não entregava** | **limite/throttle do alerta** p/ notificação em massa (2 entrega, 53 não) | **envio em LOTES** (`04_enviar_lotes`): ~10 destinos por disparo, com pausa |
| Auditoria/controle de envio | só boolean | **`send_status`** (pending/skip/sent) + tabela **`send_log`** (1 linha por lote) |
| Multi-SA | lista única | sync/envio filtram por **`sa`** — cada SA envia só p/ seus contatos |

---

## 7. Linha do tempo dos pedidos (o que foi ajustado, em ordem)

1. Criar o JOB de ingestão + resumo PT-BR + envio semanal por e-mail (lista em tabela).
2. SMTP sem App Password → usar **SQL Alert** para envio. Schema em `cosin_aws_serverless_catalog`. Envio **sexta**.
3. Disclaimer de IA (não oficial; acessar link). Lista inicial só `rodrigocosin@gmail.com`.
4. Validado: scraping, resumo (Opus 4.8), alerta enviando para Gmail externo.
5. E-mail mostrava agregação → corrigido (sem agregação, mostra os posts).
6. Layout em **cards**, só Post/Resumo/Link, resumo em **bullets** (com hierarquia), sem disponibilidade no card; corrigido o link que sumia.
7. Resumo ainda mais curto (~700 chars).
8. Critério de envio passou a ser **"ainda não enviados"** (`weekly_sent=false`).
9. Removidas as tabelas de controle (usar `weekly_sent_at`).
10. Explicado `resumo` vs `resumo_html`; `resumo` passou a incluir sub-pontos; criada `bullets_json`.
11. **Envio via JOB** (Legacy alert + `sql_task`); criados os 2 jobs; reset/recriações de alerta.
12. Assunto com **YYYY-MM-DD**; removido "(gerado por IA)" do assunto.
13. Gate de conteúdo (não enviar vazio) com `condition_task` + `empty_result_state=ok`.
14. `sync_recipients` movido para o fluxo de envio; depois para o **job diário** (pré-staging das subscriptions).
15. Adicionados `rodrigo.cosin@databricks.com` e `rodolfo.catharino@databricks.com`.
16. **Destinatários ocultos** → 1 Notification Destination por pessoa (validado).
17. Job semanal renomeado para **`blog_send_semanal`**.
18. Documentação para replicação: `SETUP.md`, `deploy.sh`, e o notebook **`setup_deploy`** (deploy 100% dentro do Databricks).
19. Arquivos de apoio subidos para a pasta no workspace; pasta movida para `tools_demos_public/blog_digest` (caminhos ajustados).
20. Segundo disclaimer no corpo: **disponibilidade não garantida** (Cloud/região/fase).

---

## 8. Como operar

- **Adicionar/remover destinatário:** editar `email_recipients` (campo `active`). O job diário
  sincroniza destinos e subscriptions automaticamente.
- **Forçar reenvio de um post:** `UPDATE post_summaries SET weekly_sent=false WHERE url='...'`.
- **Mudar visual/textos do e-mail:** editar `body`/`subject` em `00_preparar_email.py` e rodar
  o notebook (ou o job de envio) para reaplicar no alerta.
- **Rodar manualmente:** `databricks jobs run-now <job_id> --profile fe-vm-cosin-aws-serverless`
  ou via UI. Ordem: diário (popula + sync) → de envio.

## 9. Replicar em outro ambiente

Ver `SETUP.md`. Recomendado: abrir o notebook **`setup_deploy`**, ajustar o bloco CONFIG e
**Run all** (cria tudo dentro do Databricks). Alternativas: `deploy.sh` (CLI local) ou manual.

## 10. Possíveis melhorias futuras (não implementadas)

- Reativar `rodolfo.catharino@databricks.com` quando quiser (`active=true`).
- Paginação no `02_sync_recipients` caso a lista de destinos fique > ~100.
- Idempotência no `setup_deploy` (hoje cria objetos novos a cada execução).
- Internacionalização / outro idioma, se necessário.
