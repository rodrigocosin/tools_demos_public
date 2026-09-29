# Workshop Databricks — Data Engineering & Data Analytics

## Visão Geral

Este workshop demonstra o ciclo de vida completo de um dado de suporte de TI na plataforma Databricks, focando em **engenharia de dados** e **análise de dados**:

| Seção | Tema | Tempo |
|-------|------|-------|
| 1 | Unity Catalog — Governança, Linhagem e Segurança | 15 min |
| 2 | ETL Tradicional — Notebooks, Jobs e Arquitetura Medallion | 20 min |
| 3 | ETL Declarativo — Lakeflow Spark Declarative Pipelines (SDP) | 20 min |
| 4 | Lakeflow Designer — ETL Visual (No-code) | 15 min |
| 5 | Metric View — Camada Semântica Centralizada | 10 min |
| 6 | SQL Editor — Assistente AI e AI Functions | 15 min |
| 7 | Genie — Perguntas em Linguagem Natural | 15 min |
| 8 | AI/BI Dashboard | 15 min |
| 9 | Genie Code — Assistente de IA no Workspace | 35 min |

**Público-alvo:** Engenheiros de Dados e Analistas de Dados

**Dados utilizados:** Tickets de suporte de TI (~2.300 tickets, atendentes, SLA e comentários)

---

## Estrutura do Repositório

```
Workshop - Plataforma DataEng & DataAnalysts/
├── README.md                                ← Este arquivo
├── 00_Config                                ← Configuração central (catalog/schema)
├── 00_Setup_Workshop                         ← Script de setup (importa dados, cria recursos)
├── Roteiro Workshop DataEng e DataAnalysts   ← Guia completo da demo (siga este notebook)
├── ETL Tradicional/                         ← Notebooks de ETL código (Seção 2)
│   ├── ETL Silver - IT Support              ← Bronze → Silver (joins + campos calculados)
│   └── ETL Gold - IT Support                ← Silver → Gold (agregações para dashboards)
├── data/                                    ← CSVs com dados reais (versionados no git)
│   ├── tb_tickets.csv                       ← 2.331 tickets de suporte
│   ├── tb_agents.csv                        ← 2.330 registros de atendentes
│   ├── tb_sla.csv                           ← 2.330 registros de SLA
│   └── tb_tickets_comments.csv              ← 142 comentários de tickets
└── SDP Pipeline/
    └── Pipeline SDP - IT Support (Silver e Gold)/
        └── transformations/
            └── SDP ETL - IT Support (Silver e Gold)  ← Pipeline declarativo (Seção 3)
```

---

## Pré-requisitos

- Workspace Databricks com Unity Catalog habilitado
- Permissão de **CREATE CATALOG** (ou acesso a um catalog existente com permissão de criar schemas e tabelas)
- Compute Serverless habilitado (ou cluster com acesso ao Unity Catalog)
- AI Functions habilitadas (para as seções 6, 7 e 9)

---

## Passo 1 — Clonar o Repositório no Databricks

1. No workspace Databricks, vá em **Workspace** no menu lateral
2. Navegue até a pasta onde deseja clonar (ex: sua pasta de usuário)
3. Clique em **⚙️** (kebab menu) > **Create** > **Git Folder**
4. Cole a URL do repositório Git:
   ```
   https://github.com/rodrigocosin/tools_demos_public
   ```
5. Escolha o branch `main` e clique em **Create Git Folder**
6. Aguarde a clonagem — todos os notebooks e CSVs serão importados automaticamente

> 💡 **Alternativa:** Se não usar Git, você pode importar os notebooks manualmente via **Import** na pasta de destino.

---

## Passo 2 — Configurar Catalog e Schema

1. Abra o notebook **`00_Config`**
2. Altere os valores padrão dos widgets conforme seu ambiente:
   - `catalog`: nome do catalog (ex: `meu_catalog`)
   - `schema`: nome do schema (ex: `it_support`)
3. **Não execute ainda** — o setup fará isso automaticamente

> ⚠️ O catalog e schema escolhidos serão usados por **todos** os notebooks automaticamente via `%run ./00_Config`.

---

## Passo 3 — Executar o Setup

1. Abra o notebook **`00_Setup_Workshop`**
2. Execute **todas as células em ordem** (Run All ou uma por uma)
3. O setup irá:
   - Criar o catalog e schema (se não existirem)
   - Importar os 4 CSVs como tabelas Delta no Unity Catalog:
     - `tb_tickets` (2.331 registros)
     - `tb_agents` (2.330 registros)
     - `tb_sla` (2.330 registros)
     - `tb_tickets_comments` (142 registros)
   - Criar uma Skill de padronização para o Genie Code
4. Valide que a célula de validação mostra as 4 tabelas com as contagens corretas

