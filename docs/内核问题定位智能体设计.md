# Kernel 稳定性定位 Agent 设计与实现

更新：2026-10-07。用户最新指令：暂时停止日志收集，重点根据已验证工具设计定位 Agent。因此没有继续编译或注入故障，50 份故障数据仍为待办。

## 工作流

```mermaid
flowchart LR
  A[日志与用户选定 Skill] --> B[输入校验与任务去重]
  B --> C[SGLang 多问题分诊]
  C --> D[精确版本源码上下文]
  D --> E[程序化证据收集]
  E --> F[dsh + Qwen 比较根因假设]
  F --> G[证据行号与验证步骤]
  G --> H[人工验证与贡献统计]
```

SGLang 输出是路由线索，不是根因答案。dsh 使用 Qwen3.8，通过独立任务目录分析。模型失败时任务明确失败，不伪装成规则或模型成功。首个异常优先；后续 panic 可能只是连锁反应。多异常长日志按故障标题和文件边界分组，最多 16 个事件，保留原始行范围；相邻 panic 标为可能连锁反应。分组不证明多个独立根因，模型仍优先分析首个故障。

## 已实现的工具证据层

`scripts/kernel_triage.py` 在 dsh 运行前执行固定参数工具，不接受任意 shell 命令。证据层使用 argv 调用、40 秒总预算、单命令最多 8 秒、输出截断、最多四个符号文件。模型阶段最多四次工具调用是提示词约束，**不是运行时强制次数限制**；模型调用仍由 dsh sdk-minimal 的 bash 完成，并受已有 bubblewrap 文件权限隔离和总超时约束。

| 材料/工具 | 当前行为 | 停止或降级条件 |
|---|---|---|
| rg / 原始日志 | 带原始行号提取版本、异常、分配/释放、调用栈线索 | 输出超过预算则记录截断；无匹配不生成故障 |
| 精确版本源码 | 校验下载 SHA256，读取日志明确 path:line 附近代码 | 未知版本、文件缺失或哈希不符不猜测源码 |
| llvm-readelf / ELF | 网页材料绑定任务后生成 artifacts.json，读取架构和 Build ID | 越界路径、非 ELF、过大文件直接拒绝 |
| llvm-objdump | 与提供者声明的 Build ID 一致后，按日志中的函数名反汇编 | 匹配声明不等于证明运行构建一致；不转换 KASLR 地址 |
| llvm-symbolizer / GDB | 检测是否安装，当前不自动执行地址映射 | 必须先补运行构建一致性和重定位证据 |
| crash / drgn | 提交的 vmcore 与 vmlinux 的 Build ID、架构、日志版本一致时，执行固定 sys/bt 与最多 32 个任务摘要 | 标识缺失、不匹配、存在自动加载调试节或工具预算不足则停止；转储来源及根因仍需人工确认 |

网页分析选项支持最多四个符号文件、一个 ELF vmcore 和一个文本 .config。ELF 单文件最多 2GB、配置最多 2MB、每次总量最多 4GB；材料按账号归属隔离，流式 SHA256、只读保存，材料编号参与任务去重。压缩 kdump 暂不支持。所有附件存储在忽略的 data/materials，任务副本在沙箱只读挂载。

scripts/kernel_artifacts.py 有界解析 ELF/VMCOREINFO，核对架构、BUILD-ID 与 OSRELEASE。配置记录 SHA256 与 CONFIG_DEBUG_INFO；仅有日志或 VMCOREINFO 中相同配置哈希时标记配置材料一致。提交者声明的 Build ID 仅用于初步符号检查。即使符号与转储标识一致，runtimeMatchVerified 和 rootCauseVerified 仍保持 false，表示运行材料来源与根因尚未人工确认。

固定转储查询不接受用户表达式或脚本：crash 禁 .crashrc，drgn 仅加载显式符号，工具禁 debuginfod 自动下载、使用空 HOME；含自动加载或外部调试链接节的符号拒绝查询。每个子进程最多 8 秒、4GB 虚拟内存及 8 CPU 秒，仍受 40 秒总证据预算与输出截断。尚无真实配套 vmcore，本次只验证了门禁与固定参数，不宣称真实转储定位成功。

## 诊断策略

| 问题族 | 必须检查的证据 | 常见误判 |
|---|---|---|
| 越界/踩内存 | 访问类型和大小、对象边界、分配栈、精确源码布局 | 将崩溃函数当成最早破坏内存的函数 |
| UAF | alloc/free/access 三条生命周期、异步引用、引用计数 | 仅凭函数名推断释放者 |
| 泄漏 | kmemleak 对象、失去拥有引用的路径、持续增长证据 | 把 OOM 直接等同于泄漏 |
| watchdog | 卡住的 CPU/任务、IRQ 和抢占状态、持续时间 | 将正常慢负载断言为死锁 |
| 锁/自旋锁 | 等待者与持有者、锁对象、可达锁顺序、原子上下文 | 将 lockdep 类别警告断言为已发生的死锁 |
| hung task | 等待点、mutex/completion 的拥有者或生产者 | 将所有 D 状态断言为磁盘问题 |
| RCU stall | 阻塞宽限期的 CPU/任务、静止状态和调度情况 | 只看到 RCU 栈就归咎于 RCU 实现 |
| OOM | cgroup/全局压力、分配上下文、victim 和 allocator | 将分配失败断言为内存损坏 |

当前兼容报告分类仍用已有七类；泄漏/watchdog 是 evidence.families 中的独立线索，不冒充新分类已完成接入。

## 输出与状态

保留 `evidence.json`：原始行号、源码 revision/URL/SHA、工具参数/退出码/截断标记/实际输出、材料缺口。模型读取最多 9000 字符的 `evidence-brief.txt`，选定 Skill 摘要总计最多 4000 字符，避免 8K 上下文被大日志淹没。完整输入仍保留供有限补查。

个人空间任务实时显示 triage → source → symbols → hypotheses 等实际事件。报告新增可展开工具证据；模型私有思考不发送给用户。程序发现的材料缺口合并进最终 limitations，不能被模型省略。非法证据行号过滤；无有效日志证据的假设置信度强制降为 low。所有报告仍待人工确认，安装工具或高类别分数不等于根因已证明。

Skill 仍由用户选择，报告保留贡献者；本次没有改变管理员审核、手动 Benchmark 和不退化合入门禁。Agent 代码变更加入任务指纹，旧报告不会错误复用为新流程结果。Benchmark 标签、修复摘要不进入模型任务目录。

## 验证与后续

Python 测试覆盖原始行号不变、输入不可变、源码哈希错误、符号路径越界、健康日志不造故障。既有网站测试继续覆盖账号、PR 门禁、去重、进度和源码安全。旧六例模型跑分是旧流程结果；新流程实测单独保存，不能冒用旧分数。

本轮新增上传权限、材料去重、ELF 注记、多个事件、构建不匹配拒绝查询、固定查询参数及阴性日志拒答测试。下一步：用可信来源的真实配套 vmcore 验证只读查询；扩大阴性与跨版本样本；人工根因确认后按 Skill 贡献统计。完整代码树搜索需要以已验证版本只读挂载，当前默认提供日志关联文件，不能声称全树检索已完成。

参考： [Linux bug hunting](https://docs.kernel.org/admin-guide/bug-hunting.html)、[LLVM](https://llvm.org/docs/CommandGuide/)、[dsh Python SDK](https://github.com/deepseek-ai/deepseek-harness/tree/master/python/sdk)。
