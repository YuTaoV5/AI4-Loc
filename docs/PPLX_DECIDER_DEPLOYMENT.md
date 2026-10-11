# PPLX-Decider v1：服务器部署、下载与验收手册

2026-10-12 补充：按分时复用完成的全GPU测试单独记录于 [复测入口](../research/pplx-timeshare-20261012/README.md)。下文2026-10-11的CPU卸载部署/验收保持历史条件，不用于全GPU速度比较。

记录日期：2026-10-11。此手册记录实际部署方式及复现命令；本轮验收证据见 [deployment/pplx-decider/validation](../deployment/pplx-decider/validation/)。历史 121 次分类实验保持独立，见 [实测报告](../research/pplx-decider-20261011/REPORT.md)。

最终验收：服务保持运行，PID2638；真实三类型接口和项目客户端均通过，推理后停止/重启及再次推理通过。两处生命周期问题已修复并保留失败记录；部署脚本五个SHA256与提交文件一致。这里的“验证通过”限定为下述已执行项目，不包含网站切换、原生SGLang或重启宿主机恢复。

## 1. 部署对象与范围

真实权重为 `perplexity-ai/pplx-decider-v1-27b`，固定 revision：

```text
b01a5cbaca5391f73bd55103d4f27e8982cd5e60
```

本机原有 SGLang 0.5.21 服务继续在 30000 运行，显存约 60 GiB，单卡 A100 80 GiB 无法再放入约 49 GiB 的完整 BF16 专用模型。因此使用官方模型仓库的 prepare/forward/answer、专用 readout 与保存温度，通过 Transformers + Accelerate CPU 卸载部署到独立 30002 端口。这是实际验证路线；不是原生 SGLang 专用模型部署，也没有把通用模型改个别名冒充专用模型。

本服务支持文本有限决策，供 AI4Loc 的 DecisionClient 调用。没有替换网站生产配置、没有提供 Chat，也没有恢复当前未运行的网站。Windows 原生不执行这里的 Linux/CUDA/进程管理命令；应在 GPU Linux 服务器或具备 CUDA 的 WSL2 中运行。远程 Windows 客户端可通过 SSH 隧道调用。

## 2. 权重与源代码下载地址

