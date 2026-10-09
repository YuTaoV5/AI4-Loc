from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
template = (ROOT / "tools/kelip-slide/assets/deck-template.html").read_text(encoding="utf-8")

def S(section, title, kicker, h1, sub, body, cls=""):
    title = title.replace('"', '&quot;')
    return f'''<section class="slide {cls}" data-sec="{section}" data-title="{title}">
      <div class="kicker"><b>{len(slides)+1:02d}</b>{section} · {kicker}</div>
      <h1>{h1}</h1><div class="sub">{sub}</div>{body}
    </section>'''

def flow(items):
    parts = []
    for i, (title, desc, accent) in enumerate(items):
        c = "node accent" if accent else "node"
        parts.append(f'<div class="{c}"><b>{title}</b><span>{desc}</span></div>')
        if i < len(items)-1:
            parts.append('<div class="flow-arrow">→</div>')
    return '<div class="flow">' + ''.join(parts) + '</div>'

def rows(items):
    return '<div class="rows">' + ''.join(
        f'<div class="rowline"><b>{a}</b><span>{b}</span><small>{c}</small></div>' for a,b,c in items
    ) + '</div>'

def px(name, label):
    patterns = {
        "chip": ["00111100","01111110","11011011","11111111","11111111","11011011","01111110","00111100"],
        "log": ["11111110","10000010","10111010","10100010","10101110","10000010","11111110","00000000"],
        "trace": ["10000001","11000011","01100110","00111100","01100110","11000011","10000001","00000000"],
        "fork": ["00011000","00011000","00011000","11111111","11000000","11000000","00000011","00000011"],
        "gauge": ["00111100","01000010","10011001","10100101","10111101","10000001","01000010","00111100"],
    }
    cells = []
    for y, line in enumerate(patterns[name]):
        for x, bit in enumerate(line):
            if bit != "0":
                color = "#0071E3" if bit == "1" else "#9CC8FF"
                cells.append(f'<rect x="{x}" y="{y}" width="1" height="1" fill="{color}"/>')
    return f'<svg class="pxico" viewBox="0 0 8 8" aria-label="{label}" shape-rendering="crispEdges">{"".join(cells)}</svg>'

slides = []

# Cover uses the same 1920x1080 Kelip stage and navigation.
slides.append(f'''<section class="slide cover" data-sec="封面" data-title="Jev × 手机 SoC 软件工程">
 <div class="t"><div class="kicker">技术专题 · 研发工具链中的结构化决策</div><h1>Jev</h1>
 <div class="p">把 <b>概率判断</b> 接进手机 SoC 软件流程<br>看清它能做什么，也守住它不该做的事</div></div>
 <div class="brand">华为手机 SoC 软件工程视角 · 2026-09</div>
 <div class="photos">
   <div class="cover-icon">{px("chip","SoC")}<b>SoC 软件栈</b></div>
   <div class="cover-icon">{px("log","日志")}<b>构建与验证</b></div>
   <div class="cover-icon">{px("trace","Trace")}<b>Perfetto 分析</b></div>
   <div class="cover-icon">{px("fork","分流")}<b>Typed decision</b></div>
   <div class="cover-icon">{px("gauge","置信度")}<b>校准与门控</b></div>
 </div></section>''')

slides.append(S("定位","先在研发工具链试点，别进内核热路径","工程判断","先在研发工具链试点，<span class='thin'>别进内核热路径</span>","它适合做异构日志的语义分流，不是可直接烧进手机的本地模型",
    flow([("编译 / CI","日志分类 · 失败分流",True),("性能 / 功耗","特征归因 · 回归排序",True),("代码 / 设备动作","确定性校验 · 人工签核",False)]) +
    '<div class="note"><b>边界：</b>研发主机或 CI 服务侧的建议能力；不进入调度器、驱动、中断或启动关键路径。</div>'))

slides.append(S("模型接口","Jev 回答判断题，不负责写解释","TypeSafe API","Jev 回答判断题，<span class='thin'>不负责写解释</span>","把非结构化问题转为预先定义的输出空间",
    flow([("STATE","日志 + 指标 + 设备 / 构建上下文",False),("Jev 1.13","对问题并行评估",True),("ANSWERS","typed 选择、分数、是 / 否概率",False)]) +
    '<div class="note">输入支持 string / JSON / 文本数组；输出可直接供程序读取。类型约束不代表语义结论总正确。</div>'))

