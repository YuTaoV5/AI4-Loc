# 网站恢复、自动自检与定位迭代（2026-10-07）

网站已恢复并接入新版工具定位循环，模型保持 `qwen3.8:27b-kernel-8k`。项目 Supervisor 管理网站 8787 和兼容代理 11435；平台 Ollama 11434、SGLang 30000 保留。新版定位直接使用 Ollama 原生接口，避免在定位前再做一次重复的模型分类。

网站保留 `openharmony-lkdtm-lab-v1` 的 64 例应用数据；旧社区集的目录/tgz、`$LAB/benchmark/app-format` 和新 `stability-v1` 均保留。定位配对评测使用 `stability-v1`，不能把两套日志或历史分类成绩混为定位准确率。`$LAB=/root/gpufree-data/kernel-insight-lab`。

## 自检程序

入口 `scripts/run-website-selfcheck.py` 汇总退出码、耗时、代码哈希及 JSON 报告；`scripts/website-selfcheck.js` 执行业务链路。每次使用新输出目录，保留之前的失败记录。

```bash
cd /opt/kernel-insight/app
export LAB=/root/gpufree-data/kernel-insight-lab
export PATH=/opt/kernel-insight/runtime/bin:/opt/kernel-insight/runtime:/usr/bin:/bin
export PLANTUML_JAVA=/usr/bin/java
export PLANTUML_JAR=/opt/kernel-insight/runtime/plantuml.jar
python3 scripts/run-website-selfcheck.py \
  --output "$LAB/iterations/selfcheck-$(date +%Y%m%d-%H%M%S)" \
  --base http://127.0.0.1:8787 --analysis-case OHOS-003 \
  --source-version 6.6.1
```

自检登录凭据可通过 `KERNEL_SELFCHECK_PASSWORD` 环境变量提供，程序不写入密码或会话令牌。`--repair` 先调用现有项目 Supervisor 恢复器，活跃分析期间拒绝维护；它不接管或重启平台模型。没有创建定时任务。

要补测匹配本地构建源码的真实模型链路，在上面的环境中增加：

```bash
export KERNEL_AGENT_MODE=dsh KERNEL_AGENT_ENGINE=closed-loop
export KERNEL_AGENT_TRANSPORT=ollama-native
export KERNEL_AGENT_MODEL=qwen3.8:27b-kernel-8k
export KERNEL_AGENT_BASE_URL=http://127.0.0.1:11434
export KERNEL_AGENT_PYTHON=/opt/kernel-insight/runtime/venv/bin/python
export KERNEL_VERIFIED_SOURCE_REGISTRY=/opt/kernel-insight/verified-source-registry.json
# 给汇总命令追加：
# --verified-log "$LAB/datasets/stability-v1/cases/pressure_oom/agent.log"
```

普通回归和隔离业务检查会清除继承的模型开关，防止测试意外调用线上模型。只有明确的模型试跑才启用真实请求。`--verified-log` 在临时网站实例中执行，结束后清理临时账号、数据库和上传材料，保留输出报告中的模型指标及工具证据。

| 范围 | 实际检查 |
| --- | --- |
| 登录与权限 | 登录/退出、注册、个人资料、角色修改、管理员权限、跨用户任务与材料隔离 |
| 分析与报告 | 文本、批量文件、gzip、组合选择、任务去重、报告、原日志、进度与 SSE、审核退回 |
| Skill 闭环 | 投稿、审核门禁、冻结当前 64 例、手动评测、无退化合入、经验阅读、贡献排名 |
| 展示与图表 | HTML/JS/CSS/logo/vendor、Markdown 净化、Mermaid 标记、真实 PlantUML PNG 与外链拒绝 |
| 源码与材料 | 真实官方源码下载、官方 SHA256、缓存复用、源码片段；ELF/config 身份门禁由回归测试覆盖 |
| 线上数据 | 当前 manifest、全部 64 例日志的原始字节 SHA256、健康与模型连接 |
| 真实模型 | 线上 UAF Benchmark 试跑；隔离网站 OOM 输入→匹配源码→工具→定位报告 |

单元/接口回归固定使用单独保存的 6 例社区 fixture，不依赖部署环境是否已切换到 64 例注入集。线上写入只产生明确的 Benchmark 试跑；Skill 合入、角色修改及模拟审核在临时数据库执行。

## 本轮修正

- 恢复项目 Supervisor 和网站/代理；发布时保留上一版本及配置备份，不删除旧数据集。
- 日志下载直接发送原始字节，避免非 UTF-8 故障输出在解码时改变哈希。
- 网站规则层与新 agent 都跳过正常 `debug:` 和锁依赖初始化信息，防止错误首现场/标题。
- 报告界面兼容旧、新证据格式，显示阶段、组件、第一现场、源码候选及实际模型/工具次数。
- 本地源码注册表绑定 120 个已验证日志哈希与 12 份源码文件哈希；已知补丁构建的未知日志不能静默替换为官方源码。
- 修复部署包中 sandbox 脚本缺少执行权限的问题；线上真实模型验收包含沙箱执行。

## 定位迭代结果

同模型、同数据指纹、同 6 例与 `log+source` 输入，最大 8 次模型请求、240 秒预算；差别是新增有界源码线索预检。它只使用日志中的任务名与栈帧，通过源码搜索/读取补齐证据，不读取场景标签或根因答案。

| 指标 | 对照版 | 新版 |
| --- | ---: | ---: |
| 报告完成 | 5/6 | 6/6 |
| 故障代码位置命中 | 3/5（60%） | 5/5（100%） |
| 实际模型请求总数 | 21 | 6 |
| 分析总时间 | 181.347 秒 | 95.834 秒 |
| 每例平均分析时间 | 30.225 秒 | 15.972 秒 |

模型请求减少 71.4%，总分析时间减少 47.2%。新版每个故障还执行了 3 次只读预检工具，健康基线执行 1 次；不能把“1 次模型请求”理解成没有工具工作。额外 3 例检查命中 2/3，RCU stall 保留为失败回归项。

代码命中按路径、函数及标注范围重叠计算；这不是独立机制正确率，更不是生产故障泛化准确率。OOM 的离线报告仍需复核“目标分配量”与“实际达到的驻留量”的表述。引入提交准确率、机制准确率保持未知；没有真实 vmcore、bisect 或修复前后验证。

完整配对结果、请求次数、用时、代码哈希与开放回归项见 [agent-iteration-20261007.json](agent-iteration-20261007.json)。网站验收记录见 [website-acceptance-20261007.json](website-acceptance-20261007.json)。

最终验收：发布 `f4648fac616c`，Node 36/36、Python 29/29、隔离业务 15/15、线上 9/9、匹配源码模型检查 8/8。线上 UAF 为 1 次模型请求、9.864 秒；匹配源码的隔离网站 OOM 为 1 次请求、3 次工具检查、11.225 秒，首诊断提取 0.0046 秒。这些链路时间与离线配对实验分别记录，不能混算。浏览器逐页检查并确认新报告标题、首现场和指标展示，截图保存在 `docs/previews/website-localization-v10.jpg`。
