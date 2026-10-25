#!/bin/bash
# Existing /opt/kernel-insight server: invoked by the container bootstrap hook.
set -euo pipefail
base=/opt/kernel-insight
ctl="$base/runtime/venv/bin/supervisorctl"
if "$ctl" -c "$base/supervisord.conf" pid >/dev/null 2>&1; then
  exit 0
fi
exec "$base/runtime/venv/bin/supervisord" -n -c "$base/supervisord.conf"
