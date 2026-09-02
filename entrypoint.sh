#!/usr/bin/env bash
# Container entrypoint: wait for Postgres, init schema, optionally seed, serve.
set -euo pipefail

HOST="${POSTGRES_HOST:-localhost}"
PORT="${POSTGRES_PORT:-5432}"

echo "[entrypoint] Waiting for PostgreSQL at ${HOST}:${PORT}..."
python - <<'PY'
import os, socket, time

host = os.getenv("POSTGRES_HOST", "localhost")
port = int(os.getenv("POSTGRES_PORT", "5432"))
for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("[entrypoint] PostgreSQL is reachable.")
            break
    except OSError:
        time.sleep(2)
else:
    raise SystemExit("[entrypoint] PostgreSQL was not reachable in time.")
PY

echo "[entrypoint] Initialising database schema (idempotent)..."
python -c "import asyncio; from database.schema import init_db; asyncio.run(init_db())"

# One-time seed: only if enabled AND the documents table is empty.
if [ "${SEED_ON_STARTUP:-false}" = "true" ]; then
  NEED_SEED="$(python - <<'PY'
import asyncio
from database.repository import count_documents
from database.session import db

async def main() -> None:
    await db.connect()
    try:
        n = await count_documents()
    finally:
        await db.disconnect()
    print("yes" if n == 0 else "no")

asyncio.run(main())
PY
)"
  if [ "${NEED_SEED}" = "yes" ]; then
    echo "[entrypoint] Seeding sample documents from ${SEED_PATH:-data/sample_docs}..."
    python -m database.ingest --path "${SEED_PATH:-data/sample_docs}" \
      || echo "[entrypoint] Seeding failed (is GOOGLE_API_KEY set?); continuing."
  else
    echo "[entrypoint] Documents already present; skipping seed."
  fi
fi

echo "[entrypoint] Launching API on ${API_HOST:-0.0.0.0}:${API_PORT:-8000}..."
exec uvicorn api.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