| 内容 | 固定来源 |
| --- | --- |
| 模型卡与许可证 | [官方模型仓库](https://huggingface.co/perplexity-ai/pplx-decider-v1-27b) |
| 固定文件列表 | [固定 revision 文件页](https://huggingface.co/perplexity-ai/pplx-decider-v1-27b/tree/b01a5cbaca5391f73bd55103d4f27e8982cd5e60) |
| 官方大小/哈希元数据 | [HF API：固定 revision + blobs](https://huggingface.co/api/models/perplexity-ai/pplx-decider-v1-27b/revision/b01a5cbaca5391f73bd55103d4f27e8982cd5e60?blobs=true) |
| 官方参考入口 | [固定 inference.py](https://huggingface.co/perplexity-ai/pplx-decider-v1-27b/resolve/b01a5cbaca5391f73bd55103d4f27e8982cd5e60/inference.py) |
| 专用决策配置 | [固定 decision_config.json](https://huggingface.co/perplexity-ai/pplx-decider-v1-27b/resolve/b01a5cbaca5391f73bd55103d4f27e8982cd5e60/decision_config.json) |
| 独立读出头 | [固定 readout.safetensors](https://huggingface.co/perplexity-ai/pplx-decider-v1-27b/resolve/b01a5cbaca5391f73bd55103d4f27e8982cd5e60/readout.safetensors) |

任意 backbone 分片使用以下形式，具体名称以官方 metadata 或 safetensors index 为准，不手工猜测：

```text
https://huggingface.co/perplexity-ai/pplx-decider-v1-27b/resolve/b01a5cbaca5391f73bd55103d4f27e8982cd5e60/<文件名>
```

本次共下载并校验 30 个必要文件：11 个 backbone 分片，readout，config/decision_config，tokenizer/processor/chat template，safetensors index，参考推理/服务/类型源文件及许可证等。不能只下载 readout，也不能用通用 Qwen backbone 顶替专用训练后的 backbone。

服务器直接连接 Hugging Face 不可用，实际以 `https://hf-mirror.com` 传输固定 revision，下载器使用 `User-Agent: Mozilla/5.0`。镜像不是身份依据：LFS 文件按独立官方元数据 SHA256 校验，其他文件按 Git blob SHA1 校验。临时签名 URL、认证令牌和 SSH 密码不进入文档或仓库。

## 3. 目录及资源

```text
/root/gpufree-data/systemone/models/PPLX-Decider-v1-27B/  # 可重复下载的权重缓存
/opt/kernel-insight/services/pplx-decider-v1/            # 独立服务
  serve.py / service.py / verify-*.py
  venv/                                                # 独立 Accelerate 安装
  state/                                               # PID、日志、加载/验证结果
/opt/kernel-insight/experiments/pplx-decider-20261011/    # 历史实验；不要覆盖
```

硬件与限制：单卡 A100-SXM4-80GB，驱动 580.126.09；容器 Python 3.12，cgroup 内存上限 120 GiB、CPU quota 12 核，PID 1 为 tini。启动前原有模型显存约 61392 MiB、余量约 19761 MiB，任务队列无 queued/running。部署器要求本 profile 启动前至少 16000 MiB 空闲显存；该阈值不是任意上下文/并发下的显存保证。

权重下载前预留至少 55 GiB，另留环境和工作空间；下载器按尚未下载文件的总大小再加 2 GiB 检查空间。完整权重已缓存后，本服务器缓存盘约余 8.3 GiB；不要在该盘重复解压一套权重。内存使用要区分可回收文件缓存与匿名内存，不能只看宿主机总内存。

## 4. 从 GitHub 安装文件

以下命令在 Linux 执行。已有项目仓库时用其绝对路径设置 `AI4LOC_REPO`，不要覆盖工作树。

```bash
git clone https://github.com/YuTaoV5/AI4-Loc.git
export AI4LOC_REPO="$PWD/AI4-Loc"
export PPLX_HOME=/opt/kernel-insight/services/pplx-decider-v1
export PPLX_MODEL=/root/gpufree-data/systemone/models/PPLX-Decider-v1-27B
mkdir -p "$PPLX_HOME/state" "$PPLX_MODEL"
cp "$AI4LOC_REPO"/deployment/pplx-decider/*.py "$PPLX_HOME/"
cp "$AI4LOC_REPO"/deployment/pplx-decider/official-model-metadata.json "$PPLX_HOME/"
```

确认仓库 commit 与发布记录一致，再部署。下面的 `run-benchmark.py` 不参与服务启动；它的固定实验目录已经有历史数据，不能直接重跑覆盖。

## 5. 下载与完整校验

仓库附带的 metadata 是本次独立从官方 HF API 获取的固定版本公开快照。联网主机也可重新获取以核对：

```bash
curl -fL 'https://huggingface.co/api/models/perplexity-ai/pplx-decider-v1-27b/revision/b01a5cbaca5391f73bd55103d4f27e8982cd5e60?blobs=true' \
  -o "$PPLX_HOME/official-model-metadata.fetched.json"
```

若服务器官方链路不可达，使用仓库内固定快照，或在可联网主机取得 JSON 后用 scp 上传；无需上传签名下载地址。

```bash
python3 "$AI4LOC_REPO/research/pplx-decider-20261011/fetch-checkpoint.py" \
  --metadata "$PPLX_HOME/official-model-metadata.json" \
  --destination "$PPLX_MODEL" \
  --endpoint https://hf-mirror.com --workers 3
```

官方链路可用时，把 endpoint 改为 `https://huggingface.co`。下载器断点续传 `.part`、最多重试 5 次、3 个并行文件；完成后写入 `verified-checkpoint.json`。已有完整文件不会重复下载，但仍重新计算哈希。不要在服务加载/推理同时更新目录。

独立二次验证命令：

```bash
python3 "$PPLX_HOME/verify-checkpoint.py" \
  --checkpoint "$PPLX_MODEL" \
  --metadata "$PPLX_HOME/official-model-metadata.json" \
  --output "$PPLX_HOME/state/checkpoint-verification.json"
```

本轮重新读取并校验全部 30 文件，40.778 秒通过。出现大小或哈希差异必须先修复下载，再启动模型；不能仅检查文件存在。

## 6. 本服务器已验证的依赖安装

已有 `/root/systemone-venv` 中的 Torch/Transformers/CUDA 依赖可用。为避免改变原有模型服务，新建 venv，通过 `.pth` 只复用平台依赖，在新环境安装 Accelerate：

```bash
/root/systemone-venv/bin/python -m venv "$PPLX_HOME/venv"
"$PPLX_HOME/venv/bin/python" - <<'PY'
import pathlib, site
pathlib.Path(site.getsitepackages()[0], 'platform.pth').write_text(
    '/root/systemone-venv/lib/python3.12/site-packages' + chr(10)
)
PY
"$PPLX_HOME/venv/bin/python" -m pip install --no-deps accelerate==1.15.0 \
  -i https://pypi.tuna.tsinghua.edu.cn/simple
"$PPLX_HOME/venv/bin/python" -c \
  'import torch,transformers,accelerate; print(torch.__version__,transformers.__version__,accelerate.__version__)'
```

实际输出：`2.13.0+cu130 5.12.1 1.15.0`。`.pth` 必须有真实换行，不能写成字面量反斜杠 n。该 venv 依赖原平台目录，迁移时不能只复制 venv。

实际附属版本：FastAPI 0.142.2、Uvicorn 0.54.0、safetensors 0.9.0rc1、Pillow 12.3.0、huggingface-hub 1.33.0、tokenizers 0.22.2、Pydantic 2.14.0b2、NumPy 2.3.5。这是环境记录，不表示应把这些预发布包升级进现有生产环境。

全新 GPU 主机先按固定 checkpoint 的 `inference.py` 声明创建独立 Python/CUDA 运行环境，官方入口 `uv run inference.py` 会解析其依赖；此入口通常整模型上 GPU，需要充足空闲显存。新环境尚未在本服务器按“从零安装”验收，不可把现有环境复用结果当成任意 CUDA/包版本的兼容保证。若改用本服务的 CPU 卸载入口，还需 Accelerate，并重新运行本手册的完整接口验证。

## 7. 启动命令与参数

已验证的管理入口：

```bash
"$PPLX_HOME/venv/bin/python" "$PPLX_HOME/service.py" start \
  --checkpoint "$PPLX_MODEL" --port 30002 \
  --gpu-weight-limit 10GiB --cpu-memory-limit 64GiB
"$PPLX_HOME/venv/bin/python" "$PPLX_HOME/service.py" status
```

等价前台命令，可交给平台的 Supervisor/systemd/container entrypoint 托管：

```bash
"$PPLX_HOME/venv/bin/python" "$PPLX_HOME/serve.py" \
  --checkpoint "$PPLX_MODEL" --port 30002 \
  --gpu-weight-limit 10GiB --cpu-memory-limit 64GiB \
  --record "$PPLX_HOME/state/runtime.json"
```

| 参数/固定设置 | 本次值与含义 |
| --- | --- |
| checkpoint | 完整专用模型目录，固定 revision；启动核对完整校验摘要 |
| port / host | 30002 / 127.0.0.1；与原通用模型30000分离 |
| gpu-weight-limit | 10GiB，Accelerate 权重放置额度，**不是 GPU 总占用上限** |
| cpu-memory-limit | 64GiB，CPU 权重放置额度，**不是 cgroup/进程总内存上限** |
| gpu-wait-seconds | 管理器默认60秒等待显存≥16000MiB，处理退出后的CUDA释放延迟；超时拒绝启动，不降低门槛 |
| dtype / attention | BF16 / sdpa；未量化 |
| CPU threads | 8；参考构造逻辑一致 |
| max_length | 官方 prepare 默认每问题8192 token，超限报错，不自动截断 |
| 问题数量 / 并发 | 每请求1–3个；单请求推理锁，忙时529，不设内部等待队列 |
| temperature | 读取 checkpoint 保存值2.207568021892729；不采用Chat采样温度 |
| codes / readout | 官方255个单token codes和独立训练头；不重建为普通A/B提示 |
| 网络下载 | 模型加载时HF_HUB_OFFLINE、TRANSFORMERS_OFFLINE开启 |
| API | GET /health、POST /v1/systemone；无 /v1/chat/completions |

管理器把 stdout/stderr 追加至 `state/server.log`，写 PID/启动时间及 `state/runtime.json`，脱离 SSH 后保持运行。它不负责崩溃自动重启或容器重启后自动恢复；平台重新启动后须执行 start，或按上面的前台命令添加平台托管。不要同时运行两套管理器占用同一端口。

### 完整GPU驻留（分时维护使用）

更新后的 `serve.py` 支持 `--placement full-gpu`；显式把整个backbone与专用readout放在cuda:0，并逐参数断言没有CPU/meta参数。该模式忽略cpu-memory-limit/gpu-weight-limit；这两个额度仅用于默认cpu-offload模式。不能只把额度调大后仍让auto静默卸载。

本轮使用实验目录的冻结入口；恢复后的常驻服务磁盘入口仍为e415d96版本。要使用以下新参数，先按本文上传步骤将仓库新版serve.py复制到目标服务目录；不要给旧版入口传入新参数。

在已释放原GPU模型并确认显存足够的维护窗口，前台命令为：

```bash
"$PPLX_HOME/venv/bin/python" "$PPLX_HOME/serve.py" \
  --checkpoint "$PPLX_MODEL" --placement full-gpu \
  --port 30002 --record "$PPLX_HOME/state/full-gpu-runtime.json"
```

检查runtime中的placement=full-gpu、parameterDevices仅含cuda:0，及health的cpuOffload=false。本轮完整参数52173271520字节（48.59GiB）。需要额外显存放置激活等运行内存，49GiB不是启动总显存要求。当前service.py管理入口仍使用默认CPU卸载配置；完整GPU模式使用上述前台命令或本轮受保护的分时实验控制器，不给管理器传入其不支持的placement参数。

本平台通用模型由Go Supervisor管理、未配置控制RPC，直接结束模型会被自动拉起。此次维护控制器保存原进程身份/配置，短暂暂停Supervisor监控，在独立恢复守护保护下分时测试，再恢复监控让原配置重新启动。SSH/Ollama等子服务继续运行，但监控暂停期间它们的自动重启暂不可用。此流程仅适用于已经核验的当前容器，不能照搬固定PID到其他机器；其他平台优先使用正常的模型服务管理接口。失败启动与恢复记录均单独保留。

## 8. 请求、验证及 Agent 接入

```bash
curl -fsS http://127.0.0.1:30002/health
curl -fsS http://127.0.0.1:30002/v1/systemone \
  -H 'Content-Type: application/json' --data-binary @- <<'JSON'
{"model":"perplexity-ai/pplx-decider-v1-27b","state":"BUG: KASAN: use-after-free in worker","questions":{"family":{"type":"choice","instructions":"Classify the explicit diagnostic.","criteria":{"uaf":"Explicit use-after-free","oom":"Out-of-memory","unknown":"Insufficient evidence"}}}}
JSON
```

返回 `answers.family.choice` 及归一化 `probabilities`，`usage.input_tokens` 为问题批次输入量，`output_tokens=0`。`noul` 返回 true 的概率；`score` 返回有序等级索引的期望值与概率。服务固定一个 checkpoint，model 可省略或为上述真实ID，也接受现有 DecisionClient 默认别名 `jev-latest`；别名不切换模型，响应总是返回真实ID。此适配只支持文本，拒绝 images 和未知字段。

概率来自专用读出及模型保存温度，没有完成独立内核领域校准；高概率不等于根因已确认。

完整验收：

```bash
"$PPLX_HOME/venv/bin/python" "$PPLX_HOME/verify-service.py" \
  --base http://127.0.0.1:30002 \
  --agent-scripts /opt/kernel-insight/app/scripts \
  --output "$PPLX_HOME/state/validation.json"
```

检查真实ID/revision、choice/noul/score、有限概率和为1、输出token为0；缺state、错误模型名、空criteria分别422；Chat路由404；现有 DecisionClient 实际返回 `memory_lifetime` 并保存轨迹。使用合成日志，仅验收部署，不写网站任务、公共榜单，不计入历史121次benchmark。

需要在独立 Agent 进程切换定界端时设置：

```bash
export KERNEL_DECISION_API=systemone
export KERNEL_DECISION_MODEL=perplexity-ai/pplx-decider-v1-27b
```

同时将该进程创建 DecisionClient 时的 base 参数设为 `http://127.0.0.1:30002`。环境变量本身不改变 base；项目中实际由调用者传入。Chat/根因模型仍使用原生成服务。本次仅验证客户端兼容，没有改网站的生产模型配置或宣称完整定位提分。

Windows 访问仅监听 loopback 的服务器接口：

```powershell
ssh -N -p 30113 -L 30002:127.0.0.1:30002 root@120.209.70.195
```

保持该终端连接，再访问本机 `http://127.0.0.1:30002/health`。若本机端口被占用，改为 `-L 30003:127.0.0.1:30002`。通过SSH交互认证，不把密码写入命令。未开放公网端口，当前接口没有独立应用鉴权。

## 9. 停止、重启与问题处理

```bash
"$PPLX_HOME/venv/bin/python" "$PPLX_HOME/service.py" stop
"$PPLX_HOME/venv/bin/python" "$PPLX_HOME/service.py" start
tail -n 80 "$PPLX_HOME/state/server.log"
```

stop 核对记录PID、进程启动tick及serve.py命令，只向本服务发SIGTERM，不做按名称批量kill，不触碰原模型。超时保留现场人工检查；不可直接误杀其他GPU进程。

显式执行停止/重启验收（会短暂停止本 PPLX 服务）：

```bash
"$PPLX_HOME/venv/bin/python" "$PPLX_HOME/verify-lifecycle.py" \
  --output "$PPLX_HOME/state/lifecycle-validation.json"
```

每步退出码、旧/新PID及失败尝试均写入指定 JSON。生命周期验证后，再执行 verify-service.py 验证真实推理；只检查健康端点不足以证明加载后的模型可用。

| 现象 | 处理 |
| --- | --- |
| 官方下载不通、镜像403 | 使用固定revision镜像及下载器UA；仍按官方哈希校验，勿记录临时签名URL |
| 分片缺失/哈希不同 | 重取对应文件，重新verify；不要只凭模型别名启动 |
| import torch/transformers失败 | 检查platform.pth真实换行、Python3.12平台路径；新主机安装独立依赖 |
| CUDA OOM | 检查其他GPU进程、问题长度/批次；10GiB仅权重额度。停止本服务释放资源，重评额度与运行条件 |
| 请求耗时十几秒 | 当前CPU卸载存在权重搬运开销；不是同条件全GPU速度数据 |
| HTTP529 | 已有推理进行中；调用方限并发，记录重试，勿无限并行 |
| HTTP422 | 修正state/questions/criteria/model；超8192token先做可审计证据裁剪 |
| port occupied / PID mismatch | status检查归属，不覆盖端口、不按陈旧PID杀进程 |
| stop后立即start被显存检查拒绝 | 本轮复现过CUDA显存释放延迟，已改为最多等待60秒；超时再检查其他进程，不关闭显存保护 |
| stop时退出过程中的cmdline暂时为空 | 本轮复现并修复：发SIGTERM前严格核对命令与启动tick，发信号后仅等待同一启动tick的原进程退出；不把正常CUDA退出误判为PID被替换 |
| health正常但网站不通 | 模型接口与网站是不同服务；网站8787需按网站部署runbook独立恢复 |

## 10. SGLang 原生路线与结论边界

原生专用模型部署须使用确实包含 `decision_config.json`/专用readout支持的 SGLang 构建；当前平台0.5.21没有该支持，本次没有升级。查阅 [SGLang专用模型说明](https://docs.sglang.io/cookbook/autoregressive/Perplexity/PPLX-Decider-v1-27B) 与 [项目接口说明](SGLANG_JEV_LIKE_DEPLOYMENT.md)，固定验证过的构建commit再部署。不能用通用 `/v1/decisions` 的“无额外开关”规则替代专用权重支持确认。

专用全GPU部署约需49GiB权重空间加运行内存；本机通用模型仍驻留，未验证原生SGLang全GPU性能。历史test两端27/27，无提分证据；本轮服务验收仅证明下载身份、运行及接口兼容，不替代新机制泛化或根因定位实验。
