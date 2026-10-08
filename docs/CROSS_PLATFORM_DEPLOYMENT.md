# Windows / Linux 全功能部署与文件审计

核对日期：2026-10-07。本文件区分现有实测状态、补充的部署入口和仍需部署验收的能力。不能将能打开网站等同于模型定位、符号化、内存转储分析和故障采集全部可用。

2026-10-09 状态更新：原服务器现已运行 release `163bdd0af0ec`，一键 Agent 跑分与个人 Prompt 功能已部署；同代码专用私有实例完成九例真实模型验收，Node 42/42、Python 53/53 回归通过。详见 [最新平台验收](AGENT_BENCHMARK_PLATFORM.md) 和 [详细分析](AGENT_BENCHMARK_ANALYSIS_20261009.md)。下文“尚未同步远端”“Supervisor 拒绝连接”及旧测试计数描述的是 10 月 7 日核查快照，不代表当前服务器状态；全新 Linux/WSL2 安装仍未新增验收。

## 当前结论

| 方式 | 网站业务 | 真实模型工具 Agent | Linux 沙箱、crash / QEMU 实验 |
| --- | --- | --- | --- |
| Windows 原生 Demo | 已启动，已有归档报告 | 默认关闭 | 不支持原生等价执行 |
| Windows + WSL2 Linux | 新增统一部署入口，待本机安装验收 | 与 Linux 使用同一代码和配置 | 在 Linux 内执行，要求用户命名空间可用 |
| Linux 原服务器 | 整改前 51 个网站/Agent 必要代码文件与本地一致；本轮修改尚未部署远端 | 原有完整执行链 | 已有相关工具 |
| 全新 Linux x86_64 | 新增依赖安装、运行时初始化、启动和依赖预检脚本 | 需配置真实模型服务 | 需安装系统依赖并通过沙箱启动检查 |

本机 `wsl --list --quiet` 当前提示尚未安装 WSL，因此尚未在这台 Windows 上实跑 Linux 全功能。未宣称全新安装已验收。原远端核查时项目 Supervisor socket 拒绝连接；代码一致不表示该服务此刻运行正常。本次没有擅自重启远端平台或模型服务。

## 本地与远端是否完整对应

通过 SSH 只读核对当前 `/opt/kernel-insight/app`，实际 release 为 `f4648fac616c`。对 server、public、scripts、tools/kernel-debug 以及 package 两个文件计算 SHA256，整改前 51/51 与本地一致；整改后再次核对为 49 个一致、2 个有意修改（打包程序和可移植沙箱）、缺失 0。本轮新部署入口尚未同步远端。远端登录 PATH 上没有 node，但旧服务使用 `/opt/kernel-insight/runtime/node`，不能据此判定服务器未安装 Node。

恢复归档中的 165 个文件，整改后 78 个原位置一致，81 个网站数据文件在 `data/datasets/openharmony-lkdtm-lab-v2/` 中一致，6 个有意不同（README、handover、根 benchmark manifest 和本轮修改的 3 个部署/实验脚本）；缺失 0。根 `data/benchmark/` 保持 6 例社区夹具，因此部署 80 例必须显式选择数据集目录。

Linux 的源码树、链接、文件权限及私有服务状态另外保留在 `data/server-snapshots/20261007-full/` 三个归档中。它们不是在 Windows 上直接可运行的环境。外部模型权重、Ollama/SGLang 服务本身不包含在备份；完整部署必须另行提供。源码/产物材料不全的样本仍不能凭部署补全。

## 16G 的组成与保留要求

首次扫描得到逻辑文件大小 16,819,467,268 字节，即 16.82 GB / 15.66 GiB；整改后含测试临时文件约 16.822 GB。不等同于 NTFS 实际分配空间，扫描跳过 reparse points。细目见 `deployment-audit-20261007.json`。