slides.append(S("模型接口","Choice、Score、Noul 解决不同判断","三种原语","Choice、Score、Noul <span class='thin'>解决不同判断</span>","先定义输出空间，再把问题交给模型",
    rows([("Choice","这个失败最像哪个子系统？","driver 0.74 · HAL 0.18 · kernel 0.08"),
          ("Score","这次性能退化严重度在哪一档？","0–3 档的概率加权位置"),
          ("Noul","故障是否只发生在特定 SoC revision？","P(yes) = 0.82")]) +
    '<div class="note">Score 是序位分布的期望位置，不是物理量；Noul 不返回 confidence 字段。</div>'))

slides.append(S("方案比较","选择取决于数据、时延和部署边界","工程基线","选择取决于<span class='thin'>数据、时延和部署边界</span>","建议和规则、本地 encoder 以及通用 LLM 同台比较",
    '<div class="tblwrap"><table class="tbl left wrap compact"><thead><tr><th>方案</th><th>适合</th><th>代价 / 边界</th></tr></thead><tbody>'
    '<tr><td><b>规则 / parser</b></td><td>格式明确、可验证的条件和数值计算</td><td>措辞变化会让规则变脆</td></tr>'
    '<tr><td><b>本地 encoder</b></td><td>有标签、高吞吐、离线、本地数据</td><td>需标注和版本维护；新类目要更新</td></tr>'
    '<tr><td><b>通用 LLM</b></td><td>解释、总结、开放式推理、代码生成</td><td>自由文本需校验；时延 / 成本较高</td></tr>'
    '<tr class="hi"><td><b>Jev</b></td><td>固定问题空间、概率分流、零样本启动</td><td>托管 API、英文优先；本域表现需实测</td></tr>'
    '</tbody></table></div>'))

slides.append(S("测量","官方倍数是特定工作流的上沿","官方发布文 · 2026-09-15","官方倍数是特定工作流的<span class='thin'>上沿</span>","不能把服务端评测数字直接当成手机端时延或 SoC 工程收益",
    '<div class="stats"><div class="stat"><div class="n">$0.042<small>/M</small></div><div class="l"><b>当前官方输入价格</b><br>按输入 token 计费，输出免费；限额可变</div></div>'
    '<div class="stat"><div class="n">70–500<small>ms</small></div><div class="l"><b>官方发布的服务端区间</b><br>网络位置、负载和请求形状会影响实测</div></div>'
    '<div class="stat text dim"><div class="n"><span class="acc">193.6× / 444.6×</span></div><div class="l"><b>最高速度 / 成本倍数</b><br>一个官方 workflow 的高端结果，非普遍基准</div></div></div>'
    '<div class="note">官方说明：这些 workflow 由模型能力团队设计，并以大型 LLM 平均作参照，偏差可能存在。</div>'))

slides.append(S("可靠性","置信度适合分流，不等于正确率保证","TypeSafe Confidence","置信度适合分流，<span class='thin'>不等于正确率保证</span>","校准是群体属性，不能把 0.9 解释成这一条有 90% 把握正确",
    flow([("概率分布","Choice / Score 的各类概率",False),("阈值验证","reliability · ECE · Brier",True),("工程动作","低风险自动分流 / 高风险人审",False)]) +
    '<div class="note">按误报与漏报成本分别定阈值；再看 risk–coverage，验证自动覆盖率升高时错误如何变化。</div>'))

slides.append(S("可靠性","已知弱点决定预处理和降级策略","官方 Jev 1.13 Jaggedness","已知弱点决定<span class='thin'>预处理和降级策略</span>","模型适合语义判断；把数学、计数、日期比较留给代码",
    rows([("字面理解 / 否定","“未复现”与“已复现”容易受上下文影响","结构化字段，明确正反条件"),
          ("数值与日期","不要让模型算 p95、频率差、时间窗","parser / SQL / 代码"),
          ("长 state / 无关内容","噪声会降低判断质量并增加成本","先筛选、去重、聚合"),
          ("对抗性文本","日志内容可改变模型判断","state 当不可信数据，做注入测试"),
          ("中文 / 多跳推理","CJK 并非主要优化语言，多跳更脆弱","分语言、分难度评测；保留 unknown")]) +
    '<div class="note">以上限制来自 TypeSafe 自己的 1.13 文档，版本升级后也要重新回归。</div>'))

