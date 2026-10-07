# OpenHarmony 5.10 isolated fault laboratory

Repository: https://gitee.com/openharmony/kernel_linux_5.10.git

Pinned commit: `f88704ae607f90518f67aee33790ac06d6ada77d` (Gitee master, verified with `git ls-remote`).

This laboratory collects **real serial logs from deliberate fault injection**. They are not production incidents or newly discovered OpenHarmony vulnerabilities. Never insert its test modules into the server kernel. Only the QEMU guest may execute faults. Do not reboot or replace the host kernel.

## Evidence requirements

1. Build the pinned source; preserve configuration, compiler version, build log and SHA256 of bzImage/vmlinux.
2. Boot a clean guest and retain a complete baseline serial log before injecting faults.
3. Start a fresh, networkless guest for each case. The guest has no host filesystem sharing, disks, GPU or device passthrough. Enforce process timeout and bounded RAM/CPU.
4. Preserve original serial bytes, per-case SHA256, trigger source and line range, command, kernel identity, expected diagnostic, observed diagnostic, exit reason and root-cause annotation.
5. A planned or merely timed-out test is not a collected fault. Count a case only after the expected diagnostic is present and evidence has been reviewed. Keep failures and unsupported cases in the run report.
6. Do not count repeated copies of one crash as different root causes. Report family coverage separately from the number of fault variants.
7. Keep labels and fault-trigger source out of the diagnostic agent's input. Supply only raw log and permitted kernel source; evaluate against the sealed annotations afterwards.
8. Split training/test cases by mechanism family, not random log lines. Add healthy baseline negatives. Never silently replace the existing community benchmark or its skill-merge baseline.

## Limits

The server is a container without `/dev/kvm`; use QEMU TCG. This reproduces software faults on an x86_64 build of the requested tree. It does not establish coverage of ARM board drivers, real hardware ECC faults, physical watchdogs, or every stability failure. A watchdog or deadlock must produce its corresponding real kernel diagnostic to qualify.

Server artifacts live under `/root/gpufree-data/kernel-insight-lab`, separate from the website, model weights and host kernel. Large build products are not committed to Git.
