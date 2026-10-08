#!/usr/bin/env bash
# Ubuntu/Debian dependencies; explicitly invoked by an administrator.
set -euo pipefail
[[ "$(id -u)" == 0 ]] || { echo 'Run this dependency installer with sudo.' >&2; exit 1; }
apt-get update
apt-get install -y python3 python3-venv python3-pip nodejs npm git curl ripgrep \
  bubblewrap llvm binutils gdb crash strace default-jre-headless plantuml graphviz \
  qemu-system-x86 build-essential flex bison bc libssl-dev libelf-dev cpio xz-utils busybox-static rsync
node -e 'if(Number(process.versions.node.split(".")[0])<20)throw Error("Install Node.js >=20 before continuing")'
echo 'Dependencies installed. Run setup-linux-runtime.sh as the service user next.'