slides.append(S("外部评测","有标签数据时，小型 encoder 可能更合适","GitHub · 预注册独立评测","有标签数据时，<span class='thin'>小型 encoder 可能更合适</span>","Banking77 · paired n=208 · 单一英文意图分类任务",
    '<div class="tblwrap"><div class="tt">Accuracy and median call duration</div><table class="tbl num two compact"><thead><tr><th>配置</th><th>准确率</th><th>中位耗时</th></tr></thead><tbody>'
    '<tr class="hi"><td>Jev 1.13</td><td class="acc">83.2%</td><td>0.44 s</td></tr>'
    '<tr><td>GPT-5.6 Terra</td><td>87.5%</td><td>1.51 s</td></tr>'
    '<tr><td>监督 encoder</td><td>93.3%</td><td class="acc">0.01 s</td></tr>'
    '</tbody></table><div class="note">encoder 约用 10,000 条标签训练。零样本启动的便利性与任务准确率是两条不同轴。</div></div>'))

slides.append(S("外部评测","二次复核可能把正确答案改错","GitHub · jev-classification-benchmark","二次复核可能把<span class='thin'>正确答案改错</span>","TREC 200 条试验样本：GPT-6 Astra few-shot 经 Jev review 后准确率下降",
    '<div class="stats two"><div class="stat"><div class="n">194 / 200</div><div class="l">复核前正确数<br>GPT-6 Astra few-shot</div></div>'
    '<div class="stat dim"><div class="n">173 / 200</div><div class="l">复核后正确数<br>Jev 纠正 3 个，同时改错 24 个正确答案</div></div></div>'
    '<div class="note">单次探索性测试，不能概括 Jev 的整体表现；但足以说明二次模型复核也要冻结数据、测误改率。</div>'))

slides.append(S("参考案例","Jev 适合插在召回与规则之间","skJack/-lip- · 第 30 期 Jev","Jev 适合插在<span class='thin'>召回与规则之间</span>","PaperDance：先用全文与向量检索召回论文，再用 Jev 判断相关性并重排",
    flow([("25 万篇","全文 + 向量候选召回",False),("Jev","选择 / 概率判断",True),("代码策略","阈值过滤、重排、人审",False)]) +
    '<div class="note">作者报告：54 篇标注子集英文查询 AUC 0.995，纯中文查询 0.924；个别关键论文概率仅 0.14–0.25。小样本自测，不可外推为 SoC 故障准确率。</div>'))

slides.append(S("SoC 应用","把判断点放在研发工具链","手机 SoC 软件生命周期","把判断点放在<span class='thin'>研发工具链</span>","以通用 Android / Linux 工程名词举例，华为私有栈映射到对应模块",
    flow([("Bring-up","启动 · probe · 电源时序",False),("CI / VTS","失败分流 · 回归归因",True),("性能 / 功耗","trace 特征 · 异常排序",True),("发布门禁","确定性条件 · 责任人签核",False)]) +
    '<div class="note">AOSP VTS 覆盖 Kernel 与 HAL 测试；这里借它说明研发链路，不假定华为内部使用相同接口。</div>'))

slides.append(S("SoC 用例","失败日志可自动分流，不自动改代码","用例一 · CI / VTS","失败日志可自动分流，<span class='thin'>不自动改代码</span>","适合样本量大、owner 难找、历史失败重复出现的模块",
    rows([("输入","test timeout · board R2 · kernel build 8421","保留原始 log 与测试 ID"),
          ("计算","重试率、版本差异、首次失败时间","代码做精确比较"),
          ("Jev","Choice：clock / power / driver / HAL / unknown","给概率，不写根因长文"),
          ("动作","建议 owner、附证据片段、相似问题链接","人审后回填标签")]) +
    '<div class="note">不允许模型结论直接改代码、刷机、重启设备或关闭 release blocker。</div>'))

