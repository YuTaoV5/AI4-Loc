#!/bin/bash
set -euo pipefail
base=/opt/kernel-insight
manage_ollama=0
if [[ -f "$base/supervisord.conf" ]] && grep -q '^\[program:kernel-ollama\]' "$base/supervisord.conf"; then manage_ollama=1; fi
"$base/runtime/venv/bin/pip" install --disable-pip-version-check supervisor
release=$(realpath -- "$1")
[[ "$release" =~ ^/opt/kernel-insight/releases/[a-f0-9]{12}$ ]] || exit 1
[[ -f "$release/package-lock.json" && -f "$release/server/index.js" ]] || exit 1
export PATH="$base/runtime:/usr/bin:/bin:/usr/sbin:/sbin"
install -d -m 755 "$base/data" "$base/runtime/bin"
chown kernel-insight:kernel-insight "$base/data"
chmod -R a+rX "$release"
install -d -m 755 "$base/runtime/npm"
cp -a /root/.nvm/versions/node/v24.19.0/lib/node_modules/npm/. "$base/runtime/npm/"
chown -R kernel-insight:kernel-insight "$release"
runuser -u kernel-insight -- env PATH="$PATH" npm_config_cache="$base/data/npm-cache" \
  node "$base/runtime/npm/bin/npm-cli.js" --prefix "$release" ci --omit=dev --ignore-scripts
install -m 755 "$release/runtime-seed/linux/rg" "$base/runtime/bin/rg"
cp "$release"/runtime-seed/linux/{decode_stacktrace.sh,faddr2line,decodecode,extract-vmlinux,checkstack.pl} "$base/runtime/bin/"
chmod 755 "$base/runtime/bin/"*
chmod 755 "$release/scripts/agent-sandbox.sh"
if [[ -e "$base/app" && ! -L "$base/app" ]]; then echo 'Existing app is not a managed symlink; stop.' >&2; exit 1; fi
previous=$(readlink -f "$base/app" 2>/dev/null || true)
ln -sfn "$release" "$base/app"
cat > "$base/supervisord.conf" <<'CONF'
[unix_http_server]
file=/opt/kernel-insight/supervisor.sock
chmod=0600
[supervisord]
logfile=/opt/kernel-insight/data/supervisor.log
pidfile=/opt/kernel-insight/data/supervisor.pid
childlogdir=/opt/kernel-insight/data
[rpcinterface:supervisor]
supervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface
[supervisorctl]
serverurl=unix:///opt/kernel-insight/supervisor.sock
[program:kernel-insight]
command=/opt/kernel-insight/runtime/node /opt/kernel-insight/app/server/index.js
directory=/opt/kernel-insight/app
user=kernel-insight
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stdout_logfile=/opt/kernel-insight/data/web.stdout.log
stderr_logfile=/opt/kernel-insight/data/web.stderr.log
environment=KERNEL_SOURCE_TRANSPORT="curl",PLANTUML_JAVA="/usr/bin/java",PLANTUML_JAR="/opt/kernel-insight/runtime/plantuml.jar",PORT="8787",KERNEL_INSIGHT_DATA_DIR="/opt/kernel-insight/data",KERNEL_AGENT_MODE="dsh",KERNEL_AGENT_MODEL="qwen3.8:27b-kernel-8k",KERNEL_AGENT_BASE_URL="http://127.0.0.1:11435/v1",KERNEL_AGENT_PYTHON="/opt/kernel-insight/runtime/venv/bin/python",KERNEL_AGENT_SANDBOX="/opt/kernel-insight/app/scripts/agent-sandbox.sh",KERNEL_AGENT_CONCURRENCY="1",KERNEL_AGENT_TIMEOUT_SECONDS="420",KERNEL_ROUTER_BASE_URL="http://127.0.0.1:30000/v1",KERNEL_ROUTER_MODEL="Qwen3.8-27B-SystemOne",PATH="/opt/kernel-insight/runtime/bin:/opt/kernel-insight/runtime:/usr/bin:/bin"
[program:ollama-compat]
command=/opt/kernel-insight/runtime/venv/bin/python /opt/kernel-insight/app/scripts/ollama-compat.py
user=kernel-insight
autostart=true
autorestart=true
stdout_logfile=/opt/kernel-insight/data/compat.stdout.log
stderr_logfile=/opt/kernel-insight/data/compat.stderr.log
CONF
if [[ "$manage_ollama" == 1 ]]; then
cat >> "$base/supervisord.conf" <<'OLLAMA'
[program:kernel-ollama]
command=/usr/local/bin/ollama serve
directory=/root
user=root
autostart=true
autorestart=true
stdout_logfile=/opt/kernel-insight/data/ollama.stdout.log
stderr_logfile=/opt/kernel-insight/data/ollama.stderr.log
environment=OLLAMA_HOST="127.0.0.1:11434",OLLAMA_KEEP_ALIVE="60m",OLLAMA_FLASH_ATTENTION="1",OLLAMA_KV_CACHE_TYPE="q8_0"
OLLAMA
fi
chmod 600 "$base/supervisord.conf"
"$base/runtime/venv/bin/python" "$release/scripts/manage-supervisor.py" --restart
"$base/runtime/venv/bin/supervisorctl" -c "$base/supervisord.conf" status
curl --fail --silent --retry 8 --retry-connrefused --retry-delay 1 http://127.0.0.1:8787/api/health
"$base/runtime/venv/bin/python" - "$release" "$previous" <<'PY'
import pathlib,re,shutil,sys
base=pathlib.Path('/opt/kernel-insight/releases').resolve()
keep={pathlib.Path(p).resolve() for p in sys.argv[1:] if p}
for p in base.iterdir():
 if p.is_dir() and not p.is_symlink() and re.fullmatch('[a-f0-9]{12}',p.name) and p.resolve().parent==base and p.resolve() not in keep:
  shutil.rmtree(p)
print('\nKept current and previous source releases; persistent data unchanged')
PY
