# Kernel Insight 服务器部署与恢复流程

适用日期：2026-10-07。本文总结本项目在 Ubuntu 容器、A100 80GB、已有 Ollama / SGLang 服务环境中的部署和接管经验。它是已有服务器的升级与恢复手册；不是裸机自动安装方案。

## 1. 目录与服务边界

| 路径 / 接口 | 用途 |
| --- | --- |
| `/opt/kernel-insight/releases/<包 SHA256 前 12 位>` | 发布源码及该版本依赖 |
| `/opt/kernel-insight/app` | 指向当前 release 的软链接 |
| `/opt/kernel-insight/runtime` | Node、Python venv、图表和检索工具 |
| `/opt/kernel-insight/data` | 账号、任务、报告、上传材料、源码缓存和服务日志 |
| `/opt/kernel-insight/supervisord.conf` | 项目专属 Supervisor 配置 |
| `/opt/kernel-insight/supervisor.sock` | 项目控制 socket |
| `127.0.0.1:8787` | 网站和 API，使用非 root 账号 kernel-insight |
| `127.0.0.1:11435/v1` | Ollama OpenAI 兼容适配器 |
| `11434` | 已有 Ollama；实际监听范围以现场 ss 输出为准 |
| `127.0.0.1:30000/v1` | 已有 SGLang 分诊模型 |

发布包只包含源码、公开 Benchmark 和已校验的工具种子。账号、会话、SSH 密码、私人日志、符号材料、vmcore、模型权重与内核缓存留在服务器，不进入 Git 或发布包。发布目录与持久化数据分开，回退源码不会回退任务数据。

## 2. 登录后先盘点，不直接重启

本机建立访问隧道，按现场信息替换占位符，密码交互输入：

```bash
ssh -p <SSH_PORT> -L 127.0.0.1:8788:127.0.0.1:8787 root@<SSH_HOST> -N
```

浏览器访问 http://127.0.0.1:8788 。首次初始化会创建默认管理员；账号信息按项目账号管理流程处理，网站保持回环监听。

服务器只读盘点：

```bash
readlink -f /opt/kernel-insight/app
ss -lntp
ps -eo pid,ppid,user,etime,comm
/opt/kernel-insight/runtime/venv/bin/supervisorctl -c /opt/kernel-insight/supervisord.conf pid
/opt/kernel-insight/runtime/venv/bin/supervisorctl -c /opt/kernel-insight/supervisord.conf status
curl --fail --silent http://127.0.0.1:8787/api/health
curl --fail --silent http://127.0.0.1:11435/v1/models
curl --fail --silent http://127.0.0.1:30000/v1/models
df -h / /root/gpufree-data
nvidia-smi
```

