# PPLX 全 GPU 分时复用复测

本轮按用户要求移除 CPU 卸载：先停止通用模型与 PPLX CPU sidecar，PPLX 完整驻留唯一 A100 采集78次；释放后通用模型全GPU采集43次。共121正式调用、2合成预热。最后恢复原服务；结果见 [REPORT.md](REPORT.md) 与 `results/`。

实测test均27/27；PPLX均值5.672s、通用2.563s，PPLX约慢2.21倍。25个映射案例repeat=0均23/25，35个未映射案例不评分。这里测量家族定界，尚未验证完整根因定位效果。

**这是部署方案比较。** 两端相同硬件、BF16、证据与三个问题；通用实验端关闭radix缓存，串行客户端。PPLX采用官方参考Transformers/SDPA，通用采用SGLang0.5.21，运行时/内核/提示/读出仍不同，顺序为PPLX→通用，未做AB/BA。因此解决了CPU卸载的不公平因素，仍不能宣称纯权重速度因果收益或所有运行条件已相同。

## 数据与复算

```bash
python -m pip install -r ../pplx-decider-20261011/requirements-analysis.txt
python analyze.py --public
python verify.py
```

公开121次派生表、概率、协议、阶段设备与服务恢复证明；原始输入/轨迹/日志保留私有归档，不随Git发布。现有test已参与开发；自然日志中的LKDTM符号保留。stage/reporter/根因没有独立真值；35未覆盖案例不评分，LOOP/SOFTLOCKUP的注入标签与第一诊断差异不事后改分。

## 执行与维护

- `benchmark.py prepare`：冻结协议、输入清单、代码哈希及seed=202610120的共享案例/重复顺序；每端9test×3+16train×1，另35例PPLX-only。
- `benchmark.py run --arm pplx|generic`：匿名bwrap、180秒超时、零重试；评分只在父进程，实际模型请求无额外标签字段。
- `serve.py`：本次冻结的运行入口副本；`--placement full-gpu` 显式device_map全GPU，并断言所有参数在cuda:0，防止auto静默卸载。
- `orchestrate.py`：限于本服务器维护，保存原进程环境在服务器700目录中的600私有文件；平台Go Supervisor无RPC，因此暂停其监控、终止明确模型进程组，执行两个阶段，再恢复监控由原配置重新拉起通用模型。其他平台子服务继续运行。独立守护进程在控制器退出或1小时上限时清理自身测试进程并恢复服务。

这些脚本有固定实验路径，**不能覆盖当前目录重复运行**。新实验必须创建新目录、保存当前受管模型PID/启动tick及私有环境、确认空队列/空闲端口、核对Supervisor身份与恢复路径。不要把固定PID或恢复环境快照复制到另一服务器使用。

第一次启动尝试位于服务器相邻 `pplx-timeshare-20261011`：新增记录代码读取不存在的hf_device_map属性导致启动退出，0正式调用；中止后原服务恢复。修复后使用本目录新冻结协议重跑，保留失败现场。

服务器证据：`/opt/kernel-insight/experiments/pplx-timeshare-20261012/`；本地私有归档：`data/local-archive/pplx-timeshare-20261012/`。原进程环境/账号配置不发布，也不混入公开图表。旧CPU卸载数据保持在独立研究目录，不合并为本轮公平对照。

`retain.py` 在服务器完成恢复后生成私有归档，排除进程环境/lease、权重、venv及临时制备副本。本轮624383字节、536证据文件，SHA256 `1e6e699a0bd6fac1b456e71fa51815920300e44f7623151f417a1cc1da6a83b3`；本地核对归档及每个文件哈希。公开数据离线复算与私有数据派生的7个数据文件、Markdown和HTML报告逐字节一致；四组图已目视检查。
