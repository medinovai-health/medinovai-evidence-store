#!/usr/bin/env bash
set -euo pipefail

E_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$E_ROOT"

mos_python="python3"
if [[ ! -d .venv ]]; then
  "$mos_python" -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
pip install -q -r requirements.txt

echo "INIT_SUCCESS: venv ready at $E_ROOT/.venv"

if [[ "${MOS_COMPOSE_UP:-0}" == "1" ]]; then
  docker compose up -d
  echo "Temporal UI (default): http://localhost:8088"
fi

python -c "from src.api.app import app; print('FastAPI app import OK')"
echo "Smoke: run API with: uvicorn src.api.app:app --host 0.0.0.0 --port 8000"
echo "Worker:  python -m src.worker"
