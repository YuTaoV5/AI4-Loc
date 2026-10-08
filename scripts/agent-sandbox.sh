#!/bin/bash
set -euo pipefail
workspace=$(realpath -- "$1")
data=$(realpath -- "${KERNEL_INSIGHT_DATA_DIR:-/opt/kernel-insight/data}")
[[ "$(dirname -- "$workspace")" == "$data/agent-runs" && "$(basename -- "$workspace")" =~ ^[a-f0-9-]{36}$ ]] || { echo 'Invalid agent workspace' >&2; exit 1; }
runtime=$(realpath -- "${KERNEL_AGENT_RUNTIME:-/opt/kernel-insight/runtime}")
runner=$(realpath -- "$3")
expected_runner=$(realpath -- "$(dirname -- "$0")/agent-runner.py")
[[ "$runner" == "$expected_runner" ]] || { echo 'Invalid runner' >&2; exit 1; }
[[ "$2" == "$runtime/venv/bin/python" && "$4" == "$workspace/request.json" ]] || exit 1
readonly_mounts=(--ro-bind "$workspace/input.log" "$workspace/input.log")
plugins="$(dirname "$(dirname "$runner")")/plugins"
if [[ -d "$plugins" ]]; then readonly_mounts+=(--ro-bind "$plugins" "$plugins"); fi
if [[ -d "$workspace/artifacts" ]]; then readonly_mounts+=(--ro-bind "$workspace/artifacts" "$workspace/artifacts" --ro-bind "$workspace/artifacts.json" "$workspace/artifacts.json"); fi
exec bwrap --unshare-user --unshare-pid --die-with-parent --new-session \
  --ro-bind /usr /usr --ro-bind /bin /bin --ro-bind /lib /lib --ro-bind /lib64 /lib64 \
  --ro-bind /etc /etc --ro-bind "$runtime" "$runtime" \
  --ro-bind "$(dirname "$runner")" "$(dirname "$runner")" \
  --bind "$workspace" "$workspace" "${readonly_mounts[@]}" --ro-bind /proc /proc --dev /dev --tmpfs /tmp \
  --chdir "$workspace" -- "$2" "$runner" "$4"
