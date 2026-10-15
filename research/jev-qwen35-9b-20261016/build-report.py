"""Render a data-backed report after completion; never invent missing metrics."""
import pathlib,json,csv,html,statistics
E=pathlib.Path(__file__).resolve().parent
def load(p):return json.loads((E/p).read_text(encoding='utf-8'))
def rows(p):return [json.loads(x) for x in (E/p).read_text(encoding='utf-8').splitlines()]
def table(headers,rs):return '| '+' | '.join(headers)+' |\n|'+'|'.join('---' for _ in headers)+'|\n'+'\n'.join('| '+' | '.join(str(v) for v in r)+' |' for r in rs)+'\n'
def main():
    summary=load('summary.json');train=load('training-complete.json');completion=load('completion.json')
    assert completion['status']=='completed' and completion['restored']
    data=load('dataset-frozen.json');training=rows('training-steps.jsonl')
    accuracy=summary['accuracy'];acc=lambda m,a:next(r for r in accuracy if r['checkpoint']==m and r['api']==a and r['source']=='all')
    paired=summary['checkpoint_concurrency_summary']
    select=lambda m,a,c,d,cache:next(r for r in paired if r['checkpoint']==m and r['arm']==a and r['concurrency']==str(c) and r['decisions']==str(d) and r['cache']==cache and r['mode']=='sequential' and r['instrumented']=='True')
    text='# Qwen3.5-9B 决策模型：训练与项目并发复测\n\n'
    text+='## 实测摘要\n\n'
    for api in ['decision','chat']:
        b,t=acc('base',api),acc('trained',api)
        text+=f"- {api} 第一诊断家族：基座 {b['correct']}/{b['cases']}（{b['accuracy']:.1%}），训练后 {t['correct']}/{t['cases']}（{t['accuracy']:.1%}）。这是弱监督标签一致性，不是独立专家根因准确率。\n"
    for model in ['base','trained']:
        d,c=select(model,'decision',4,8,'warm'),select(model,'chat',4,8,'warm')
        reduction=(1-float(d['makespan_seconds'])/float(c['makespan_seconds']))*100
        text+=f"- {model} 的 4任务×8步、预热条件：Decision 整批 {float(d['makespan_seconds']):.4f}s，Chat 单token整批 {float(c['makespan_seconds']):.4f}s，Decision 耗时变化为减少 {reduction:.2f}%；活跃 KV 峰值均值分别 {float(d['peak_active_kv_mib']):.2f}/{float(c['peak_active_kv_mib']):.2f}MiB。需结合完整8条件与置信区间解读。\n"
    text+='\n## 模型、方法与来源\n\n'
    text+='用户确认采用官方 Qwen3.5-9B 预训练模型，固定 revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`。通过独立官方元数据校验15个文件；镜像只承担传输。参考 Laya 类型化概率决策与 proper-score RLCD，在 Qwen 因果混合注意力骨干训练 LoRA；未复用 Laya 的双向 BERT 决策头，也不是 TypeSafe Jev 专有架构复现。没有从随机参数预训练9B。\n\n'
    text+=f"48处文本投影使用 rank8、alpha16 LoRA，共 {train['trainable_parameters']:,} 个参数，BF16骨干/FP32适配器与AdamW。3epoch共{train['steps']}微步（每4微步更新，99次优化器更新），学习率1e-4。第1epoch为CE，后2epoch为CE＋RLCD。按开发NLL选 epoch{train['best_epoch']}（从0计），选定温度{train['temperature']}。从训练循环开始到评估、导出与哈希共{train['seconds']:.1f}s；不含此前加载、首次基座评估与编译。峰值torch分配{train['peak_allocated_bytes']/2**30:.2f}GiB；不等同于NVML resident峰值。\n\n"
    text+='RLCD 在分类logits上采样零均值高斯扰动，以 log score＋0.75 spherical score 为奖励，按组标准化优势构造高斯策略梯度，并加入CE。只训练choice任务，不声称训练了noul、score、工具选择或根因提交预测能力。Laya还支持有序score的RPS，此实验无该监督。合并后恢复原模型架构，基座与训练后均用同一SGLang，消除跨引擎对比中的主要混杂。\n\n'
    text+='理论边界：未截断的log/spherical评分规则为概率监督提供依据；本实现延续log奖励下限−9.21、有限4次扰动采样及优势标准化，不能把这些数值近似后的训练目标宣称为全域严格恰当性或无偏策略梯度的证明。监督奖励来自既有标签，不涉及人类偏好或在线真实故障反馈；CE预热、RLCD和开发选点共同作用，本轮没有等训练步数的CE-only消融、多seed或新盲测，不能把最终差异单独归因RLCD。\n\n'
    text+='```mermaid\nflowchart LR\n L[真实日志 / 源码 / 编译产物] --> E[只读工具提取证据]\n E --> D[Qwen9B 决策前向]\n D --> P[候选概率 / 第一诊断定界]\n P --> C[Chat 提出可验证假设]\n C --> T[源码搜索 / 阅读 / 符号化]\n T --> C\n C --> R[带证据的定位报告与缺失信息]\n R --> V[隔离评估器 / 机制聚类统计]\n F[机制分组 / 冻结划分] --> A[仅train训练 / dev选点校准]\n A --> D\n F --> G[仅test金标 / Agent不可见]\n G --> V\n```\n\n这是系统工作逻辑，不表示本次监督覆盖了所有节点。本轮训练的是决策节点的第一诊断family任务，报告节点另做小样本完整流程检查。测试评分不回流训练。\n\n'
    text+='[Laya固定版本](https://github.com/NandhaKishorM/laya/tree/4ac226d5ee88ed6df8db288a05c766d7a34ee682)；[Qwen模型卡](https://huggingface.co/Qwen/Qwen3.5-9B)；[Foundry模型生命周期与部署概览](https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/foundry-models-overview)。Foundry页面不是Jev算法来源，本轮没有使用Azure资源。\n\n'
    text+='## 数据、划分和标签泄露审计\n\n'
    text+=f"现有两种内核构建共{sum(data['counts'].values())}条纳入日志，划分为{data['counts']}。跨内核按规范化注入机制分组，历史test组取并集，再用固定哈希划分其余组；重复读写、refcount、usercopy等变体归组。模型只能看到经过注入标识遮盖的诊断窗口、问题与选项，不包含路径、split、gold或机制字段。精确输入及机制组跨划分交集为空；原始文件逐个验哈希，源哈希与窗口哈希在冻结清单。\n\n"
    text+='标签按第一诊断标记及其邻近内容确定，是程序产生的弱监督。没有独立专家复核，没有新盲测保证；自然近重复、预训练污染和已有开发者见过测试集的影响仍在。窗口按诊断标记提取，只支持定界任务；不能据此评价自主从全部日志寻找首现场的能力。可见的“KASAN use-after-free”等是推理证据，同时也意味着该任务相当程度是显式诊断解析，不能当作隐含根因推理能力。\n\n'
    text+='开发集仅4条、3类，部分test类别从未进入train，温度在边界取0.5，校准容易过拟合。主准确率按每案例三种选项置换多数投票；置换和跨内核同机制不作独立样本。两模型差异用机制聚类bootstrap，探索性区间不构成准确率等效检验。\n\n'
    text+=table(['划分','类别','数量'],[(split,label,n) for split,labels in data['label_counts'].items() for label,n in labels.items()])
    text+='\n## 概率与标签一致性\n\n'+table(['模型','接口','内核','正确/案例','准确率'],[(r['checkpoint'],r['api'],r['source'],f"{r['correct']}/{r['cases']}",f"{r['accuracy']:.2%}") for r in accuracy])
    text+='\n![混淆矩阵](figures/accuracy-confusion.png)\n\n'
    baseline_rows=list(csv.DictReader((E/'tables/base-decision-case-predictions.csv').open(encoding='utf-8-sig')))
    trained_rows=list(csv.DictReader((E/'tables/trained-decision-case-predictions.csv').open(encoding='utf-8-sig')))
    family_results=[]
    for label in data['classes']:
        b=[r for r in baseline_rows if r['label']==label];t=[r for r in trained_rows if r['label']==label]
        family_results.append((label,len(b),sum(r['prediction']==label for r in b),sum(r['prediction']==label for r in t)))
    text+=table(['第一诊断类别','测试支持数','基座正确','训练后正确'],family_results)
    text+='\n主要提升集中在“explicit_panic_or_warning”与“memory_protection”的标签边界，属于本任务监督口径的适配；locking仍有错误，watchdog与OOM没有测试支持，不能据此得出所有故障家族均改善的结论。\n\n'
    text+=table(['接口','训练后−基座准确率','机制簇','机制聚类95%区间'],[(r['api'],f"{r['trained_minus_base_accuracy']:+.2%}",r['mechanism_clusters'],f"[{r['cluster_bootstrap95'][0]:+.2%}, {r['cluster_bootstrap95'][1]:+.2%}]") for r in summary['paired_accuracy']])
    text+='\n'+table(['模型','温度','案例NLL','Brier','ECE(10箱)'],[(r['checkpoint'],r['temperature'],f"{r['case_nll']:.4f}",f"{r['case_brier']:.4f}",f"{r['ece10']:.4f}") for r in summary['calibration']])
    text+='\n这些概率指标先对每案例的三种选项置换平均，再评分；不与原始逐请求校准指标混用。可靠性分箱原始数见 `calibration.json`。只在开发集确定温度，测试集只报告结果；若温度校准使测试NLL恶化，不能用准确率不变掩盖这一点。\n\n'
    text+='![训练目标与概率校准](figures/training-and-calibration.png)\n\n候选概率是给定选项集合后的条件分布，不是保证无遗漏的全空间真值概率。12选项上的开发温度也不能自动推广至其他选项数或stage/reporter等新问题。\n\n'
    calibration=summary['calibration'];b=next(r for r in calibration if r['checkpoint']=='base');t=next(r for r in calibration if r['checkpoint']=='trained' and r['temperature']==1)
    text+=f"本轮正是这一反例：准确率提高同时，NLL由{b['case_nll']:.3f}升至{t['case_nll']:.3f}；部分错误高度自信。Brier/ECE改善不等于所有概率质量指标改善。温度0.5来自4条开发样本，测试NLL进一步恶化，当前不建议将此校准温度作为可信置信度上线。\n\n"
    drift=load('merge-validation.json')
    text+=f"BF16合并前后4条开发输入top1全部相同，但最大logit差达{max(x['max_absolute_logit_difference'] for x in drift):.3f}，并非逐位等价。最终主结果均测量实际合并后SGLang服务；未合并模型的离线分数只作为旁证，不冒充部署分数。\n\n"
    text+='## 并发实验与完整计时口径\n\n'
    text+='每模型112trial：80主条件（2接口×1/4任务×1/8顺序步骤×冷/热×5重复），20批量8题，12观测敏感性。980正式HTTP、1330内部问题；预检、warmup、prime、准确率与Agent调用独立计数。模型固定执行基座→训练后，同模型内部trial随机化。4个实际日志诊断窗口相同，每任务题干不变、选项轮换；部分选项集合不含正确类别，因此性能实验不报准确率。\n\n'
    text+='SGLang0.5.21、BF16、8192上下文、mem-fraction-static0.55、32个FP32 linear状态槽、实际容量4，相同A100 80GB分时独占。Decision完整概率响应耗时与Chat首个非空delta.content分别记录，Chat只生成1token。两接口完整prompt token ID逐项相等。没有把响应头或role当TTFT；Decision没有文本TTFT。批量8题是8个内部prompt评分，不是Laya式单次共享状态编码。\n\n'
    text+='![两模型八条件热力图](figures/checkpoint-latency-heatmap.png)\n\n'
    text+=table(['模型','缓存','任务×步骤','Decision整批秒','Chat整批秒','Decision完整概率均值秒','Chat首内容均值秒'],[
        (m,cache,f'{c}×{d}',f"{float(select(m,'decision',c,d,cache)['makespan_seconds']):.4f}",f"{float(select(m,'chat',c,d,cache)['makespan_seconds']):.4f}",f"{float(select(m,'decision',c,d,cache)['mean_call_seconds']):.4f}",f"{float(select(m,'chat',c,d,cache)['mean_ttft_seconds']):.4f}")
        for m in ['base','trained'] for cache in ['cold','warm'] for c,d in [(1,1),(4,1),(1,8),(4,8)]])
    text+='\n每侧详细统计及6组图见 `analysis/base`、`analysis/trained`；逐请求排队、主机prefill区间、缓存命中与响应在其 `tables/calls.csv` 和 `server-requests.csv`。调度快照保留 run_batch/process_batch_result 前后，包含队列长度、请求ID、活跃/可回收attention KV、linear状态池与torch allocator。NVML约100ms保留显存、功耗、利用率、温度和时钟；边界间无法捕捉的短峰值不外推。\n\n'
    text+='9B全注意力每token KV=2×8层×4KV头×256维×2字节=32KiB。linear状态另计。resident显存、活跃KV与预分配池容量不是同一指标；不得因预分配池同样大而宣称没有活动KV差异，也不能把9B比旧27B的小体积归因于Decision接口。`trial-power-energy.csv`只在采样覆盖区间积分GPU板级能量，不将并发任务重复分摊，不视为单请求能耗或纯模型动态能耗。\n\n'
    text+='![显存、KV和功耗对齐轨迹](figures/gpu-kv-power-timeline.png)\n\n'
    text+='## 现有Agent闭环检查\n\n'
    agent=[]
    for m in ['base','trained']:
        for r in load(f'data/{m}/agent-summary.json'):
            metrics=r['metrics'];agent.append((m,r['variant'],r['case'],r['status'],r['scores']['codeLocationHit'],metrics.get('modelRequests'),metrics.get('toolCalls'),metrics.get('boundarySeconds'),metrics.get('localizationSeconds')))
    text+=table(['模型','流程','案例','状态','源码位置命中','模型HTTP','工具次数','定界秒','总定位秒'],agent)
    text+='\n三个案例是已见过历史测试，不构成新的独立根因实验。源码位置交叠命中不是根因机制正确，更不能证明找到了引入问题的提交；数据集没有独立提交金标。沿用实际部署Agent的证据读取、工具、匿名工作目录和bubblewrap；只在冻结副本显式关闭thinking。完整工具/API轨迹私有保留，公开仅导出计数和评分。失败计入分母，不能只报告成功请求耗时。\n\n'
    if (E/'agent32k/completion.json').exists():
        done=load('agent32k/completion.json');assert done['status']=='completed' and done['restored']
        repaired=[]
        for model in ['base','trained']:
            for r in load(f'agent32k/{model}/agent-summary.json'):
                m=r['metrics'];repaired.append((model,r['variant'],r['case'],r['status'],r['scores']['codeLocationHit'],m.get('modelRequests'),m.get('toolCalls'),m.get('boundarySeconds'),m.get('localizationSeconds')))
        text+='### 独立32k上下文及客户端兼容修复复核\n\n'
        text+='8k失败不能解释为模型不会定位：原请求实际17,672/20,734token，HTTP400明确报告超过8192。首次32k复核进一步暴露客户端将`tool_calls:null`当列表遍历的错误；该轮中止、守护恢复、部分结果与原因独立保留。随后在全新目录重跑两模型，显式关闭thinking、将空tool_calls归一为[]，上下文32768，其他配置相同；没有改动8k性能/分类结果。\n\n'
        text+=table(['模型','32k流程','案例','状态','源码位置命中','模型HTTP','工具次数','定界秒','总定位秒'],repaired)
        text+='\n完整公开明细见 `agent32k/`，每侧6个匿名bubblewrap工作目录均验证看不到评估canary、业务状态、host root及host proc。上下文修复和客户端修复不是权重训练收益，两模型均接受相同修复。3例结果只作闭环功能与效率探索；混合流程若增加调用与总时间，不能以局部定界接口更快抵销这个事实。\n\n'
    text+='## 结论与适用边界\n\n'
    for api in ['decision','chat']:
        diff=acc('trained',api)['accuracy']-acc('base',api)['accuracy']
        text+=f"- {api}：本轮训练后第一诊断弱标签一致性变化 {diff:+.2%}。该观测只能支持此冻结数据/口径；若下降，应优先补充独立专家标注、扩大开发集并覆盖缺失类别，不能以训练loss接近0作为上线依据。\n"
    text+='- LoRA训练和权重合并保持了原Qwen架构，并不会自动改变SGLang的KV管理或将8题合为一次前向。接口省去生成步骤是否有利，必须看各条件延迟及实际缓存命中；不能从“无输出token”推导显著省显存。\n- 只有本轮记录才是9B实测；旧27B、PPLX和不同引擎结果保留为历史资料，不能拼成同一消融。当前设计仍有固定模型顺序、小开发集、弱标签、有限输入和观测开销等限制；未做多训练seed、未获得新盲测、未证明跨项目泛化或根因提交提升。\n\n'
    text+='## 部署、恢复及证据\n\n'
    text+='原27B生产模型已由独立恢复控制器恢复，实际Decision与Chat合成请求验收见 `restoration.json`；实验30003退出。恢复模型服务不代表网站全部功能通过验收。PPLX当前未运行，其11个非必要、逐个校验的可下载分片已依用户授权清理；恢复固定版本和文件清单见 `weight-reclamation.json` 及 `pplx-recovery-metadata.json`，配置、tokenizer和代码未删。\n\n'
    text+='新权重位于 `/root/gpufree-data/systemone/models/AI4Loc-Jev-Qwen3.5-9B`，哈希见 `trained-checkpoint-manifest.json`。训练适配器、原始请求/SSE/源日志/完整调度记录与失败重试留在服务器，并打包到本地Git忽略目录；公开仓库只保存脚本、允许字段数据、表格、图和说明，不发布密码、业务状态、原始日志或大模型权重。\n\n'
    text+='完整执行流程、命令参数与参考见 [README](README.md)。公开数据按完整prompt token SHA＋服务端接收时间唯一关联HTTP；离线核验入口 `verify-public.py`，重算入口 `analyze.py` / `build-report.py`。\n'
    (E/'REPORT.md').write_text(text,encoding='utf-8')
    # Markdown source is canonical. Render safe standalone text with figure links.
    (E/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Qwen3.5-9B决策训练与复测</title><style>body{max-width:1200px;margin:40px auto;font:16px/1.7 system-ui;background:#fafafa}pre{white-space:pre-wrap;overflow-wrap:anywhere}img{width:100%}</style><h1>Qwen3.5-9B决策训练与复测</h1><img src="figures/accuracy-confusion.png"><img src="figures/checkpoint-latency-heatmap.png"><pre>'+html.escape(text)+'</pre>',encoding='utf-8')
    print('REPORT_BUILT')
if __name__=='__main__':main()