slides.append(S("SoC 用例","数值归因留给 PerfettoSQL 和代码","用例二 · trace 分析","数值归因留给<span class='thin'>PerfettoSQL 和代码</span>","Jev 负责“更像哪类回归”；指标与差值由确定性脚本计算",
    flow([("Perfetto","sched / freq / GPU / power / logs",False),("SQL / parser","wake-to-run p95 · jank · 频点驻留",True),("Jev","scheduler / GPU / thermal / I/O",False)]) +
    '<div class="note">功耗 rail 数据依设备支持而异。先规范 trace 配置与窗口，再让模型读小而相关的特征摘要。</div>'))

slides.append(S("SoC 用例","Bring-up 归因要保留版本上下文","用例三 · 跨版本兼容性","Bring-up 归因要保留<span class='thin'>版本上下文</span>","相同错误行不代表相同根因；设备与软件配置必须跟随样本",
    rows([("硬件维度","SoC revision · board · PMIC · memory SKU","决定问题是否局限某一物料组合"),
          ("软件维度","kernel branch / config · firmware · HAL version","由脚本精确定位首次变化版本"),
          ("环境维度","cold / warm boot · 温度档 · lab station · test ID","分清偶发和稳定复现"),
          ("Jev 判断","相似故障族 · 疑似共同依赖 · 建议 owner","不把相关性当成已验证 root cause")]) +
    '<div class="note">版本比较、回归区间和频率由代码计算；模型只辅助解释语义相似度。</div>'))

slides.append(S("集成设计","把工程证据装进 state，把策略留在代码","示意 JSON · 非真实调用","把工程证据装进 state，<span class='thin'>把策略留在代码</span>","问题要直白，标签描述要能区分具体边界",
    '<div class="code2"><div class="code"><div class="tt">request state</div><pre>{\n  "model": "jev-1.13.0",\n  "state": {\n    "failure": "probe defer -EPROBE_DEFER",\n    "subsystem": "camera power sequence",\n    "board_rev": "R2",\n    "kernel": "6.x / build 8421",\n    "repeat_rate": "3 of 5 cold boots",\n    "boot_ms_delta": 186\n  },\n  "questions": {\n    "owner": { "type": "choice", ... },\n    "severity": { "type": "score", ... },\n    "cold_boot_only": { "type": "noul", ... }\n  }\n}</pre></div>'
    '<div class="code"><div class="tt">deterministic policy</div><pre>if api_timeout:\n    fall_back_to_existing_queue()\nelif owner.confidence &lt; τ:\n    route_to_human_triage()\nelif severity.score &gt;= gate:\n    suggest_component_owner()\nelse:\n    attach_suggestion_only()\n\n# exact math stays in code\n# never release from model score alone</pre></div></div>'))

slides.append(S("集成设计","本地抽取与策略，托管服务只做语义判断","目标架构","本地抽取与策略，<span class='thin'>托管服务只做语义判断</span>","把 Jev 当可替换依赖；服务异常不阻断 build、test 或刷机",
    flow([("设备 / 测试场","logcat · tombstone · Perfetto",False),("研发主机","脱敏 · SQL · 去重 · 压缩 state",True),("Jev API","固定版本 · typed answer",False),("研发闭环","建议 owner · 人工确认 · 标签回流",False)]) +
    '<div class="note">原始数据留本地，外发字段最少化；不允许调用外部服务时，替换成本地 encoder 或规则。</div>'))

slides.append(S("部署边界","托管服务与手机端实时控制不是一回事","官方 Models 文档","托管服务与<span class='thin'>手机端实时控制</span>不是一回事","Jev 当前以 API 方式提供；未公开可下载权重，输入仅文本",
    '<div class="two"><div class="col"><div class="h2">研发云 / 实验室主机 · 可试</div>'
    '<div class="li"><b>CI、夜间回归、性能报告</b><br>建议式分流，可设置超时与回退</div>'
    '<div class="li"><b>网络服务 · 官方 70–500ms</b><br>实测要加地域、排队、TLS 与限流</div></div>'
    '<div class="col"><div class="h2">手机运行时 / 内核热路径 · 当前不适合</div>'
    '<div class="li"><b>调度、IRQ、DVFS、启动决策</b><br>需要硬实时、本地和确定性路径</div>'
    '<div class="li"><b>离线 / 隐私约束</b><br>用规则或小型本地模型承接</div></div></div>'
    '<div class="note">typed 输出不等于实时、安全或离线可用。</div>'))