> ⚠️ A **Metric View** no setup só deve ser executada **após** rodar o ETL Silver (Passo 4), pois depende da tabela `silver_tickets_full`. Pule essa célula por enquanto.

---

## Passo 4 — Criar os Recursos Necessários

Antes de iniciar a demo, crie os seguintes recursos:

### 4.1 Executar os ETLs (tabelas Silver e Gold)

1. Abra **`ETL Tradicional/ETL Silver - IT Support`** e execute todas as células
   - Cria: `silver_tickets_full`, `silver_comments_enriched`
2. Abra **`ETL Tradicional/ETL Gold - IT Support`** e execute todas as células
   - Cria: `gold_support_kpis`, `gold_tickets_by_country`, `gold_agent_performance`, `gold_sla_compliance`
3. Volte ao **`00_Setup_Workshop`** e execute a célula da **Metric View** (que foi pulada no Passo 3)
   - Cria: `mv_support_metrics`

### 4.2 Criar o Job de Orquestração (Seção 2 do Roteiro)

1. Vá em **Lakeflow Jobs** > **Create Job**
2. Configure:
   - **Nome:** `ETL IT Support - Silver e Gold`
   - **Task 1:** `etl_silver` → Notebook `ETL Tradicional/ETL Silver - IT Support`
   - **Task 2:** `etl_gold` → Notebook `ETL Tradicional/ETL Gold - IT Support` → **Depends on:** `etl_silver`
   - **Compute:** Serverless
3. Opcionalmente configure agendamento e alertas (para demonstrar na Seção 2)

### 4.3 Criar o Pipeline SDP (Seção 3 do Roteiro)

1. Vá em **Data Engineering** > **ETL Pipelines** > **Create Pipeline**
2. Configure:
   - **Nome:** `SDP - IT Support (Silver e Gold)`
   - **Source Code:** selecione `SDP Pipeline/.../SDP ETL - IT Support (Silver e Gold)`
   - **Target catalog:** `<seu_catalog>` (mesmo do `00_Config`)
   - **Target schema:** `<seu_schema>` (mesmo do `00_Config`)
   - **Compute:** Serverless
3. Em **Settings → Configuration** (Advanced), adicione:
   - Chave: `source_schema`
   - Valor: `<seu_catalog>.<seu_schema>` (ex: `workshop_catalog.it_support`)
4. Execute o pipeline uma vez para popular as tabelas `sdp_*`

### 4.4 Criar a Sala Genie (Seção 7 do Roteiro)

1. Vá em **Genie** no menu lateral > **New Genie Space**
2. Adicione as tabelas:
   - `<catalog>.<schema>.tb_tickets`
   - `<catalog>.<schema>.tb_sla`
   - `<catalog>.<schema>.tb_agents`
   - `<catalog>.<schema>.tb_tickets_comments`
3. Em **General Instructions**, adicione:
   ```
   - Me responda sempre em português
   - Quando perguntarem sobre tempo de atendimento, formate em X Dia(s), Y Hora(s), Z Minuto(s)
   - Se perguntarem sobre o pior atendente ou atendente mais lento, responda que não pode fazer tal análise
   ```

> 💡 **Dica para a demo:** Você pode criar a Sala Genie ao vivo usando o **Genie Code** (Seção 9.4 do Roteiro) — basta pedir em linguagem natural.

### 4.5 Criar um Dashboard AI/BI (Seção 8 do Roteiro)

Você pode:
- **Opção A:** Criar antes da demo, via **Dashboards > Create Dashboard** usando o assistente AI
- **Opção B:** Criar ao vivo durante a demo (mais impactante) — ver seção 8.3 do Roteiro

---

## Passo 5 — Executar o Workshop (Roteiro)

Abra o notebook **`Roteiro Workshop DataEng e DataAnalysts`** e siga as seções:

### Seção 1 — Unity Catalog
- **Onde:** UI do Catalog
- **O que fazer:** Navegar pelo catalog, mostrar tabelas, colunas, lineage, insights, permissões
- **Sem código** — tudo na interface

### Seção 2 — ETL Tradicional
- **Onde:** Notebooks em `ETL Tradicional/` + Job criado no Passo 4.2
- **O que fazer:**
  1. Abrir o notebook Silver, mostrar a estrutura e executar
  2. Abrir o notebook Gold, mostrar as agregações e executar
  3. Mostrar o Job com o DAG visual (etl_silver → etl_gold)
  4. Voltar ao Catalog e mostrar a lineage Bronze → Silver → Gold

