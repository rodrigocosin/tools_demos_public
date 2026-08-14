#!/bin/bash
set -e

PROFILE="cosin-aws-serverless"
APP_NAME="exames-clinicos"
WORKSPACE_PATH="/Workspace/Users/rodrigo.cosin@databricks.com/exames-clinicos-app"

echo "=== 1. Build frontend ==="
cd "$(dirname "$0")/frontend"
npm run build
cd ..

echo "=== 2. Sync source files ==="
databricks sync . "$WORKSPACE_PATH" \
  --profile "$PROFILE" \
  --exclude node_modules \
  --exclude .venv \
  --exclude __pycache__ \
  --exclude .git

echo "=== 3. Upload frontend/dist (force overwrite) ==="
databricks workspace import-dir \
  frontend/dist \
  "$WORKSPACE_PATH/frontend/dist" \
  --overwrite \
  --profile "$PROFILE"

echo "=== 4. Deploy ==="
databricks apps deploy "$APP_NAME" \
  --source-code-path "$WORKSPACE_PATH" \
  --profile "$PROFILE"

echo "=== Deploy concluido ==="
echo "URL: https://exames-clinicos-7474659847183384.aws.databricksapps.com"
