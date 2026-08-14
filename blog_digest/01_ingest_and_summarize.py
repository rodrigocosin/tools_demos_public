# Databricks notebook source
# MAGIC %md
# MAGIC # Databricks Blog — Ingestão incremental + Resumo PT-BR (diário)
# MAGIC
# MAGIC Este notebook:
# MAGIC 1. Acessa `https://www.databricks.com/blog` e coleta os posts recentes
# MAGIC 2. Faz carga **incremental** em `blog_posts` (dedup por URL — só insere o que ainda não existe)
# MAGIC 3. Para cada post novo, gera um **resumo em PT-BR** com `ai_query` usando o melhor LLM disponível
# MAGIC    (`databricks-claude-opus-4-8`) e grava em `post_summaries`
# MAGIC
# MAGIC Roda **diariamente**. O envio do email é feito por outro job (semanal, sexta-feira).

# COMMAND ----------

# MAGIC %pip install beautifulsoup4 lxml requests --quiet
# MAGIC %restart_python

# COMMAND ----------

# --- CONFIG (ajuste para seu ambiente) ---
CATALOG = "cosin_aws_serverless_catalog"          # <<< catálogo Unity Catalog
SCHEMA = "blog_digest"                             # <<< schema
LLM_ENDPOINT = "databricks-claude-opus-4-8"        # <<< melhor LLM disponível no workspace
# --- fixos ---
BLOG_LIST_URL = "https://www.databricks.com/br/blog"   # blog em português (BR)
BASE_URL = "https://www.databricks.com"
MAX_CONTENT_CHARS = 8000  # quanto do corpo do artigo enviamos ao LLM

# COMMAND ----------

import re
import hashlib
import datetime as dt
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DatabricksBlogDigest/1.0; +https://www.databricks.com)"
}

SLUG_RE = re.compile(r"^/br/blog/[a-z0-9][a-z0-9-]+$")


def fetch(url, timeout=30):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def discover_post_links(list_html):
    """Extrai URLs únicas de posts (/br/blog/<slug>) da página de listagem."""
    soup = BeautifulSoup(list_html, "lxml")
    slugs = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].split("#")[0].rstrip("/")
        # normaliza para path relativo
        if href.startswith(BASE_URL):
            href = href[len(BASE_URL):]
        if SLUG_RE.match(href):
            # ignora páginas de categoria/listagem
            if href.startswith("/br/blog/category"):
                continue
            slugs.setdefault(href, a.get_text(strip=True))
    return slugs  # {path: link_text}


def parse_post(path):
    """Busca a página do post e extrai título, data, categoria e corpo."""
    url = BASE_URL + path
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")

    def meta(prop=None, name=None):
        if prop:
            tag = soup.find("meta", property=prop)
        else:
            tag = soup.find("meta", attrs={"name": name})
        return tag["content"].strip() if tag and tag.get("content") else None

    # título
    title = meta(prop="og:title") or (soup.title.get_text(strip=True) if soup.title else None)
    if title:
        title = re.sub(r"\s*\|\s*Databricks.*$", "", title).strip()

    # data de publicação — tenta várias fontes (o blog NÃO usa ISO no meta tag)
    published_date = None
    # 1) JSON-LD "datePublished":"2026-06-09T18:09:16+0000"
    m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', html)
    if m:
        try:
            published_date = dt.date.fromisoformat(m.group(1))
        except Exception:
            published_date = None
    # 2) meta article:published_time formato "Tue, 06/09/2026 - 18:09"
    if not published_date:
        published = meta(prop="article:published_time") or meta(name="article:published_time")
        if published:
            mm = re.search(r'(\d{2})/(\d{2})/(\d{4})', published)
            if mm:
                month, day, year = mm.groups()
                try:
                    published_date = dt.date(int(year), int(month), int(day))
                except Exception:
                    published_date = None
    # 3) <time>June 9, 2026</time>
    if not published_date:
        tt = soup.find("time")
        if tt:
            try:
                published_date = dt.datetime.strptime(
                    tt.get_text(strip=True), "%B %d, %Y"
                ).date()
            except Exception:
                published_date = None

    # categoria/tipo do post (aparece no topo, ex.: "Engenharia", "Plataforma").
    # No /br/blog vem como link curto para /br/blog/category/<slug>.
    category = meta(prop="article:section") or meta(name="category")
    if not category:
        for a in soup.find_all("a", href=re.compile(r"^/br/blog/category/")):
            t = a.get_text(strip=True)
            if t and len(t) <= 30:   # ignora itens longos de menu/nav
                category = t
                break

    # breve resumo do post (excerpt exibido na listagem do blog), em PT
    excerpt = meta(prop="og:description") or meta(name="description") or ""

    # RESUMO OFICIAL do post (box "Resumo" no topo do artigo), já em PT.
    # Fica num <div class="... text-blog-summary ..."> com um <ul><li><strong>...</strong> ...</li>.
    resumo_div = soup.find("div", class_=re.compile(r"text-blog-summary"))
    post_resumo_html = resumo_div.decode_contents().strip() if resumo_div else ""
    post_resumo_text = resumo_div.get_text(" ", strip=True) if resumo_div else ""

    # corpo do artigo: junta parágrafos relevantes
    # remove nav/scripts/styles
    for bad in soup(["script", "style", "nav", "header", "footer", "aside"]):
        bad.decompose()
    paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    paras = [p for p in paras if len(p) > 40]  # descarta legendas/curtos
    content = "\n\n".join(paras)
    content = re.sub(r"\s+\n", "\n", content).strip()

    # contexto do LLM: prioriza o RESUMO OFICIAL; senão, o excerpt da listagem
    lead = post_resumo_text or excerpt
    if lead:
        if not content:
            content = lead
        elif lead[:60] not in content:
            rotulo = "Resumo oficial do post" if post_resumo_text else "Resumo do blog"
            content = f"{rotulo}: {lead}\n\n{content}"

    return {
        "url": url,
        "slug": path.rsplit("/", 1)[-1],
        "title": title,
        "category": category,
        "published_date": published_date,
        "content": content[:MAX_CONTENT_CHARS],
        "post_resumo_html": post_resumo_html,
    }


