# File Validator App

Databricks App para validação de arquivos. Upload de arquivos, validação contra regras configuráveis, histórico de validações.

## Stack
- **Backend:** FastAPI + Python (`uvicorn`)
- **Frontend:** React (em `frontend/`)
- **Workspace:** `fevm-cosin-aws-serverless.cloud.databricks.com`
- **Warehouse:** `0c2def7684630e5e`

## Estrutura
```
server/
  routes/        # Rotas da API
  db.py          # Inicialização de tabelas (init_tables no startup)
frontend/        # React SPA
notebooks/       # Notebooks auxiliares
app.py           # Entry point FastAPI (lifespan: init_tables)
```

## Inicialização
O app cria tabelas automaticamente no startup via `init_tables()` no lifespan do FastAPI.

## Comandos locais
```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar localmente
export DATABRICKS_HOST=fevm-cosin-aws-serverless.cloud.databricks.com
export DATABRICKS_TOKEN=<token>
export WAREHOUSE_ID=0c2def7684630e5e
uvicorn app:app --reload --port 8000

# Build frontend
cd frontend && npm install && npm run build
```

## Deploy
```yaml
# app.yaml
command: ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
env:
  DATABRICKS_HOST: fevm-cosin-aws-serverless.cloud.databricks.com
  WAREHOUSE_ID: "0c2def7684630e5e"
```

## Nota de segurança
O `DATABRICKS_TOKEN` no `app.yaml` atual está em texto plano — considerar mover para Databricks Secrets.
