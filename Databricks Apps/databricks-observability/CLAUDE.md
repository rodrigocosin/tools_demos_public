# Databricks Observability Dashboard

Databricks App para monitoramento de Jobs e Runs do workspace. Dashboard de observabilidade com React + FastAPI.

## Stack
- **Backend:** FastAPI + Python (`uvicorn`)
- **Frontend:** React (em `frontend/`)
- **Auth:** `x-forwarded-access-token` (OAuth do usuário via Databricks Apps proxy) ou `DATABRICKS_TOKEN` (service principal)
- **SDK:** `databricks-sdk` para listar jobs e runs

## Rotas da API
- `GET /api/jobs` — lista todos os jobs do workspace
- `GET /api/runs` — lista runs recentes
- `GET /api/debug` — debug de auth e conectividade

## Estrutura
```
server/
  routes/
    jobs.py        # Lista jobs
    runs.py        # Lista runs
  config.py        # workspace client, IS_DATABRICKS_APP flag
frontend/          # React SPA
app.py             # Entry point FastAPI
```

## Comandos locais
```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar localmente (precisa de DATABRICKS_HOST + DATABRICKS_TOKEN)
export DATABRICKS_HOST=fevm-cosin-aws-serverless.cloud.databricks.com
export DATABRICKS_TOKEN=<token>
uvicorn app:app --reload --port 8000

# Build frontend
cd frontend && npm install && npm run build
```

## Deploy
```yaml
# app.yaml
command: ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
env:
  DATABRICKS_APP_ENV: production
```

## Nota de segurança
O token `APP_DATABRICKS_TOKEN` no `app.yaml` atual está em texto plano — considerar mover para Databricks Secrets.