| 目录 | GB（十进制，约） | 用途 / 日常部署是否必需 |
| --- | ---: | --- |
| data/experiments | 5.052 | 实验、构建、中间产物和历史定位轨迹；在线服务不必全部携带，完整研究复现需保留 |
| data/server-snapshots | 4.696 | Linux 全量恢复与私有业务备份；在线不加载，恢复需保留 |
| data/source-repositories | 2.775 | 额外 6.6 内核 Git 历史；不是严格数据集的匹配源码，非默认部署必需 |
| data/kernels | 1.494 | 已下载内核源码缓存；可重建，离线源码功能需要它或等价材料 |
| data/datasets | 1.253 | 四个数据版本，严格集含约 1.017 GB vmlinux；完整评测和材料能力应带上 |
| data/toolchains | 0.955 | Windows LLVM、搜索工具及下载包；Linux 应安装自身工具，不能直接复用 Windows 二进制 |
| data/diagram-runtime | 0.223 | Windows Java/PlantUML，图表功能需要对应平台运行时 |
| node_modules | 0.190 | 可由 lockfile 重装；在线运行需要安装后的依赖 |

因此不都是运行必需文件，也不能把全部大文件直接删掉。建议保留目前完整目录作为研究与恢复主副本，部署时输出精简代码包，按能力复制数据集/源码，私有业务数据单独受控恢复。未删除原始日志、编译产物、历史记录或备份。

## 全新 Linux x86_64（Ubuntu / Debian）

先将项目放在 Linux 文件系统中，例如 `/srv/ai4loc`，并由专用非 root 用户拥有。下列安装会修改系统包，必须由管理员显式执行；启动网站不需要 root。

```bash
cd /srv/ai4loc
sudo bash scripts/install-linux-deps.sh
# 若发行版自带 Node 小于 20，先安装受支持的 Node >=20，再继续。
bash scripts/setup-linux-runtime.sh
# 仅需要旧 dsh 引擎时：bash scripts/setup-linux-runtime.sh --with-dsh

export KERNEL_AGENT_MODEL='<模型 API 中实际安装的精确名称>'
export KERNEL_AGENT_BASE_URL='http://127.0.0.1:11434'
export KERNEL_AGENT_TRANSPORT=ollama-native
export KERNEL_BENCHMARK_DIR=/srv/ai4loc/data/datasets/openharmony-lkdtm-lab-v2
bash scripts/start-linux-site.sh
```

默认开启 closed-loop Agent，使用 Python 标准库和实际模型工具调用，不需要旧 dsh SDK。OpenAI 兼容模型端点需将 transport 设为 `openai`，base URL 包含 `/v1`；密钥通过进程环境 `KERNEL_AGENT_API_KEY` 提供，不写入仓库。可选独立语义路由器用 `KERNEL_ROUTER_BASE_URL`、`KERNEL_ROUTER_MODEL` 配置；没有它不代表已提供相同的外部路由模型能力。

脚本启动前检查工具、材料目录、图表运行时和实际模型列表，并执行 bubblewrap namespace 探测；失败直接退出，不回退到演示模式。模型列表可达仍不证明推理质量，首次部署还须单独执行业务自检和真实模型评测。工具存在也不证明特定 vmcore 与其版本兼容；仍遵守 Build ID / 架构核验。

网站监听回环 8787；Linux 远程访问使用 SSH 隧道。进程常驻可使用 `deployment/ai4loc.service` 用户服务模板：默认项目 `$HOME/ai4loc`，环境文件 `$HOME/.config/ai4loc.env`，从 `deployment/ai4loc.env.example` 复制并填实际模型配置。将 unit 复制到 `~/.config/systemd/user/` 后执行 `systemctl --user daemon-reload` 和 `systemctl --user enable --now ai4loc`。项目放在其他位置时修改 unit 中两个绝对入口，需开机无登录启动时由管理员配置该用户 linger。WSL 要先启用 systemd，或使用前台启动方式。不能复用旧服务器硬编码的监督配置。已有 `/opt/kernel-insight` 升级仍参阅 DEPLOYMENT_RUNBOOK.md；原 `deploy-server.sh` 是既有服务器维护入口，不是通用安装器。