slides.append(S("部署边界","隐私、对抗输入和韧性仍由系统负责","运行护栏","隐私、对抗输入和韧性仍由系统负责","TypeSafe 明确 state 可能含有影响答案的误导文本",
    rows([("隐私","脱敏序列号、路径、客户内容；按数据级别审批外发","不允许外发就切本地方案"),
          ("可复现","pin jev-1.13.0；记录输入 schema、模型版本和概率","升级模型重跑评测"),
          ("安全","日志全都视作不可信数据；覆盖注入和错误根因样本","unknown / 人工复核"),
          ("韧性","超时、429、断网、响应异常都走原流程","不阻塞 CI / 刷机")]) +
    '<div class="note">官方称客户请求不用于训练；数据保留、零留存与企业条款仍需按合同核验。</div>'))

slides.append(S("试点方案","先离线回放，再影子运行","最小验证路线","先离线回放，<span class='thin'>再影子运行</span>","首个试点选“CI 失败 owner 建议”或“性能回归排序”，不碰发布自动放行",
    rows([("01 · 盘点","整理近两个发布周期样本，工程师双标代表数据","先确认标签一致性"),
          ("02 · 回放","同一冻结集比较规则、encoder、Jev、通用 LLM","按版本 / 子系统切片"),
          ("03 · 影子","只生成建议，不修改 CI 状态或工单 owner","记录采纳 / 误导 / 不确定"),
          ("04 · 限定上线","仅低风险自动分流；门禁仍走现有策略","保留回滚与审计")]) +
    '<div class="note">先固定语言、日志抽取 schema、阈值和版本，再讨论扩大覆盖。</div>'))

slides.append(S("试点方案","用风险覆盖率决定自动化边界","上线验收","用风险覆盖率决定<span class='thin'>自动化边界</span>","准确率之外，还要衡量严重少数类和错误自动化的代价",
    rows([("Macro F1 / per-class recall","owner 错分会把问题送错团队","subsystem · rare faults"),
          ("ECE / Brier / reliability bins","概率与命中率是否匹配","版本 · 语言 · 问题类型"),
          ("Risk–coverage","自动处理覆盖增加时错误如何变化","按错误成本分层"),
          ("p50 / p95 / cost / retry","在真实地域、负载、限流下测服务链路","输入长度 · 网络地域")]) +
    '<div class="note">测试集按设备 revision、kernel branch、release 阶段、English / 中文拆分，并和现有基线同场比较。</div>'))

slides.append(S("结论","从低风险研发流程开始验证","给 SoC 软件团队的建议","从低风险研发流程开始验证","Jev 可以减少“判断步骤”的成本，但不能替代确定性工程机制",
    '<div class="bigline"><div class="row"><span class="acc">先试</span> CI / VTS 失败分流与性能回归排序</div>'
    '<div class="row">Jev 判断语义，代码计算数值并执行策略</div>'
    '<div class="row">低置信、未知故障、中文弱项、服务超时回到原流程</div>'
    '<div class="row small">只有本域评测优于规则、encoder 与现有流程，才逐步扩大范围</div></div>'))

