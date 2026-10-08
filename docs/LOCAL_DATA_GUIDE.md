# 本地完整项目数据与恢复指南

项目根目录：`X:\Items\1_AI4-Loc`。本次将服务器项目资产归档到该目录；数据集、实验和私有业务备份均由 `.gitignore` 排除，不随代码上传 GitHub。完整系统方案见 [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md)。

## 数据入口

| 本地路径 | 内容 |
| --- | --- |
| `data/datasets/linux-community-v1/` | 6 例社区日志、来源、修复摘要和原始清单 |
| `data/datasets/openharmony-lkdtm-lab-v1/` | 永久保留的 64 例旧注入集 |
| `data/datasets/openharmony-lkdtm-lab-v2/` | 当前网站 80 例集合，包含新增 16 例启动/配置故障 |
| `data/datasets/stability-v1/` | 新材料合同集：68 场景、60 ready、8 excluded，含匹配源码和编译产物 |
| `data/experiments/kernel-lab/bootstages/` | 启动阶段脚本、场景、运行日志、清单、配置变体及编译产物 |
| `data/experiments/kernel-lab/benchmark/` | 旧 67 场景采集记录、网站格式副本及历轮定位评测 |
| `data/experiments/kernel-lab/iterations/` | 配对迭代及调用轨迹归档 |
| `data/experiments/kernel-lab/evidence/`、`scenarios/`、`dataset-audit/` | 原始构建证据、注入源码与标注审计 |
| `data/server-snapshots/20261007-full/` | 完整 Linux 恢复归档、库存与本地校验结果 |
| `data/source-repositories/openharmony-kernel-6.6/` | 原根目录内核下载的 Git 历史；原工作树未展开，保留历史而不伪称匹配故障源码 |
| `data/dataset-audit/` | 本次之前已有的实验成绩、失败、自检及轨迹副本，继续保留 |
| `data/local-archive/operations/` | 历史 SSH 运维脚本和临时操作辅助文件，不属于网站运行依赖 |

`data/benchmark/` 保持仓库原来的 6 例公开社区夹具，不用 80 例覆盖它；固定测试使用 `tests/fixtures/community-v1/`。本地网站如需显示服务器的 80 例，使用独立数据目录：

```powershell
$env:KERNEL_BENCHMARK_DIR = (Resolve-Path data/datasets/openharmony-lkdtm-lab-v2).Path
npm start
```

这只切换网站案例集合，不会自动配置真实模型。默认本地引擎仍是确定性分诊；完整模型配置及 Linux 运行边界见系统方案。

## 恢复包与校验

库存记录时间：2026-10-07 11:01:34 UTC（19:01:34 北京时间），对应服务器 release `f4648fac616c`。归档捕获的是该时刻数据，不表示以后服务器变动会自动同步。

| 归档 | 精确字节数 | 保存范围 |
| --- | ---: | --- |
| `lab.tar.gz` | 3,721,238,020 | 161,248 个常规文件，逻辑数据约 11.43 GB：全部实验目录、数据版本、源码、构建、启动阶段、运行日志、旧备份与失败证据 |
| `service.tar.gz` | 973,132,060 | 134,328 个常规文件，逻辑数据约 3.04 GB：网站持久数据、任务、账号、诊断材料、模型调用轨迹、运行时及 Supervisor/源码注册表配置 |
| `release.tar.gz` | 1,618,275 | 当前线上发布代码与 80 例网站集合，保留 Linux 文件属性 |

精确 SHA256 以 `inventory.json` 为准；下载后 `verification.json` 记录三个归档的校验与四个数据集的验证结果。私有备份包含密码哈希、任务和用户材料，已获用户明确授权，仅存本地；不要把整个数据目录提交 Git 或用于共享附件。

省略项：外部 Ollama/SGLang 模型权重及平台服务、npm 缓存与 node_modules、图表/JVM 缓存、PID/socket、历史 release 重复副本、传入部署包、此前 project-export 归档及 Python 字节码。它们分别属于外部依赖、可再生缓存或重复数据；全部共享构建产物、源码和实验失败记录仍保留。

