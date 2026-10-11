# Kernel 定位工具与实验

采集与实验：2026-10-06 至 2026-10-07。工具只保存在忽略的 `data/toolchains` 和服务器专属 runtime，不把二进制提交 Git。

| 能力 | Windows | Ubuntu Linux | 验证 |
| --- | --- | --- | --- |
| 大日志、源码检索 | ripgrep 15.2.0 | ripgrep 15.2.0 | 108,000,055 字节合成日志，定位第 1,500,001 行；Windows 另检索真实 Linux 6.6 源码 |
| ELF / DWARF / 反汇编 | llvm-mingw 20260922 | LLVM / Clang 18.1.3 | 编译 x86_64、ARM64 ELF，读取符号、反汇编、映射 fixture.c 行号 |
| Windows 符号 | LLVM COFF / PDB | 无需 | 编译 COFF、生成 PDB、读取公开符号；不执行测试 EXE |
| 独立符号验证 | LLVM | binutils / GDB | Linux 对同一 ELF 读取符号和反汇编 |
| 内核转储 | 离线 ELF 检索 | crash、drgn 0.2.0、pyelftools 0.33 | crash 可启动、drgn 可导入；**没有真实 vmcore，不能宣称转储定位已验证** |
| 系统调用 | 无需 | strace | 可启动；现场 ptrace 和压测追踪需要目标机器授权与权限 |

Windows 13 项、Linux 14 项实验记录见 [Windows JSON](windows-tool-experiments.json) 与 [Linux JSON](linux-tool-experiments.json)。这些是工具可用性实验，不是内核根因准确率测试。

## 复现

Windows 使用 Python 3.12+：

```powershell
python scripts/setup-toolkit.py
python tools/kernel-debug/smoke.py --bin data/toolchains/windows/llvm-mingw-20260922-ucrt-x86_64/bin --rg data/toolchains/windows/ripgrep-15.2.0-x86_64-pc-windows-msvc/rg.exe --source-root data/kernels/release-6.6/linux-6.6
```

安装器固定版本和 SHA256，解压前校验。LLVM 的 DLL 和资源目录是依赖，不能只留下 exe。

Ubuntu 24.04：

```bash
sudo apt-get install ripgrep llvm clang binutils gdb crash strace python3-venv python3-dev libelf-dev libdw-dev
python3 -m venv data/toolchains/venv
data/toolchains/venv/bin/pip install drgn==0.2.0 pyelftools==0.33
data/toolchains/venv/bin/python tools/kernel-debug/smoke.py
```

远端已安装上述 Linux 工具，额外下载了 v6.6 的 `decode_stacktrace.sh`、`faddr2line`、`decodecode`、`extract-vmlinux`、`checkstack.pl`。现场使用须从**目标精确 revision** 获取对应脚本；v6.6 只是安装样本。工具保留上游许可证，不将第三方脚本冒称项目原创 Skill。

## 方法与来源

可供后台 agent 阅读的经验方法位于 [diagnostic-methods.md](../tools/kernel-debug/diagnostic-methods.md)：有界检索、版本确认、符号化、对象生命周期、锁/RCU 等分诊。它是项目诊断指导，不是已经完成临床式验证的自动根因证明。

- [Linux 社区 bug hunting](https://docs.kernel.org/admin-guide/bug-hunting.html)：定位日志、符号、精确版本与复现条件。
- [ripgrep 上游](https://github.com/BurntSushi/ripgrep)：日志和大型代码树搜索。
- [LLVM objdump](https://llvm.org/docs/CommandGuide/llvm-objdump.html)、[symbolizer](https://llvm.org/docs/CommandGuide/llvm-symbolizer.html)、[llvm-mingw 发布](https://github.com/mstorsjo/llvm-mingw/releases/tag/20260922)：多架构 ELF 与 Windows 符号工具。
- [drgn](https://github.com/osandov/drgn)、[crash](https://github.com/crash-utility/crash)：匹配 vmlinux / 调试信息后的内核对象与转储检查。
- [Brendan Gregg 的 Linux crisis tools 博客](https://www.brendangregg.com/blog/2024-03-24/linux-crisis-tools.html)：现场工具准备与可观测性。perf/ftrace/bpftrace 因目标内核和权限要求，本轮只收录为条件候选；Coccinelle 尚未安装或验证。

没有调试信息时不能把反汇编地址猜成源码行；没有 vmcore 时不能把 drgn 安装成功算成转储分析成功。源码拉取失败会记录 URL/revision 错误，不自动替换成其他内核版本。