# COMMAND ----------

# 1) Descobre links de posts já existentes no destino (para evitar re-fetch desnecessário)
existing_urls = set(
    r["url"]
    for r in spark.sql(
        f"SELECT url FROM {CATALOG}.{SCHEMA}.blog_posts"
    ).collect()
)
print(f"Posts já ingeridos: {len(existing_urls)}")

# 2) Coleta a listagem do blog
list_html = fetch(BLOG_LIST_URL)
links = discover_post_links(list_html)
print(f"Links de posts encontrados na listagem: {len(links)}")

# 3) Mantém apenas os que ainda não existem (carga incremental)
new_paths = [
    p for p, _ in links.items()
    if (BASE_URL + p) not in existing_urls
]

# 3b) URLs extras informadas manualmente (widget extra_urls, separadas por vírgula).
#     Permite incluir posts que não estão mais na listagem (input manual).
dbutils.widgets.text("extra_urls", "")
for u in dbutils.widgets.get("extra_urls").split(","):
    u = u.strip()
    if not u:
        continue
    path = u.split("?")[0].split("#")[0]          # remove query/fragment
    if path.startswith(BASE_URL):
        path = path[len(BASE_URL):]
    path = path.rstrip("/")
    if (BASE_URL + path) not in existing_urls and path not in new_paths:
        new_paths.append(path)
        print(f"  + extra (manual): {path}")
print(f"Posts NOVOS a ingerir: {len(new_paths)}")

# COMMAND ----------

# 4) Faz o parse dos posts novos
rows = []
for path in new_paths:
    try:
        post = parse_post(path)
        if not post["title"]:
            print(f"  pulado (sem título): {path}")
            continue
        h = hashlib.sha256((post["content"] or "").encode("utf-8")).hexdigest()
        rows.append((
            post["url"], post["slug"], post["title"], post["category"],
            post["published_date"], None, post["content"], h,
            post.get("post_resumo_html", ""),
        ))
        print(f"  OK: {post['title'][:70]}  [{post['published_date']}]")
    except Exception as e:
        print(f"  ERRO em {path}: {e}")

print(f"\nPosts parseados com sucesso: {len(rows)}")

# COMMAND ----------

from pyspark.sql.types import (
    StructType, StructField, StringType, DateType, IntegerType
)

schema = StructType([
    StructField("url", StringType(), False),
    StructField("slug", StringType(), True),
    StructField("title", StringType(), True),
    StructField("category", StringType(), True),
    StructField("published_date", DateType(), True),
    StructField("read_minutes", IntegerType(), True),
    StructField("content", StringType(), True),
    StructField("content_hash", StringType(), True),
    StructField("post_resumo_html", StringType(), True),
])

