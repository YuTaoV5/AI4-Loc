#!/bin/bash
set -euo pipefail
LAB=/root/gpufree-data/kernel-insight-lab
COMMIT=f88704ae607f90518f67aee33790ac06d6ada77d
mkdir -p "$LAB/evidence" "$LAB/build" "$LAB/source"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends qemu-system-x86 busybox-static bison flex libelf-dev libssl-dev bc cpio build-essential
if [ ! -e "$LAB/source/.git" ]; then
 git -C "$LAB/source" init
 git -C "$LAB/source" remote add origin https://gitee.com/openharmony/kernel_linux_5.10.git
fi
git -C "$LAB/source" fetch --depth=1 origin "$COMMIT"
git -C "$LAB/source" checkout --detach "$COMMIT"
test "$(git -C "$LAB/source" rev-parse HEAD)" = "$COMMIT"
cd "$LAB/source"
make O="$LAB/build" x86_64_defconfig
scripts/config --file "$LAB/build/.config" \
 --enable KASAN --enable KASAN_GENERIC --enable KASAN_INLINE \
 --enable DEBUG_KERNEL --enable DEBUG_INFO --enable DEBUG_FS \
 --enable DEBUG_KMEMLEAK --enable DEBUG_KMEMLEAK_AUTO_SCAN \
 --enable PROVE_LOCKING --enable DEBUG_SPINLOCK --enable DEBUG_MUTEXES \
 --enable DEBUG_ATOMIC_SLEEP --enable DEBUG_LIST --enable REFCOUNT_FULL \
 --enable DETECT_HUNG_TASK --enable SOFTLOCKUP_DETECTOR \
 --enable LOCKUP_DETECTOR --enable RCU_STALL_COMMON \
 --enable LKDTM --enable MODULES --enable BLK_DEV_INITRD \
 --enable DEVTMPFS --enable DEVTMPFS_MOUNT \
 --disable WERROR --disable DEBUG_INFO_BTF \
 --set-str SYSTEM_TRUSTED_KEYS '' --set-str SYSTEM_REVOCATION_KEYS ''
make O="$LAB/build" olddefconfig
make O="$LAB/build" -j6 bzImage modules > "$LAB/evidence/build.log" 2>&1
cp "$LAB/build/.config" "$LAB/evidence/kernel.config"
git rev-parse HEAD > "$LAB/evidence/commit.txt"
make -s O="$LAB/build" kernelrelease > "$LAB/evidence/kernelrelease.txt"
sha256sum "$LAB/build/arch/x86/boot/bzImage" "$LAB/build/vmlinux" "$LAB/build/.config" > "$LAB/evidence/build.sha256"
gcc --version > "$LAB/evidence/compiler.txt"
echo KERNEL_BUILD_COMPLETE
