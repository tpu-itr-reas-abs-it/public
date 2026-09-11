#!/usr/bin/env bash
# api | worker | migrate | seed | shell
set -euo pipefail

wait_for_postgres() {
  echo "Ожидание PostgreSQL на ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
  python - <<'PY'
import os, socket, sys, time

host = os.getenv("POSTGRES_HOST", "db")
port = int(os.getenv("POSTGRES_PORT", "5432"))
deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            sys.exit(0)
    except OSError:
        time.sleep(1)
print(f"PostgreSQL {host}:{port} недоступен", file=sys.stderr)
sys.exit(1)
PY
}

case "${1:-api}" in
  api)
    wait_for_postgres
    alembic upgrade head
    exec gunicorn app.main:app \
      --worker-class uvicorn.workers.UvicornWorker \
      --workers "${WEB_CONCURRENCY:-4}" \
      --bind 0.0.0.0:8000 \
      --timeout 60 \
      --graceful-timeout 30 \
      --access-logfile - \
      --error-logfile -
    ;;
  dev)
    wait_for_postgres
    alembic upgrade head
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ;;
  worker)
    wait_for_postgres
    exec arq app.tasks.worker.WorkerSettings
    ;;
  migrate)
    wait_for_postgres
    exec alembic upgrade head
    ;;
  seed)
    wait_for_postgres
    exec python -m app.db.seed
    ;;
  *)
    exec "$@"
    ;;
esac
