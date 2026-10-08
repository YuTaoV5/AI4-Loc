# Benchmark 标签泄露审计与解释边界

记录日期：2026-10-09。审计对象为服务器实际用于定位评测的 stability-v1，manifest SHA256 为 `10194de902204fd6621428e2631f044fc17dada0b4fcea679ba1e00d285bb63f`。共 68 个登记案例，60 个 ready（59 故障 + 1 健康），423 个契约文件完整性检查通过。其他社区/应用格式数据集不能自动继承此审计结论。

## 结论

检查范围内未发现把 groundTruth、rootLocation、期望类别或场景命令主动发送给模型的直接答案通道。60 个 agentLog 都逐字节符合脱敏契约，原始日志单独保留。源码树未发现 manifest.json、ground-truth.json、labels.json 或 JSONL 标注；历史 63 份定位工具轨迹没有读取采集脚本。

这不是“绝对没有任何泄露”的证明。历史脚本在评测进程中载入过标签再调用 Agent，缺少操作系统隔离；现有 test 结果此前参与过 Agent 设计；故障注入函数名和实现具有语义提示。无法验证模型预训练污染，也没有独立新数据盲测。因此历史分数仅代表已有合成集合的回归表现。

## 新评测的隔离措施

1. 评测器持有 manifest 和评分标签；工作目录是随机 UUID，模型只看到 `/work` 与清理后的 `<workspace>/<source>` 路径，不收到案例 ID、family、split、causalSource 切片、注入指令和答案字段。
2. 每次启动独立 bubblewrap 进程，挂载运行时、Agent 脚本、单案例输入、所有案例共享的完整匹配源码树。没有数据集父目录、评测输出父目录或业务数据挂载。网络保留以调用本机模型，不宣称网络隔离。
3. 源码只读挂载；source_read 仅允许实现语言扩展名，并验证 realpath 位于源码根，拒绝 ../、.git、标签和采集脚本。source_search 仅返回 C/H 文件的匹配路径与源码，不返回任意目录的元数据。
4. 不挂载 proc，避免通过 `/proc/*/root` 重新看见宿主文件。每次 worker 在运行前验证评测器 canary、宿主数据目录、业务状态、proc 入口均不可见，并记录 isolation-audit.json；不满足就中止，不静默降级到同进程执行。
5. Agent 退出后才读取该案例评分标签。失败仍计入分母；真实标签、源码与日志未修改。分类对照的完整请求、定位工具证据和输出保存在私有实验目录；定位对照保存请求哈希而未保存所有中间生成 payload，上线版补充生成请求 payload 审计，认证 header 不写入文件。

同一组案例共享同一源码与编译产物，避免“为每个案例预选正确源码文件”的隐性 oracle。日志中的原始堆栈、函数名、文件位置和诊断文本是合法输入；故意删除它们会改变定位任务。真实源码中的注入函数名字很直白，所以该集合仍可能走捷径，不能与生产疑难根因准确率等同。

## 网站路径静态检查

`server/index.js` 的 Benchmark 请求只把日志和构建版本元数据交给 agent.execute，社区答案检索位于模型执行外。closed-loop 入口忽略 skills.json 和社区候选，读取实际 input.log/source/artifacts。verified source registry 为匹配构建提供相同的受哈希校验源码清单；不能将按案例根因裁剪的清单包装为独立源码获取。

网站规则引擎会从同一社区案例库检索候选答案，Skill 投稿测试也复用冻结案例类别，这些属于知识检索/规则回归，**不能当作独立根因模型评测**。旧原生 dsh 路径还可读取用户 Skill，若 Skill 在相同测试集上开发，同样存在评测污染风险。本次模型速度/定位结论只对应注明的受限入口。

## 保留与复现

工具：`scripts/audit-benchmark-leakage.py --dataset <stability-v1> --history <旧实验目录> --output <审计.json>`；新模型评测入口为 scripts/run-localization-benchmark.py，Linux bubblewrap 为必要条件。

完整审计及逐例 isolation-audit.json 位于 `/opt/kernel-insight/experiments/decision-hybrid-20261008/`；本地审计副本位于 `data/local-archive/decision-hybrid-20261008/`。初始审计因换行归一化比较和空 ki.act= 值产生的误报已修正，原报告保留。容器拒绝新 proc 挂载、源码软链接挂载失败以及未限深度探索的实验日志也全部保留，没有删除失败轮次。

后续建立机制分组独立的新测试集，冻结提示/路由后再采集，加入自然故障与源码改名扰动对照，独立复核阶段、报错组件、因果机制和引入提交。当前根因机制/引入提交/修复验证的真值不全，rootCauseAccuracy 保持 null。
