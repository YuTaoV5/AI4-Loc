#!/bin/bash
set -euo pipefail
workspace=$(realpath -- "$1")
[[ "$workspace" =~ ^/opt/kernel-insight/data/agent-runs/[a-f0-9-]{36}$ ]] || { echo 'Invalid agent workspace' >&2; exit 1; }
runtime=/opt/kernel-insight/runtime
runner=$(realpath -- "$3")
[[ "$runner" == /opt/kernel-insight/releases/*/scripts/agent-runner.py || "$runner" == /opt/kernel-insight/app/scripts/agent-runner.py ]] || { echo 'Invalid runner' >&2; exit 1; }
[[ "$2" == "$runtime/venv/bin/python" && "$4" == "$workspace/request.json" ]] || exit 1
readonly_mounts=(--ro-bind "$workspace/input.log" "$workspace/input.log")
if [[ -d "$workspace/artifacts" ]]; then readonly_mounts+=(--ro-bind "$workspace/artifacts" "$workspace/artifacts" --ro-bind "$workspace/artifacts.json" "$workspace/artifacts.json"); fi
exec bwrap --unshare-user --unshare-pid --die-with-parent --new-session \
  --ro-bind /usr /usr --ro-bind /bin /bin --ro-bind /lib /lib --ro-bind /lib64 /lib64 \
  --ro-bind /etc /etc --ro-bind "$runtime" "$runtime" \
  --ro-bind "$(dirname "$runner")" "$(dirname "$runner")" \
  --bind "$workspace" "$workspace" "${readonly_mounts[@]}" --ro-bind /proc /proc --dev /dev --tmpfs /tmp \
  --chdir "$workspace" -- "$2" "$runner" "$4"
