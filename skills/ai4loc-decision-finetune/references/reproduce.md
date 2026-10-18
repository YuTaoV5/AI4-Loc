# Qwen3.5-9B决策微调：完整复现指导

## 1. 准备代码、环境和GPU

需要完整AI4Loc仓库及本skill。使用Linux CUDA环境；Windows可准备/检查数据和生成计划，GPU训练建议在已有服务器环境执行。历史验证环境为A100-SXM4-80GB、Python3.12+、Torch2.13.0+cu130、Transformers5.12.1；推理为SGLang0.5.21。不要直接升级正在工作的生产环境。

历史服务器已验证解释器：`/root/systemone-venv/bin/python`。新机器先创建独立venv，按组织镜像或官方轮子安装上述Torch/CUDA组合及Transformers、Accelerate、Safetensors、HuggingFace Hub；随后保存`pip freeze`、`nvidia-smi`、驱动/CUDA信息。精确旧轮子不可取得时应记录新环境并另开复现记录，不能冒称逐位复现。

```bash
python3.12 -m venv .venv-decision
source .venv-decision/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cu130
python -m pip install transformers==5.12.1 accelerate==1.15.0 safetensors huggingface-hub
python -m pip install flash-linear-attention==0.5.2 fla-core==0.5.2
python -m pip check
python -c "import torch,transformers; print(torch.__version__,transformers.__version__); print(torch.cuda.is_available())"
nvidia-smi
```

