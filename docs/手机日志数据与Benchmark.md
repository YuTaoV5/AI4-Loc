# 手机全阶段日志与独立验收

本套件扩展 AI4-Loc 的手机日志输入范围，不将手机阶段硬编码进通用定位引擎。日志解析、关联及真实报告格式仍由用户 Skill 定义。网页入口为社区 Benchmark 中的“手机全阶段日志”，也可访问 `/phone-benchmark.html`。

## 三种数据的用途

- **真实手机语料**：ABRLog 的发布方提取日志块，来自同一设备/同一次 bugreport 的文件保持在一个包内。用于上传、解压、多文件检索、跨阶段线索与 Skill 调用测试；没有人工根因标签，不计算根因准确率。当前采集文件 `ABRLog_Dataset.zip` 约 145 MB，展开约 1.14 GiB。它是 bugreport 提取块，不是早期启动链全覆盖承诺，也不是原始 RawData 完整导出。
- **合成全阶段套件**：8 例明确标注 synthetic 的最小受控案例。覆盖正常启动、BL2 DDR 训练失败、BL31 非安全入口交接失败、UEFI AVB 验签失败、kernel UFS I/O 超时引起 Android 存储等待、Android zygote 重启，以及加密/早期日志缺失时的证据不足。不是从真机抓取，没有模拟完整硬件，也没有故障注入复现；日志较短，分数仅用于集成验收。
- **真机故障复现**：尚待具备目标手机、UART/厂商抓取能力及可控复现条件后采集。不能用合成日志分数代替真机效果。

xloader / BL2 / BL31 / UEFI / kernel / Android 在本套件中是示例平台阶段；不同芯片应使用各自阶段映射。早期致命失败截断后续阶段，不能伪造该次启动的 Android 成功日志。真实时间关联还需考虑 boot ID、复位次数及各阶段计时基准。

## 准备与使用

```bash
python3 scripts/prepare-phone-benchmark.py /opt/kernel-insight/data/phone-benchmark/synthetic
python3 scripts/collect-phone-logs.py /opt/kernel-insight/data/phone-benchmark/abrlog
python3 scripts/prepare-phone-real-samples.py /opt/kernel-insight/data/phone-benchmark/abrlog
```

采集器从发布方 API 获取文件大小、校验和及下载地址，核对完整校验和后才展开，拒绝越界路径和链接，限制展开总量。`provenance.json` 保存来源、原包 SHA256 和逐文件路径。真实日志按设备和采集批次重新压缩，不修改日志正文，不把不同手机拼接成一例。

网站可下载合成包和真实采集包。将包上传到新建分析，选 **DeepSeek Harness · Skill 自主定位**、自己的已合入 Skill 和 Prompt；仍可用个人组合。手机测试入口与既有内核源码定位榜单分开，不改变旧套件分母。

## 可量化的合成场景评分

模型输出 JSON：`stage / component / mechanism / evidence[{file,quote}] / nextAction`。阶段 20、组件 20、机制 20、原文证据 30、下一步动作 10，满分 100。三个类别字段和动作按限定词表核对；证据必须指向真实输入文件、包含金标准关键片段，且引用全文确实存在于日志，不接受模型编造的引文。失败、超时和非结构化报告按 0 计，固定八例为分母。

`synthetic/private/gold.json` 留在可信控制器；ZIP 不含答案，匿名工作区仅挂载该例输入及所选 Skill。控制器等待沙箱模型退出后才读取金标准。模型知道通用输出词表，但不知道每例答案。这是公开受控案例练习集，不是盲测。

可信管理员运行真实 Harness 评测的 control.json：

```json
{
  "dataset": "/opt/kernel-insight/data/phone-benchmark/synthetic",
  "output": "/opt/kernel-insight/data/phone-benchmark/runs/RUN_ID",
  "skills": [],
  "prompt": "按实际证据定位，不要推测缺失阶段。"
}
```

加载现有网站服务的模型/网关/沙箱环境，使用服务账号运行：

```bash
node scripts/run-phone-benchmark.js /absolute/path/control.json
```

只能在 Linux Harness 沙箱下运行；没有沙箱就拒绝，不回退裸机。设置 `KERNEL_HARNESS_TIMEOUT_SECONDS=240`、`KERNEL_HARNESS_MAX_TOKENS=4096` 可控制每例预算。`skills` 可填个人组合冻结快照；含已发布压缩包时同时提供 `sourceData` 指向原数据目录，用于校验并复制封存包。不得直接把未审查包标成已发布。

运行输出包括逐例模型报告、预测和独立评分结果。`phone-benchmark/latest.json` 仅由可信管理员指向已选择的验收运行，格式为 `{"id":"RUN_ID"}`；网站展示该运行汇总，不提供自动刷榜。不要把私人组合的报告当作公共验收发布。`runs/` 与原始语料均在 Git 忽略目录；仓库只提交脱敏验收摘要。

来源：[ABRLog 官方记录](https://zenodo.org/records/21892365)、[AOSP bugreport 说明](https://source.android.com/docs/core/tests/debug/read-bug-reports)、[TF-A 示例平台启动链](https://trustedfirmware-a.readthedocs.io/en/latest/plat/qti/rb3gen2.html)。


## 2026-10-26 部署与验收

当前 release：`/opt/kernel-insight/releases/phone-benchmark-20261025`。用户重启后确认网站与 MiniMax 网关均自动运行；重新建立本机 `127.0.0.1:8788` 的 SSH 隧道。

已校验下载 ABRLog 提取块，原包 MD5 `8c33844d6f4855448acc36104fc84e90`，展开 1,221,599,973 字节、1,012 文件，重新打包为 15 款手机的 45 个采集包。未重新编造或拼接日志。来源原包和采集清单保存在 `data/phone-benchmark/abrlog`。

八例合成套件通过真实 MiniMax-M2.7 + Harness 执行，8/8 有效报告、受控分数 100/100；这组最小日志已显式提供异常信号，不能据此推导真实根因能力或长日志性能。真实 HUAWEI L29 包另做检索验收：20 个展开文件（含来源清单）、6,490,306 字节，约 101 秒生成报告；报告中 Android release 属性与原文件逐字一致。该包缺少有效 kernel 内容，报告说明了证据限制。真实语料没有金标准，故未计入准确率。

Node 58/58、Python 69/69 回归通过。详细去除私有路径的记录见 [验收 JSON](phone-log-acceptance-20261026.json)。尚未执行目标真机故障注入或 UART 全启动链采集。
