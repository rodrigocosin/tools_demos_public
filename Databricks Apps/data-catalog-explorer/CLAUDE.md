# Data Catalog Explorer v2 (versão antiga)

Versão anterior/simplificada do Data Catalog Explorer. Node.js + Express básico sem proxy para API Databricks.

> **Atenção:** Esta é a versão antiga, movida de `~/data-catalog-explorer/`. A versão atual e completa está em `../data-catalog-explorer/`.

## Stack
- **Backend:** Node.js + Express (`server.js`)
- **Frontend:** React + Vite (em `frontend/`)

## Diferença para v1
Esta versão não implementa proxy para a API do Databricks — apenas serve o frontend estático. A versão em `data-catalog-explorer/` tem integração completa com autenticação e proxy.

## Comandos
```bash
npm install
cd frontend && npm install && npm run build
node server.js
```
