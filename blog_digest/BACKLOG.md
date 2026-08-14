# Backlog / Tarefas futuras — Databricks Blog Digest

Itens planejados, ainda **não implementados**.

---

## TAREFA 1 — Seção de "Eventos por vir" no digest semanal

**Objetivo:** incluir, no mesmo e-mail semanal (numa **seção inferior**, abaixo dos posts),
os **eventos futuros** da Databricks para as regiões **Latin America** e **North America**.

### Origem dos dados
- URL: `https://www.databricks.com/events?event_type=all&region=latin-america,north-america`
- Aba **"Upcoming"** (eventos por vir) — é de lá que saem os eventos. (Há também "Featured" e
  "On Demand"; usar **somente Upcoming**.)
- A página mostra "Showing X-Y of N events" e cards. De cada card dá pra extrair:
  - **Nome** do evento (ex.: "Data + AI Summit 2026", "Unity Catalog Workshop")
  - **Tipo** (ex.: `IN-PERSON EVENT`, `WORKSHOP`, `WEBINAR`, `VIRTUAL EVENT`…)
  - **Data** (ex.: "June 15 – June 18", "June 29")
  - **Local** quando presencial (ex.: "San Francisco, United States")
  - **Link de registro** ("Register now")

### Regras de negócio
- **Persistência/controle:** manter o evento sendo enviado **enquanto ele aparecer** na página
  "Upcoming". Quando o evento **sair** da página, parar de incluí-lo no digest.
  → tabela de controle com `still_listed` (atualizado a cada scrape diário).
- O envio dos eventos ocorre **no mesmo e-mail semanal** (sexta), numa **seção inferior**,
  separada da seção de posts.
- Conteúdo por evento no e-mail: **nome**, **tipo** (presencial/workshop/etc.), **data** e
  **link de registro** — de forma breve.
- **Local:** mostrar **somente quando o evento for presencial** (in-person).
- **Filtro de presenciais:** manter apenas eventos presenciais do **Brasil** ou dos **EUA**
  (excluir presenciais de outros países). Eventos **não presenciais** (workshop/webinar/virtual)
  são mantidos normalmente, **sem** linha de local.

### Desenho proposto (para implementar)
1. **Nova tabela de controle** `upcoming_events`:
   | coluna | descrição |
   |---|---|
   | `event_key` | chave estável (ex.: slug/URL do registro, ou hash de nome+data) — PK |
   | `name` | nome do evento |
   | `event_type` | tipo (IN-PERSON / WORKSHOP / WEBINAR / VIRTUAL / …) |
   | `event_date` | texto da data como exibido (ex.: "June 15 – June 18") |
   | `location` | local (quando presencial) |
   | `register_url` | link de registro |
   | `region` | latin-america / north-america |
   | `first_seen_at` | 1ª vez que apareceu |
   | `last_seen_at` | última vez visto na página |
   | `still_listed` | BOOLEAN — true enquanto aparece em "Upcoming" |

2. **Novo notebook** `04_ingest_events.py` (rodar no **job diário**, após o `01`):
   - Scrape da página Upcoming (regiões LATAM + NA). Atenção: a lista pode ser paginada
     ("Showing 1-5 of 5") e/ou carregada via JS — validar se `requests`+BeautifulSoup pega
     os cards ou se precisa de outra abordagem (ex.: endpoint JSON interno / parâmetros de página).
   - **MERGE** em `upcoming_events`: upsert dos eventos vistos agora (atualiza `last_seen_at`,
     `still_listed=true`); marca `still_listed=false` os que **não** vieram no scrape atual.

3. **E-mail (seção de eventos):** o notebook `00_preparar_email` passa a também consultar
   `upcoming_events` (where `still_listed=true`) e **montar um bloco HTML de eventos** que é
   anexado ao `custom_body` **após a seção de posts** (os posts usam `{{#QUERY_RESULT_ROWS}}`;
   os eventos podem ser HTML estático montado no momento do preparar, já que são poucos).
   - Cabeçalho da seção: ex.: "📅 Eventos por vir".
   - Por evento: `[TIPO]` · **Nome** · Data (· Local) · link "Registrar".

### Status da investigação (2026-06-11) — BLOQUEIO conhecido
- A página de eventos é **Gatsby/React e renderiza os cards 100% via JavaScript**.
  `requests + BeautifulSoup` **NÃO funciona** (diferente do blog): os títulos/tipos/datas
  **não estão no HTML** servido.
- Testado e **sem sucesso**: JSON:API do Drupal (`/jsonapi/node/event*` → devolve o shell),
  `page-data.json` da rota `/events` (rota client-only, não existe estático), e grep nos
  bundles (`app.js`) — o endpoint dos eventos está num **chunk lazy** e não foi isolado.
- **Conclusão:** os eventos vêm de uma **chamada XHR em runtime**. Para implementar, escolher 1:
  1. **(recomendado)** Obter a URL/headers dessa XHR via **DevTools → Network (filtro Fetch/XHR)**
     ao carregar a página, e então consumir essa API direto com `requests` (leve e estável).
  2. **Navegador headless** (Playwright/Selenium) renderizando a página e raspando os cards —
     exige compute que rode browser (provável **cluster clássico + init script**; pode não
     funcionar no serverless atual). Mais pesado para um job semanal.

### Outros pontos de atenção
- Datas vêm como texto ("June 15 – June 18") — manter como texto é suficiente para o e-mail;
  se quiser ordenar/expirar por data, parsear para DATE.
- Deduplicação por `event_key` estável (preferir a URL de registro ou um slug do evento).
- Para o filtro Brasil/EUA, usar o campo de local/país do evento (presencial). Conferir como o
  país vem na API (ex.: "United States", "Brazil"/"Brasil").
