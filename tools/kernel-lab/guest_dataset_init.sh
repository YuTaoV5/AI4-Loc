#!/bin/busybox sh
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
/bin/busybox --install -s /bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /sys/kernel/debug
mount -t debugfs debugfs /sys/kernel/debug
mount -t tmpfs tmpfs /tmp
echo '8 4 1 7' > /proc/sys/kernel/printk
SCN=baseline
ACT=
for x in $(cat /proc/cmdline); do
 case "$x" in ki.scn=*) SCN="${x#ki.scn=}";; ki.act=*) ACT="${x#ki.act=}";; esac
done
echo KI_RUNTIME_NOTES_BEGIN
base64 /sys/kernel/notes
echo KI_RUNTIME_NOTES_END
echo KI_RUNTIME_RELEASE="$(uname -r)"
echo '===== KI_SCENARIO_BEGIN' "$SCN" '====='
if [ "$SCN" = baseline ]; then
 sleep 3
 echo KI_BASELINE_DONE
else
 [ -w /proc/sys/kernel/watchdog_thresh ] && echo 5 > /proc/sys/kernel/watchdog_thresh
 [ -w /proc/sys/kernel/hung_task_timeout_secs ] && echo 12 > /proc/sys/kernel/hung_task_timeout_secs
 [ -w /proc/sys/kernel/hung_task_warnings ] && echo 10 > /proc/sys/kernel/hung_task_warnings
 [ -w /sys/module/rcupdate/parameters/rcu_cpu_stall_timeout ] && echo 8 > /sys/module/rcupdate/parameters/rcu_cpu_stall_timeout
 [ -w /proc/sys/kernel/panic_on_warn ] && echo 1 > /proc/sys/kernel/panic_on_warn
 [ -w /proc/sys/kernel/softlockup_panic ] && echo 1 > /proc/sys/kernel/softlockup_panic
 [ -w /proc/sys/kernel/hardlockup_panic ] && echo 1 > /proc/sys/kernel/hardlockup_panic
 [ -w /proc/sys/kernel/hung_task_panic ] && echo 1 > /proc/sys/kernel/hung_task_panic
 case "$SCN" in
  lkdtm_*) echo "${SCN#lkdtm_}" > /sys/kernel/debug/provoke-crash/DIRECT || echo KI_TRIGGER_FAILED; sleep 35;;
  leak_*)
   insmod /ki_bench.ko || echo KI_MODULE_FAILED
   echo clear > /sys/kernel/debug/kmemleak
   echo "$ACT" > /sys/kernel/debug/ki_bench/trigger || echo KI_TRIGGER_FAILED
   # kmemleak ignores newly allocated objects for a minimum age; wait before scanning.
   sleep 7
   echo scan > /sys/kernel/debug/kmemleak
   sleep 3
   echo scan > /sys/kernel/debug/kmemleak
   sleep 3
   cat /sys/kernel/debug/kmemleak;;
  corrupt_*)
   insmod /ki_bench.ko || echo KI_MODULE_FAILED
   echo "$ACT" > /sys/kernel/debug/ki_bench/trigger || echo KI_TRIGGER_FAILED
   sleep 3;;
  lock_*)
   insmod /ki_bench.ko || echo KI_MODULE_FAILED
   echo "lock:$ACT" > /sys/kernel/debug/ki_bench/trigger || echo KI_TRIGGER_FAILED
   sleep 25;;
  pressure_oom)
   echo 2 > /proc/sys/vm/panic_on_oom
   /pressure
   echo KI_PRESSURE_RETURNED;;
  *) echo KI_UNKNOWN_SCENARIO;;
 esac
fi
echo '===== KI_SCENARIO_END' "$SCN" '====='
sleep 1
poweroff -f