Torch2.13.0+cu130的Linux CPython3.12轮子已于2026-10-18在[PyTorch官方cu130索引](https://download.pytorch.org/whl/cu130/torch/)核对；安装仍需匹配主机驱动。保存`python -m pip freeze > requirements-resolved.txt`以冻结实际解析环境。

历史9B LoRA训练torch allocated峰值18.74GiB，但它不是最低显卡容量；还要计驱动、workspace与激活等。历史服务按静态池0.55配置NVML resident约47.5GiB，说明推理预分配与训练峰值不是同一量。沿用A10080GB最便于对照；其他GPU需先按实际上下文/并发实测预算。PPLX v1 BF16权重本身48.59GiB，另需工作区，不能当作轻量模型装入小显存。

## 2. 下载并校验固定基座

模型：`Qwen/Qwen3.5-9B`，revision：`c202236235762e1c871ad0ccb60c8ee5ba337b9a`。

```bash
python research/jev-qwen35-9b-20261016/fetch-checkpoint.py \
  --metadata research/jev-qwen35-9b-20261016/official-model-metadata.json \
  --destination /data/models/Qwen3.5-9B \
  --endpoint https://huggingface.co
```

脚本核验15个文件、4个权重分片；`verified-checkpoint.json`保留每文件大小与摘要。首次下载约18GB，另为合并模型留至少22GiB可用空间及适配器/日志空间。可用授权镜像传输，但模型身份仍以固定官方元数据校验。

## 3. 准备审核数据

使用数据skill的JSONL合同，审核首诊断证据及标签，先做机制分组，再冻结split。不要直接把旧弱标注数据当作新人工真值；旧分数可用原目录离线分析复算，方法训练应使用审核后的新版本。

```bash
python skills/ai4loc-decision-data/scripts/prepare_dataset.py \
  --input /data/annotations/reviewed.jsonl \
  --output /data/runs/decision-new-001
```

检查validation的类支持、组隔离、重复和synthetic标记。不要将private文件提交Git。

## 4. 生成计划，再执行训练

```bash
python skills/ai4loc-decision-finetune/scripts/train.py \
  --project-root "$PWD" --run-dir /data/runs/decision-new-001 \
  --base /data/models/Qwen3.5-9B --output /data/models/AI4Loc-Qwen9B-new-001
```

默认只生成计划。实际GPU训练，在相同命令末尾加`--execute`。确保资源可用；本脚本不停止任何生产服务。长任务可用tmux或受控作业队列，日志在run/training.log。

方法：冻结BF16骨干和原LM字母读出，48处rank8/alpha16 LoRA，FP32适配器与AdamW。每例每轮4次候选构造，5/8/12选项且训练gold在集合内，位置随机；上下文2048token，状态最多3000字符。第一轮CE，后两轮CE+RLCD。每4微步累计更新，3轮；学习率1e-4、weight_decay0.01、clip1。新数据N条train对应12N微步、3N次更新。

RLCD接收`logits,target,sigma`：4次中心化高斯扰动产生z，内部softmax成q；用真标签计算log+spherical奖励与标准化优势，停止reward/adv梯度；loss为CE减优势加权logdensity项。σ依次0.4、0.15，部署温度T另设。HTTP概率不携带跨接口的autograd图。

训练保存每步loss/耗时/显存、每轮dev、adapter-epoch*.pt、selected/merged-dev、温度、合并模型与manifest。推荐另准备相同审核数据的独立run，使用`--objective ce`做同更新预算基线。比较测试前固定模型选择规则。

## 5. 模型选择、合并和保留

参考训练器按dev NLL选epoch并导出合并BF16模型；温度网格在dev上选，但部署先以T=1为基线，独立验证后再采用校准温度。dev应足够覆盖各类。test只在固定方案后评估，模型分数与概率分布、输入token、候选排列和错误均保留。

需要从已保存适配器单独重建合并模型时：

```bash
cd research/jev-qwen35-9b-20261016
python merge-adapter.py --base /data/models/Qwen3.5-9B \
  --adapter /data/runs/decision-new-001/adapter-epoch1.pt \
  --output /data/models/rebuilt-new-001
```

`epoch1`只是文件名示例，应读取新run的training-complete.json选择实际best_epoch。数值和库差异可能使合并字节不同；保存当前manifest，不许将旧哈希套给新权重。

## 6. SGLang隔离启动

在独立推理环境安装并核对历史兼容SGLang版本，不把推理依赖升级混入训练环境：

```bash
deactivate
python3.12 -m venv .venv-sglang
source .venv-sglang/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cu130
python -m pip install 'sglang[all]==0.5.21'
python -m pip check
python -m pip freeze > requirements-sglang-resolved.txt
```

若包解析器提出不兼容依赖，应停止并核对现有服务器的冻结环境，不默默替换实验版本。示例启动与已测9B参数一致；端口未占用且显存充足时执行：

```bash
python -m sglang.launch_server \
  --model-path /data/models/AI4Loc-Qwen9B-new-001 \
  --served-model-name AI4Loc-Qwen9B --host 127.0.0.1 --port 30003 \
  --dtype bfloat16 --context-length 8192 --mem-fraction-static 0.55 \
  --max-running-requests 4 --mamba-full-memory-ratio 0.6 --max-mamba-cache-size 32 \
  --enable-metrics --enable-request-time-stats-logging
```

8k用于固定有限接口性能；完整源码Agent需按真实prompt长度配置，本项目独立闭环使用32768。状态池和实际max_running_requests要从启动日志与metrics确认，不只读CLI。

## 7. API验收与评估

```bash
python skills/ai4loc-decision-finetune/scripts/probe.py \
  --base-url http://127.0.0.1:30003 --model AI4Loc-Qwen9B \
  --output /data/runs/decision-new-001/api-probe.json
```

probe使用明确的合成use-after-free例子，检查Decision有限概率与Chat首个非空内容；记录真实请求时间，不计入benchmark。正式准确率可运行本skill的`evaluate.py`：

```bash
python skills/ai4loc-decision-finetune/scripts/evaluate.py \
  --run-dir /data/runs/decision-new-001 --tokenizer /data/models/Qwen3.5-9B \
  --base-url http://127.0.0.1:30003 --model AI4Loc-Qwen9B \
  --output /data/runs/decision-new-001/eval-fixed-test
```

每例3种固定排列，分别统计Decision和Chat多数票，失败保留；native Decision返回的prompt token ID与本地Chat模板逐项核对。该串行准确率评估不是随机化并发速度实验；不将标签/评分发送模型。不要直接复制历史accuracy.py的绝对路径覆盖旧研究。

需要原项目224trial矩阵的离线重算，使用`research/jev-qwen35-9b-20261016/analyze.py`及字段文档；若重新采集，采用新目录和维护窗口，按原orchestrator确认生产恢复，不把本skill当无条件停止服务的授权。

## 8. 交付与复现范围

公开：脚本、训练计划（移除敏感路径）、固定revision、公开元数据、标量结果、图表、哈希。私有：原始日志、完整prompt、账号信息、权重/适配器按组织要求留存。历史adapter私有归档不公开，因此逐位重建旧权重需要原adapter；新审核数据训练是方法复现，不能声称等于原权重。


## 9. 共享L40的新机验收记录

2026-10-18的新L40已有外部GPU任务。仅以低优先级系统Python完成11项CPU合同、两目标worker语法与本地HTTP桩检查，没有安装全局包、启动CUDA或模型端口；不表示9B真实训练/推理已在L40验收。完整记录在项目`research/decision-skills-l40-20261018/README.md`。该卡可见46068MiB，不能原样照搬旧resident约47.5GiB的A100服务配置，须待空闲后重新预算静态池、上下文与状态槽。