通过网站任务列表或已认证 API 确认没有 queued / running 任务，再进入维护。日志和 state 可能包含业务内容，现场查看时按需提取，不把原文件作为公开验收附件。不要输出 /proc/*/environ、凭据目录或完整会话文件。

## 3. 判断“FATAL 但网站正常”

本次现场出现：旧网站进程仍在提供服务，而新 Supervisor 的三个服务均 FATAL。网站 stderr 为 EADDRINUSE，原因是旧进程占据 8787；Ollama 11434 也已有平台实例。

判断顺序：

1. 用 ss 找实际端口持有者。
2. 用 PID、PPID、/proc/<PID>/cmdline 和 /proc/<PID>/cwd 核对进程归属及实际 release。
3. 对照 Supervisor pidfile、控制端返回 PID 和相同配置的所有 supervisord 进程。
4. 对照源码文件时间与进程启动时间。app 已指向新目录，不代表旧 Node 进程已加载新代码。
5. 检查最新任务是否真的生成 evidence.json，不能只靠文件部署成功判断新流程已运行。

关键教训：supervisorctl status 在子服务失败时可能返回非零，不能据此判定 Supervisor 已死，更不能直接删除它的 socket 后再启动一个实例。健康接口成功也不等于监控状态正常；两者都要核对。

## 4. 收敛项目 Supervisor

先备份项目配置，确认没有活跃任务。若配置包含 kernel-ollama，但 11434 的实际进程归平台所有，应先从项目配置移除重复服务定义，保留平台模型进程。

本仓库提供与本次恢复相同的脚本：

```bash
/opt/kernel-insight/runtime/venv/bin/python /opt/kernel-insight/app/scripts/manage-supervisor.py --restart
```

如果该文件尚未在当前 release 中，可把仓库的 scripts/manage-supervisor.py 单独上传到项目运维目录，用其绝对路径运行。

脚本只识别命令行中精确使用 `/opt/kernel-insight/supervisord.conf` 的项目 supervisord；不终止平台 Supervisor 或直接杀模型。它先检查活跃任务：控制端与唯一实例一致时执行 reread / update 并重启网站和兼容适配器；重复实例或控制失联时，对已核对的项目 Supervisor 发 SIGTERM，等待其正常退出，之后才清理 socket 并启动单一实例。超时则停止，不强行重复启动。

配置中的模型归属必须在调用脚本前核对；脚本不会自动替你判断一个 kernel-ollama 定义是否属于平台。如果 state 保留了旧 running 状态而网站已停止，应先调查残留任务与进程，不能为绕过门禁盲改业务状态。

## 5. 发布一个新版本

在包含完整 Agent 实现的工作树执行 `python scripts/package-deployment.py`，得到 source-only 包及 SHA256。打包脚本、deploy-server.sh 和完整应用属于已部署版本的实现；本次经验文档提交没有捎带工作区的其他应用改动。

发布前核对：

- runtime 已存在；实际部署脚本依赖 `/root/.nvm/versions/node/v24.19.0` 中的 npm，请按目标环境检查路径，不能把 Node 最低版本要求误当成脚本路径已可用。
- Python venv 有 Supervisor、dsh SDK 和匹配 runtime；系统有 bubblewrap、rg 及需要的 LLVM 工具。
- 既有模型端点可访问；沿用现有权重，不重新下载或启动重复实例。
- 包内没有账号、私人材料、缓存、node_modules 或凭据；SHA256 与上传后相同。
- 解包拒绝绝对路径、父目录穿越、软链接及硬链接，目标限定在 releases 下。

确认包与哈希后，上传到 incoming，解包到以哈希命名的新目录。使用该版本自带的脚本：

```bash
bash /opt/kernel-insight/releases/<RELEASE>/scripts/deploy-server.sh /opt/kernel-insight/releases/<RELEASE>
```

当前部署流程在新 release 安装依赖、配置非 root 服务、切换 app 链接，通过 manage-supervisor.py 管理项目实例，最后做健康检查。保留当前和上一版本源码，持久化 data 不删除。需要维护停机窗口：切换软链接本身不是应用无中断更新，也不是数据库迁移或自动回滚。

## 6. 发布后验收与回退

至少检查：项目只有一个 Supervisor；网站和兼容适配器均 RUNNING；8787 健康接口的 llmConnected=true；端口持有者及网站进程工作目录属于新 release。

再手动提交一个公开 Benchmark 样本，检查：

- 任务真正结束为 needs_review，而不是只进入 queued / running。
- evidence.json 存在，并含预期 schema、原始行号、工具退出码、截断标记与材料缺口。
- 报告标明待人工确认，rootCauseVerified=false；类别正确不能换算为根因已证明。
- Benchmark 试跑不计入真实业务解决数；失败记录保留，不伪装成成功。

远端模型验证示例，输出存服务器 data：

```bash
runuser -u kernel-insight -- python3 /opt/kernel-insight/app/scripts/run-agent-benchmark.py --limit 1 --output /opt/kernel-insight/data/release-smoke.json
```

验证脚本默认使用首次管理员账号；账号已变更时，通过 BENCHMARK_USERNAME / BENCHMARK_PASSWORD 提供现场凭据，保持凭据仅在当前进程环境中，勿写进脚本、Git、终端记录或公开日志。

回退前再次确认无活跃任务，记录当前和上一版本目标，恢复 app 指向已验证的上一 release，再运行项目维护脚本并重复健康与实跑检查。保留失败版本和错误证据直至调查完毕。源码回退不能代替数据格式兼容性检查。

## 7. 本次具体经验与限制

- dsh 使用独立任务目录和 DSH_HOME；模型失败要显式失败，不能回退成伪造的模型成功。
- bubblewrap 必须只读挂载 /bin，否则 SDK 的 bash/PTY 无法启动；容器不允许新 proc mount 时使用现有 /proc 只读挂载。任务日志与附件另外只读挂载。网络仍用于本机模型 API，不宣称完整网络隔离。
- 模型上下文先用 8K 紧凑证据。曾尝试 16K，与常驻 SGLang 共存时发生 CPU 卸载；按显存和延迟验证后再扩大。
- linux-next 精确历史 commit 文件可能返回 404；记录真实缺口，不能替换为最新源码并声称版本匹配。
- 工具安装、类别分数、Build ID 一致均不能证明根因。无真实匹配 vmcore 时，只能验证转储查询门禁和固定参数。
- OpenHarmony 故障采集仍暂停，构建停在缺少 ccache；未生成 bzImage，不能宣称已启动内核或收集 50 份样本。

已验证结果与运行限制见 [接管记录](SERVER_STATUS_20261007.md)；模型配置及执行链见 [远端 Agent 部署](REMOTE_AGENT_DEPLOYMENT.md)。
