#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
[[ "$(id -u)" != 0 ]] || { echo 'Run as the non-root service user.' >&2; exit 1; }
runtime="${KERNEL_AGENT_RUNTIME:-$project/data/linux-runtime}"
python3 -m venv "$runtime/venv"
# Closed-loop Agent uses the Python standard library. Legacy dsh is optional.
if [[ "${1:-}" == --with-dsh ]]; then
  "$runtime/venv/bin/pip" install 'deepseek-harness-sdk==0.1.5rc1'
fi
cd -- "$project"
npm ci --omit=dev --ignore-scripts
chmod +x scripts/agent-sandbox.sh scripts/start-linux-site.sh
echo 'Runtime ready. Configure model URL/name and start-linux-site.sh.'
