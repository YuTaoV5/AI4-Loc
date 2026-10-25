#!/bin/bash
# Fresh host or restored /opt/kernel-insight. Never embeds a provider credential.
# Root on Ubuntu 24.04 x86_64; input must be a clean Git checkout of the desired commit.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run as root'; exit 1; }
[[ $(uname -m) == x86_64 ]] || { echo 'Inspected runtime is Linux x86_64; other architectures require separate validation'; exit 1; }
source_dir=$(realpath -- "${1:?Usage: install-minimax-harness-server.sh /path/to/git-checkout}")
base=/opt/kernel-insight
commit=$(git -C "$source_dir" rev-parse HEAD)

release="$base/releases/${commit:0:12}"
apt-get update
apt-get install -y git curl ca-certificates xz-utils tar unzip file python3 python3-venv python3-pip python3-cryptography bubblewrap ripgrep binutils llvm gdb
python3 -c 'import sys; assert sys.version_info >= (3,12), "Use Python >=3.12; inspected host uses 3.12.3"'
python3 - <<'PYGUARD'
import json,pathlib
p=pathlib.Path('/opt/kernel-insight/data/state.json')
if p.exists():
 s=json.loads(p.read_text());assert not any(j.get('status') in ('queued','running') for j in s.get('jobs',[])+s.get('agentBenchmarkRuns',[])), 'Defer installation: active jobs';assert not any(x.get('pull',{}).get('status')=='testing' for x in s.get('skills',[])), 'Defer installation: active Skill tests'
PYGUARD
install -d -m 755 "$base" "$base/runtime" "$base/runtime/bin" "$base/releases" "$base/data"
getent passwd kernel-insight >/dev/null || useradd --system --create-home --home-dir "$base/home" --shell /usr/sbin/nologin kernel-insight
if [[ ! -x "$base/runtime/node" ]]; then
 node_version=v24.19.0
 download_dir=$(mktemp -d "$base/runtime/node-download.XXXXXX")
 curl --fail --retry 3 -o "$download_dir/node.tar.xz" "https://nodejs.org/dist/$node_version/node-$node_version-linux-x64.tar.xz"
 curl --fail --retry 3 -o "$download_dir/SHASUMS256.txt" "https://nodejs.org/dist/$node_version/SHASUMS256.txt"
 expected=$(awk -v filename="node-$node_version-linux-x64.tar.xz" '$2 == filename {print $1}' "$download_dir/SHASUMS256.txt")
 [[ ${#expected} == 64 ]] || { echo 'Missing official Node checksum'; exit 1; }
 printf '%s  %s\n' "$expected" "$download_dir/node.tar.xz" | sha256sum -c -
 tar -xJf "$download_dir/node.tar.xz" -C "$download_dir"
 install -m 755 "$download_dir/node-$node_version-linux-x64/bin/node" "$base/runtime/node"
 cp -a "$download_dir/node-$node_version-linux-x64/lib/node_modules/npm" "$base/runtime/npm"
fi
if [[ ! -x "$base/runtime/venv/bin/python" ]]; then
 python3 -m venv "$base/runtime/venv"
 "$base/runtime/venv/bin/python" -m pip install -r "$source_dir/deployment/minimax-harness/requirements.txt"
fi
"$base/runtime/venv/bin/python" -c 'import deepseek_harness, supervisor, elftools, importlib.metadata as m; assert m.version("deepseek-harness-sdk")=="0.1.5rc1"; assert m.version("deepseek-harness-runtime-bin")=="0.1.5rc1"; assert m.version("supervisor")=="4.3.0"'
[[ $("$base/runtime/node" --version) == v24.19.0 ]] || { echo 'Unexpected existing Node runtime; inspect before replacing'; exit 1; }
chown -R root:root "$base/runtime"
if [[ ! -d "$release" ]]; then
 install -d -m 755 "$release"
 git -C "$source_dir" archive "$commit" | tar -x -C "$release"
fi
[[ -f "$release/server/index.js" && -f "$release/package-lock.json" ]] || exit 1
# Windows checkouts may have CRLF and non-executable shell files.
find "$release/scripts" -name '*.sh' -exec sed -i 's/\r$//' {} +
find "$release/scripts" -name '*.sh' -exec chmod 755 {} +
ln -sfn /usr/bin/rg "$base/runtime/bin/rg"
chown -R kernel-insight:kernel-insight "$release" "$base/data"
runuser -u kernel-insight -- env PATH="$base/runtime:/usr/bin:/bin" npm_config_cache="$base/data/npm-cache" "$base/runtime/node" "$base/runtime/npm/bin/npm-cli.js" --prefix "$release" ci --omit=dev --ignore-scripts
# Existing restored state and config are intentionally preserved.
if [[ -e "$base/app" && ! -L "$base/app" ]]; then echo 'app must be a managed symlink'; exit 1; fi
ln -sfn "$release" "$base/app"
if [[ ! -f "$base/supervisord.conf" ]]; then
 sed '1s/^\xEF\xBB\xBF//' "$release/deployment/minimax-harness/supervisord.conf" > "$base/supervisord.conf"
fi
install -d -m 700 "$base/services/minimax"
if [[ ! -f "$base/services/minimax/credentials.json" ]]; then
 echo 'Missing root-private MiniMax config. Restore the encrypted core archive or create credentials.json using Python getpass; see handover.'
 exit 2
fi
chown root:root "$base/services/minimax" "$base/services/minimax/credentials.json"
chmod 700 "$base/services/minimax"
chmod 600 "$base/services/minimax/credentials.json"
# Verify user namespaces before enabling code-capable Harness workers.
runuser -u kernel-insight -- bwrap --unshare-user --unshare-pid --die-with-parent --ro-bind /usr /usr --ro-bind /bin /bin --ro-bind /lib /lib --ro-bind /lib64 /lib64 --dev /dev --proc /proc /bin/true
"$base/runtime/venv/bin/python" "$release/scripts/manage-supervisor.py" --restart
curl --fail --retry 8 --retry-connrefused --retry-delay 1 http://127.0.0.1:8787/api/health
printf '\nInstalled commit %s at %s\n' "$commit" "$release"