## Windows 全能力：WSL2

管理员先安装 WSL2 和 Ubuntu，并完成 Linux 普通用户初始化（可能需要系统重启）。不要将 Linux 运行时放在 Windows NTFS 中；Linux 工作副本放到 WSL 的 `/home/<user>/ai4loc` 或 `/srv/ai4loc`，保留大小写、链接和执行权限。用部署代码包复制代码，分别复制四个数据集；如需完整实验恢复，在 Linux 内恢复原始归档，不能只依赖 Windows 展开的视图。

在 WSL 中按上节安装依赖与初始化，然后 Windows 入口为：

```powershell
.\scripts\start-windows-site.ps1 -Mode Full -Distribution Ubuntu `
  -LinuxProject /home/<user>/ai4loc -Model '<实际模型名>' `
  -ModelBaseUrl 'http://127.0.0.1:11434' -Port 8787
```

模型若运行在 Windows 主机或远端，使用从 WSL **实际可达**的地址；WSL 内 127.0.0.1 不应未经验证当成 Windows 模型服务地址。Windows Demo 与 WSL Full 不要同时占用同一端口。Windows 原生演示仍可 `-Mode Demo` 启动，且明确标示它没有开启真实 Agent。

## 完整实验与数据恢复

在线分析使用用户提交的日志、源码和产物；缺失材料时输出能力边界。严格 benchmark 使用 `data/datasets/stability-v1` 及其冻结的 source.tar.gz/vmlinux，不能替换成额外 6.6 Git 树。新部署后重新生成符合本机绝对路径的可信源码注册表，禁止直接复用旧 `/root/...` 注册表。不要为让路径匹配而取消哈希或 Build ID 校验。

```bash
python3 tools/kernel-lab/kernel-dataset.py validate data/datasets/stability-v1
# 新建实验场地，不覆盖封版样本；只在独立 QEMU guest 注入故障。
export KERNEL_LAB_DIR="$HOME/ai4loc-lab"
bash tools/kernel-lab/prepare.sh
```

prepare 只准备 pinned 内核，完整历史补丁、外部注入模块、启动变体及构建证据需从 lab 归档按 LOCAL_DATA_GUIDE.md 恢复；仅运行 prepare 不能声称重建了所有历史场景。QEMU TCG 不依赖 KVM，但有 CPU、内存和磁盘开销。新实验保留失败与排除记录，不把修复摘要/真值提供给 Agent。完整恢复归档含私有账号与用户日志，仅在受控 Linux 暂存目录解包检查并配置权限，不能发布 GitHub。

## 打包与验收

`python scripts/package-deployment.py` 生成 `data/deployment/site.tar.gz`：包含网站、Agent、内核实验工具、公开夹具及部署文档；shell 脚本归一化为 LF 并保留可执行位。它不打包 16G、账号、会话、私有日志或模型权重。模型服务与大型数据分开交付是部署依赖，不代表代码包单独具备全部数据。

验收分三层：`deployment-doctor.py --full --check-model` 依赖与可达性、既有 `website-selfcheck.js` 业务闭环、既有 `run-localization-benchmark.py` 真实模型定位指标。新机完成这三层后才称该部署通过全功能验收；当前补充入口没有冒充已在空白 Linux/WSL 中跑完这些验收。

本轮代码验证：Python 回归 40/40、Node 隔离业务回归 36/36；五个部署/实验 shell 文件通过 Bash 语法检查，Windows 入口通过 PowerShell 语法解析；新增打包测试确认内核采集工具和部署入口齐全、所有 shell 为 LF/可执行、没有账号与私有备份。代码包约 2.47 MB，安装后的依赖和选配数据另计。没有新增模型推理成绩，没有执行故障注入，没有把 Windows Demo 的报告回放当作本机 Agent 新推理。