if rows:
    df_new = spark.createDataFrame(rows, schema=schema)
    df_new.createOrReplaceTempView("new_posts")

    # 5) MERGE incremental — só insere URLs que ainda não existem
    spark.sql(f"""
        MERGE INTO {CATALOG}.{SCHEMA}.blog_posts t
        USING new_posts s
        ON t.url = s.url
        WHEN NOT MATCHED THEN INSERT (
            url, slug, title, category, published_date,
            read_minutes, content, content_hash, post_resumo_html, scraped_at
        ) VALUES (
            s.url, s.slug, s.title, s.category, s.published_date,
            s.read_minutes, s.content, s.content_hash, s.post_resumo_html, current_timestamp()
        )
    """)
    print(f"MERGE concluído — {len(rows)} posts candidatos.")
else:
    print("Nenhum post novo para inserir.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## "Por que importa" via LLM
# MAGIC O **resumo já existe** no post (capturado em `post_resumo_html`). A LLM
# MAGIC (`databricks-claude-opus-4-8`) é usada **apenas** para gerar um parágrafo curto de
# MAGIC **por que aquele post importa** para o cliente. O resto (título PT, resumo oficial,
# MAGIC categoria) vem direto do scraping.

# COMMAND ----------

# Prompt do "por que importa" (LLM gera só esta frase curta)
PQI_HEAD = """Você é um analista da Databricks escrevendo para clientes brasileiros.
Em 1 a 2 frases CURTAS, em português do Brasil, explique POR QUE este post importa para o cliente — o valor ou impacto prático. Seja específico e direto. NÃO repita o título, NÃO liste recursos e NÃO comece com "Este post". Responda apenas com a(s) frase(s), sem rótulos.

Post:
Título: """

PQI_MID = """
Conteúdo:
"""

# COMMAND ----------

# Conta quantos posts ainda não têm registro em post_summaries
pendentes = spark.sql(f"""
    SELECT COUNT(*) AS n
    FROM {CATALOG}.{SCHEMA}.blog_posts p
    LEFT ANTI JOIN {CATALOG}.{SCHEMA}.post_summaries s ON p.url = s.url
""").collect()[0]["n"]
print(f"Posts aguardando processamento: {pendentes}")

# COMMAND ----------

if pendentes and pendentes > 0:
    sql = f"""
        INSERT INTO {CATALOG}.{SCHEMA}.post_summaries
            (url, title_pt, resumo, resumo_html, bullets_json, por_que_importa,
             disponibilidade, links_importantes, model_used, summarized_at,
             weekly_sent, weekly_sent_at, send_status)
        SELECT
            p.url,
            p.title                                                        AS title_pt,
            -- resumo em texto plano: tira as tags do resumo oficial
            nullif(trim(regexp_replace(coalesce(p.post_resumo_html, ''), '<[^>]+>', ' ')), '') AS resumo,
            -- resumo_html = RESUMO OFICIAL do post; fallback: trecho do conteúdo
            coalesce(
                nullif(p.post_resumo_html, ''),
                concat('<p>', left(regexp_replace(coalesce(p.content, ''), '<[^>]+>', ' '), 500), '…</p>')
            )                                                              AS resumo_html,
            CAST(NULL AS STRING)       AS bullets_json,
            -- ÚNICO uso de LLM: parágrafo curto de "por que importa"
            trim(ai_query(
                '{LLM_ENDPOINT}',
                CONCAT(:pqi_head, COALESCE(p.title, ''), :pqi_mid, COALESCE(p.content, ''))
            ))                                                             AS por_que_importa,
            CAST(NULL AS STRING)       AS disponibilidade,
            CAST(NULL AS STRING)       AS links_importantes,
            '{LLM_ENDPOINT}'           AS model_used,
            current_timestamp()        AS summarized_at,
            false                      AS weekly_sent,
            CAST(NULL AS TIMESTAMP)    AS weekly_sent_at,
            'pending'                  AS send_status
        FROM {CATALOG}.{SCHEMA}.blog_posts p
        LEFT ANTI JOIN {CATALOG}.{SCHEMA}.post_summaries s ON p.url = s.url
    """
    spark.sql(sql, args={"pqi_head": PQI_HEAD, "pqi_mid": PQI_MID})
    print("'Por que importa' gerado e registros gravados em post_summaries.")
else:
    print("Nada pendente.")

# COMMAND ----------

# Visão final
display(spark.sql(f"""
    SELECT p.published_date, p.category AS categoria, s.title_pt,
           s.por_que_importa, s.send_status
    FROM {CATALOG}.{SCHEMA}.post_summaries s
    JOIN {CATALOG}.{SCHEMA}.blog_posts p ON p.url = s.url
    ORDER BY p.published_date DESC
    LIMIT 50
"""))

