# L40新服务器：决策数据与微调skill验收

执行日期2026-10-18，验收区间北京时间15:39:34–15:39:35，Python3.12.3，NVIDIA L40，驱动报告46068MiB容量。结果见[summary.json](summary.json)、[前后资源快照](resource-observations.json)与[验收程序](verify_server.py)。

**CPU合同与协议验收通过11项；未执行9B GPU训练、真实模型推理或SGLang部署。** GPU上已有外部计算任务，前后均占用9868MiB，独立初查至归档期间仍在运行；观测利用率35%–95%。空闲显存不代表计算资源空闲。用户要求不影响其他进程，因此没有启动CUDA工作。

## 做了哪些实际操作

仅创建`/root/gpufree-data/ai4loc-skill-validation-20261018/`，上传两份skill、原冻结训练器与模型元数据，以及此验收程序；没有上传密码、业务数据或模型权重。使用系统Python标准库，`nice -n 19`低优先级，子进程`CUDA_VISIBLE_DEVICES=''`，CPU库线程上限1。不向全局或现有环境安装软件。

首次验收发现全新目录不存在`data/`时校验程序创建子目录失败；修复为`mkdir(parents=True,exist_ok=True)`，另存acceptance-02重跑成功。acceptance-01与02均保留，不覆盖首轮记录。初次问题属于校验工具的目录初始化，不是模型推理错误。

| 检查 | 结果 |
|---|---|
| 三集合合成格式样本 | 接受，明确仅为格式示例 |
| circular被误标RCU | 拒绝 |
| 同机制跨split | 拒绝 |
| 规范化输入重复 | 拒绝 |
| 注入元数据混入输入 | 拒绝 |
| 公开清单包含原日志 | 校验排除 |
| 默认训练计划 | 无模型下载、无模型加载、无GPU训练 |
| CE与CE+RLCD生成worker | 两者语法编译通过、代码SHA不同，不导入Torch |
| 合成数据加execute | 在模型导入前拒绝执行 |
| API探针 | 本地HTTP桩的两次协议请求通过 |
| 正式评估器协议 | 假tokenizer+本地HTTP桩六次请求计数通过，标签不加入请求 |

8次HTTP均为本地协议桩，不是模型响应；11项通过也不表示训练数值正确或真实SGLang兼容已在L40验证。原A100真实训练记录仍由[9B研究](../jev-qwen35-9b-20261016/README.md)提供，不以此桩测试代替。

验收前后3个既有Python进程启动tick与进程名一致；发给外部进程的信号为0。没有停止、挂起或重启其他进程；没有更改其他任务环境或配置；没有新模型端口。快照不能证明其他任务吞吐逐位不变，但本轮没有新增GPU竞争负载。

## 复现这个不占GPU的验收

在包含skills和冻结训练器的完整项目副本上，选择全新结果目录：

```bash
nice -n 19 python3 research/decision-skills-l40-20261018/verify_server.py \
  --root "$PWD" --output /data/ai4loc-checks/acceptance-new
```

验收程序仅查询`nvidia-smi`，运行标准库合同/协议测试，保存前后快照与源文件SHA。完整进程身份快照保留在私有归档，不把其他项目的命令行、环境或数据收进公开文件。

## 完整GPU验收尚需的条件

当前服务器没有旧项目的`/root/systemone-venv`、Qwen权重或SGLang服务，系统Python也无Torch/Transformers。需要在GPU空闲或另有空闲卡时，按[微调skill复现步骤](../../skills/ai4loc-decision-finetune/references/reproduce.md)创建独立环境、下载校验固定基座、输入真实审核数据，再训练和启动独立端口验收。

不得照搬旧A100的静态显存比例：旧9B服务resident约47.5GiB，大于此卡驱动报告的约44.99GiB容量；训练峰值18.74GiB也不能当作服务显存。L40须按实际上下文与状态池重新配置。PPLX v1 BF16权重48.59GiB本身已大于此卡可见容量，不能原样全GPU装载。

目前没有留下自动排队或等待GPU空闲就自行启动的作业。完整GPU验证状态为**待空闲资源**，不是已通过，也不是训练失败。私有归档摘要见[private-archive.json](private-archive.json)。