Linux 归档保留源码中的大小写、符号链接、硬链接、可执行位、源码 Git 历史及构建树；Windows 展开数据集和实验常规文件。冗余的 `shared/source-tree` 留在归档，冻结完整源码位于 `shared/source.tar.gz`；实验视图的重复大产物硬链接与构建符号链接也保留在原包，记录于 `extractions.json`，不重复生成大量副本。不要在 Windows 将整个服务归档覆盖解压到项目根目录；恢复时先在独立 Linux 暂存目录解压检查，再按系统方案设置路径、权限和运行时。

账号和 state 文件在捕获前后哈希一致，实时日志可能有不同截点；这是文件级恢复备份，不是数据库事务快照。运行时中的 Linux 二进制与 venv 不能直接当作 Windows 依赖执行。

本地复核：

```powershell
python scripts/sync-project-data.py --host 120.209.70.195 --port 30113 --snapshot 20261007-full --local-only
python tools/kernel-lab/kernel-dataset.py validate data/datasets/stability-v1
```

重新传输同一快照使用相同 ID，支持分段续传，密码只在交互中输入，不落盘：

```powershell
python scripts/sync-project-data.py --host 120.209.70.195 --port 30113 --snapshot 20261007-full --include-private
```

本轮校验通过后会清理服务器临时传输包；本地仍保留完整恢复包。服务器临时包清理后，同 ID 仅用 `--local-only` 复核；重新采集需选择新的 snapshot ID，程序禁止把不同快照写入同一 ID。需要新时点备份时也选择新的 snapshot ID。程序拒绝未知主机、无效快照名、下载哈希错误、缺失数据以及覆盖既有数据集；后续新数据版本需使用新目录，不要改写已封版样本。

## 质量和使用边界

- `stability-v1` 的 60 个有效样本配有日志、匹配源码与产物；校验覆盖 423 个文件，其他保存文件属于补充来源和历史。
- 旧 64 例和新 80 例为包含关系；新增 16 例全部 train，原 21 例 test 未扩充。启动故障中存在 console 未就绪、挂起及相同签名，不能按 80 个独立根因计算。
- 旧集与 stability-v1 共用 59 个有效场景但日志重新采集，不能混算成绩。
- 启动配置变体有不同 bzImage 和源码补丁，不能直接使用 stability-v1 的 Build ID 或标签。归档中的 `lab/source` 是最新工作树；分析 stability-v1 时使用其冻结 `shared/source.tar.gz`，不要用后续工作树替代。
- 社区 6 例没有逐例完整编译产物；完整备份不会凭空补全这些材料。
- vmcore、引入提交真值、独立机制审核及修复重跑仍不完整，不能把文件校验成功解释为因果闭环成功。

## 项目整理记录

详见 [project-cleanup-20261007.json](project-cleanup-20261007.json)。已删除无有效 HEAD/refs 的失败下载目录 `tools/-lip-`（381,937,492 字节）、可由 `tools/kernel-debug/smoke.py` 重建的合成压力日志（108,000,055 字节）及六字节 `test.txt`，合计 489,937,553 字节。

原根目录 `kernel_linux_6.6` 的完整 Git 历史移入 `data/source-repositories/`，未删除；历史运维脚本移入本地 archive。保留现有演示稿、最终预览、Kelip 模板、工具依赖、公开测试夹具、历史失败与真实评测轨迹。未清理服务器的原始数据，也未启动或重部署网站。

后续清理原则：有原始证据和用户创作的文件先保留；有生成入口的缓存可再生；只有所有归档及数据校验成功后，才清理本次传输分片。归档本身是完整恢复入口，不作为“重复大文件”删除。

本轮整理验证：Node 36/36、Python 38/38（含新增 9 项备份安全测试）、隔离网站业务 15/15 通过。既有真实模型成绩未重跑或改写。

最终归档、展开清单与验收摘要见 [project-data-inventory-20261007.json](project-data-inventory-20261007.json)。
