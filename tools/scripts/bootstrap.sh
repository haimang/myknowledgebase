#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install --upgrade pip
python3 -m pip install fastapi uvicorn pytest ruff httpx
python3 -m pip install -e packages/common
python3 -m pip install -e packages/contracts
python3 -m pip install -e packages/config
python3 -m pip install -e packages/storage_sqlite
python3 -m pip install -e packages/vector_sqlite_vec
python3 -m pip install -e packages/workflow_core
python3 -m pip install -e packages/storage_objects
python3 -m pip install -e packages/auth
python3 -m pip install -e packages/team
python3 -m pip install -e packages/ingestion
python3 -m pip install -e packages/browser_runtime
python3 -m pip install -e packages/cleaners_universal
python3 -m pip install -e packages/providers_dedicated
python3 -m pip install -e packages/workflow_clean
python3 -m pip install -e packages/rag_structurizer
python3 -m pip install -e packages/rag_constructor
python3 -m pip install -e packages/rag_vectorizer
python3 -m pip install -e packages/workflow_rag
python3 -m pip install -e packages/management
python3 -m pip install -e apps/api
python3 -m pip install -e apps/worker
python3 -m pip install -e apps/cli

echo "bootstrap done"