slides.append(S("资料","来源与结论口径","资料截止 2026-09-26","来源与<span class='thin'>结论口径</span>","官方说法、独立评测、案例作者自测和工程推演不可混为一谈",
    '<div class="two source-columns"><div class="col"><div class="h2">官方 · 模型与边界</div>'
    '<div class="li"><b>TypeSafe 发布文</b><br><small>typesafe.ai/blog/introducing-system-one-models-and-jev</small></div>'
    '<div class="li"><b>Models / Confidence / Jaggedness</b><br><small>docs.typesafe.ai/models · /confidence · /model-jaggedness/jev-1.13</small></div>'
    '<div class="li"><b>API / Quickstart / System One</b><br><small>docs.typesafe.ai/api · /introduction/quickstart · /concepts/system-one</small></div></div>'
    '<div class="col"><div class="h2">案例 · 独立测量 · SoC 工具</div>'
    '<div class="li"><b>skJack/-lip- · 第 30 期 Jev</b><br><small>github.com/skJack/-lip-/tree/main/08-第30期-Jev-不生成文本的决策模型</small></div>'
    '<div class="li"><b>独立评测</b><br><small>github.com/ickma2311/jev-baselines-eval · github.com/statsguysam/jev-classification-benchmark</small></div>'
    '<div class="li"><b>Android / Perfetto</b><br><small>source.android.com/docs/core/tests/vts · perfetto.dev/docs/getting-started/system-tracing</small></div></div></div>'
    '<div class="note">Android / Perfetto 是公开通用工程参考，不代表华为内部工具接口。</div>'))

begin = template.index("<!-- ===== 1 封面")
end = template.index('\n</div>\n<div id="nav-hot">', begin)
deck = template[:begin] + '<!-- Generated slides -->\n' + '\n'.join(slides) + template[end:]
deck = deck.replace('<title>【这里写：系列 · 第 N 期 · 主题】</title>', '<title>Jev × 手机 SoC 软件工程</title>')
extra_css = r"""
.cover .photos{height:310px;background:#fff;border-top:1px solid var(--line);gap:0;padding:24px 100px;align-items:center;justify-content:space-between}
.cover-icon{height:100%;flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;color:var(--muted);font-size:22px;letter-spacing:.04em}
.cover-icon .pxico{width:108px;height:108px}
.pxico{width:32px;height:32px;vertical-align:middle;shape-rendering:crispEdges;image-rendering:pixelated}
.note{margin-top:22px;font-size:22px;color:var(--muted);text-align:center;line-height:1.4}
.note b{color:var(--ink);font-weight:600}
.flow{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;gap:22px;margin-top:42px}
.node{min-width:0;flex:1;background:#fff;padding:46px 30px;border-radius:26px;box-shadow:0 14px 48px rgba(0,0,0,.06);text-align:center}
.node b{display:block;font-size:34px;line-height:1.25}
.node span{display:block;font-size:23px;color:var(--muted);margin-top:14px;line-height:1.4}
.node.accent{background:#E8F0FE;outline:2px solid var(--accent)}
.node.accent b{color:var(--accent)}
.flow-arrow{font-size:48px;color:var(--faint);flex:none}
.rows{flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center;margin-top:36px}
.rowline{display:grid;grid-template-columns:270px 1fr 420px;align-items:center;gap:24px;padding:25px 16px;border-top:1px solid var(--line);font-size:26px;line-height:1.35}
.rowline:last-child{border-bottom:1px solid var(--line)}
.rowline b{font-size:27px}
.rowline span{color:var(--ink)}
.rowline small{font-size:20px;color:var(--muted);text-align:right}
.tbl.left.compact td{font-size:22px;padding:12px 14px}
.tbl.left.compact td:nth-child(2),.tbl.left.compact td:nth-child(3){white-space:normal;color:var(--ink)}
.tbl.left.compact th{font-size:20px}
.tbl.num.compact td{font-size:24px}
.stat .n{font-size:68px}
.stat.text .n{font-size:42px}
.tblwrap .note{font-size:21px;margin-top:24px}
.code pre{font-size:19px;line-height:1.42;white-space:pre-wrap}
.source-columns{gap:54px;margin-top:25px}
.source-columns .li{font-size:20px;padding:9px 0;line-height:1.32}
.source-columns .li small{font-size:15px;color:var(--muted);overflow-wrap:anywhere}
.source-columns .h2{margin-bottom:6px}
.bigline .row{font-size:43px}
.bigline .row.small{font-size:29px}
"""
deck = deck.replace('</style>', extra_css + '\n</style>')
(HERE / "deck.html").write_text(deck, encoding="utf-8")
print(f"Rendered {len(slides)} slides into {HERE / 'deck.html'}")