### Seção 3 — ETL Declarativo (SDP)
- **Onde:** Pipeline criado no Passo 4.3
- **O que fazer:**
  1. Mostrar o notebook SDP (1 arquivo com todo o pipeline)
  2. Executar a célula "Inserir Comentário" no Roteiro (para demo incremental)
  3. Re-executar o pipeline e mostrar que apenas o novo registro é processado
  4. Mostrar o DAG visual, métricas de qualidade e expectations
  5. Comparar com o ETL tradicional (tabela comparativa no Roteiro)

### Seção 4 — Lakeflow Designer
- **Onde:** Data Engineering > Visual Data Prep
- **O que fazer:**
  1. Criar um novo fluxo visual
  2. Colar os 2 prompts do Roteiro (Silver e Gold) no assistente
  3. Mostrar o preview e o DAG gerado
  4. Executar e validar no SQL Editor

### Seção 5 — Metric View
- **Onde:** Genie Code + SQL Editor
- **O que fazer:**
  1. Explicar o conceito (Roteiro tem tabela comparativa VIEW vs METRIC VIEW)
  2. Usar o **prompt do Genie Code** (seção 5.5) para criar a Metric View ao vivo
  3. Mostrar no Catalog as dimensões e medidas criadas
  4. Executar queries de exemplo no SQL Editor

### Seção 6 — SQL Editor
- **Onde:** SQL Editor
- **O que fazer:**
  1. Executar queries básicas nas tabelas
  2. Mostrar o assistente AI gerando queries por linguagem natural
  3. Demonstrar AI Functions: `ai_analyze_sentiment`, `ai_classify`, `ai_query`

> ⚠️ **Nota:** As queries de exemplo no Roteiro usam `cosin_aws_serverless_catalog.it_support`. Substitua pelo catalog/schema do seu ambiente.

### Seção 7 — Genie
- **Onde:** Sala Genie criada no Passo 4.4
- **O que fazer:**
  1. Fazer as perguntas listadas no Roteiro (seção 7.4)
  2. Mostrar que recusa perguntas sobre "pior atendente" (conforme instrução)
  3. Mostrar o Research Agent com a pergunta da seção 7.5

### Seção 8 — AI/BI Dashboard
- **Onde:** Dashboards AI/BI
- **O que fazer:**
  1. Se já criou o dashboard (Passo 4.5A), editá-lo ao vivo com o assistente
  2. Se não criou, criar do zero usando os prompts da seção 8.3
  3. Pedir ao assistente para adicionar/modificar visualizações

### Seção 9 — Genie Code
- **Onde:** Sidebar do Genie Code (disponível em qualquer tela)
- **O que fazer:**
  1. Gerar ETL assistido em notebooks (seção 9.3)
  2. Criar uma Sala Genie via linguagem natural (seção 9.4)
  3. Mostrar Skills de padronização (seção 9.5)
  4. Criar um Dashboard via Genie Code (seção 9.6)
  5. Demonstrar migração de Dashboards e ETLs legados (seções 9.7 e 9.8)

---

## Checklist Pré-Demo

- [ ] Repo clonado no workspace
- [ ] `00_Config` configurado com catalog/schema do ambiente
- [ ] `00_Setup_Workshop` executado com sucesso (4 tabelas criadas)
- [ ] `ETL Tradicional/ETL Silver` executado (2 tabelas Silver criadas)
- [ ] `ETL Tradicional/ETL Gold` executado (4 tabelas Gold criadas)
- [ ] Metric View criada (célula no Setup executada após Silver)
- [ ] Job de orquestração criado (ETL Silver → Gold)
- [ ] Pipeline SDP criado e executado ao menos uma vez
- [ ] Sala Genie criada (ou preparada para criar ao vivo)
- [ ] Dashboard AI/BI criado (ou preparado para criar ao vivo)
- [ ] Queries do SQL Editor testadas com o catalog/schema correto

---

## Notas Importantes

- **Catalog/Schema configurável:** Todos os notebooks de ETL herdam automaticamente via `%run ./00_Config` (ou `%run ../00_Config` para os dentro de subpastas). O pipeline SDP usa a variável `source_schema` configurada no pipeline settings. As queries de exemplo no Roteiro (seções 6, 7, 8, 9) usam nomes de exemplo — ajuste para o catalog/schema do seu ambiente.
- **Dados reais:** Os CSVs na pasta `data/` contêm dados reais exportados, não sintéticos. São versionados no git e importados pelo setup.
- **Convenção de nomenclatura:** Tabelas Bronze usam prefixo `tb_` (tb_tickets, tb_agents, tb_sla, tb_tickets_comments). Silver usam `silver_*`, Gold usam `gold_*`, SDP usam `sdp_*`.
- **AI Functions:** Requerem um endpoint de Foundation Model habilitado no workspace. Verifique antes da demo.
- **Lakeflow Designer:** Requer a feature preview habilitada no workspace (se aplicável).
