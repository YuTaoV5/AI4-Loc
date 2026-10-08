#!/usr/bin/env bash
# Portable full Agent entry point. Existing /opt deployment remains supported.
set -euo pipefail
project=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
if [[ "$(id -u)" == 0 ]]; then echo 'Run as a dedicated non-root user.' >&2; exit 1; fi
export KERNEL_AGENT_RUNTIME="${KERNEL_AGENT_RUNTIME:-$project/data/linux-runtime}"
export KERNEL_INSIGHT_DATA_DIR="${KERNEL_INSIGHT_DATA_DIR:-$project/data/linux-local}"
export KERNEL_AGENT_PYTHON="$KERNEL_AGENT_RUNTIME/venv/bin/python"
export KERNEL_AGENT_SANDBOX="$project/scripts/agent-sandbox.sh"
export KERNEL_AGENT_MODE=dsh
export KERNEL_AGENT_ENGINE="${KERNEL_AGENT_ENGINE:-closed-loop}"
export KERNEL_AGENT_TRANSPORT="${KERNEL_AGENT_TRANSPORT:-ollama-native}"
: "${KERNEL_AGENT_MODEL:?Set the exact installed model name}"
: "${KERNEL_AGENT_BASE_URL:?Set the reachable model API URL}"
export KERNEL_AGENT_MODEL KERNEL_AGENT_BASE_URL
export PORT="${PORT:-8787}"
export PLANTUML_JAVA="${PLANTUML_JAVA:-/usr/bin/java}"
export PLANTUML_JAR="${PLANTUML_JAR:-/usr/share/plantuml/plantuml.jar}"
export PATH="$KERNEL_AGENT_RUNTIME/bin:$PATH"
if [[ -z "${KERNEL_BENCHMARK_DIR:-}" && -f "$project/data/datasets/openharmony-lkdtm-lab-v2/manifest.json" ]]; then
  export KERNEL_BENCHMARK_DIR="$project/data/datasets/openharmony-lkdtm-lab-v2"
fi
mkdir -p -- "$KERNEL_INSIGHT_DATA_DIR"
python3 "$project/scripts/deployment-doctor.py" --full --check-model
# Verify that the host permits the namespace primitive, without disabling isolation.
bwrap --unshare-user --unshare-pid --ro-bind / / --ro-bind /proc /proc --dev /dev -- /bin/true
cd -- "$project"
exec node server/index.js
