-- =====================================================================
-- Setup do schema e tabelas para o Databricks Blog Digest
-- Catalogo: cosin_aws_serverless_catalog | Schema: blog_digest
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS cosin_aws_serverless_catalog.blog_digest
  COMMENT 'Ingestao, resumo (PT-BR via LLM) e envio semanal dos posts do blog da Databricks';

-- ---------------------------------------------------------------------
-- Posts ingeridos do blog (fonte da verdade para dedup incremental)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cosin_aws_serverless_catalog.blog_digest.blog_posts (
  url            STRING    NOT NULL COMMENT 'URL absoluta do post (chave de deduplicacao)',
  slug           STRING    COMMENT 'Slug do post (parte final da URL)',
  title          STRING    COMMENT 'Titulo original (EN)',
  category       STRING    COMMENT 'Categoria informada na listagem',
  published_date DATE      COMMENT 'Data de publicacao',
  read_minutes   INT       COMMENT 'Tempo estimado de leitura em minutos',
  content          STRING    COMMENT 'Texto principal do artigo (extraido do HTML)',
  content_hash     STRING    COMMENT 'Hash do conteudo para detectar mudancas',
  post_resumo_html STRING    COMMENT 'RESUMO oficial do post (box no topo do artigo), em HTML <ul>',
  scraped_at       TIMESTAMP COMMENT 'Quando o post foi capturado pela primeira vez'
)
USING DELTA
COMMENT 'Posts do blog da Databricks ingeridos de forma incremental';

-- ---------------------------------------------------------------------
-- Resumos PT-BR gerados por LLM (1:1 com blog_posts)
-- Inclui o controle de envio (weekly_sent / weekly_sent_at) -> historico
-- de envios e derivado daqui, sem tabelas de controle separadas.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cosin_aws_serverless_catalog.blog_digest.post_summaries (
  url                STRING    NOT NULL COMMENT 'URL do post (FK -> blog_posts.url)',
  title_pt           STRING    COMMENT 'Titulo em PT-BR',
  resumo             STRING    COMMENT 'Resumo conciso (~700 chars) em texto plano, com sub-pontos entre parenteses',
  resumo_html        STRING    COMMENT 'Resumo em bullets (HTML <ul>) usado no email',
  bullets_json       STRING    COMMENT 'Estrutura crua dos bullets (JSON) p/ re-derivar resumo/resumo_html sem LLM',
  por_que_importa    STRING    COMMENT 'Reservado (atualmente nulo; o porque importa e tecido nos bullets)',
  disponibilidade    STRING    COMMENT 'Status de disponibilidade (GA, Preview, evento, etc.)',
  links_importantes  STRING    COMMENT 'Links relevantes citados no post',
  model_used         STRING    COMMENT 'Endpoint LLM usado para o resumo',
  summarized_at      TIMESTAMP COMMENT 'Quando o resumo foi gerado',
  weekly_sent        BOOLEAN   COMMENT 'Compat: true quando enviado/omitido (controle real e send_status)',
  weekly_sent_at     TIMESTAMP COMMENT 'Quando foi enviado',
  send_status        STRING    COMMENT 'pending=envia, skip=omitido proposital, sent=enviado'
)
USING DELTA
COMMENT 'Resumos PT-BR por post + controle de envio semanal';

-- ---------------------------------------------------------------------
-- Lista de destinatarios (fonte da verdade da lista de emails)
-- ---------------------------------------------------------------------
-- ---------------------------------------------------------------------
-- Log de execuções de envio (1 linha por LOTE) — auditoria do batching
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cosin_aws_serverless_catalog.blog_digest.send_log (
  execution_id  STRING    COMMENT 'Agrupa um envio (uma execucao)',
  execution_ts  TIMESTAMP COMMENT 'Inicio da execucao',
  batch_idx     INT       COMMENT 'Indice do lote',
  batches_total INT       COMMENT 'Total de lotes na execucao',
  dest_count    INT       COMMENT 'Qtd de destinos no lote',
  emails        STRING    COMMENT 'E-mails do lote (separados por virgula)',
  sub_run_id    STRING    COMMENT 'Run id do disparo do lote',
  result_state  STRING    COMMENT 'SUCCESS/FAILED do lote',
  posts_count   INT       COMMENT 'Qtd de posts no digest enviado',
  post_titles   STRING    COMMENT 'Titulos dos posts enviados',
  logged_at     TIMESTAMP COMMENT 'Quando o log foi gravado'
)
USING DELTA
COMMENT 'Historico de execucoes de envio (por lote)';

-- ---------------------------------------------------------------------
-- Lista de destinatarios (fonte da verdade da lista de emails)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cosin_aws_serverless_catalog.blog_digest.email_recipients (
  company   STRING    COMMENT 'Empresa onde a pessoa trabalha',
  email     STRING    NOT NULL COMMENT 'Email do destinatario',
  name      STRING    COMMENT 'Nome do destinatario',
  active    BOOLEAN   COMMENT 'Se deve receber o digest',
  added_at  TIMESTAMP COMMENT 'Quando foi adicionado',
  sa        STRING    COMMENT 'Nome do Solutions Architect (SA) da conta',
  ae        STRING    COMMENT 'Nome do Account Executive (AE) da conta',
  CONSTRAINT pk_email_recipients PRIMARY KEY (email)
)
USING DELTA
COMMENT 'Lista de destinatarios do digest semanal';
