"""Leadership/developer briefing: measured advantages, infrastructure and two skills."""
import pathlib,re,json,html,hashlib,shutil
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
# Reuse only data loaders, plotting setup and SVG primitives, without executing the old deck.
ns={'__file__':str(HERE/'build_technical.py')};src=(HERE/'build_technical.py').read_text(encoding='utf-8');exec(compile(src[:src.index("add('问题与计算'")],str(HERE/'build_technical.py'),'exec'),ns)
for key in ['txt','box','arrow','group','rect','path','foot','add','plt','savefig','BLUE','INK','GRAY','DEFS','USED'] :globals()[key]=ns[key]
slides=ns['slides'];notes=ns['notes'];plan=ns['plan'];E=html.escape
old=(HERE/'deck-technical-28.html').read_text(encoding='utf-8')
USED.update(ROOT/n for n in ['docs/Jev实验主线与9B分类收益解读_20261018.md','research/decision-localization-20261011/report.md','research/jev-qwen35-9b-20261016/REPORT.md','docs/首诊断弱标签RCU子串误判审计_20261018.md','research/pplx-timeshare-20261012/results/pplx-runtime.json','research/pplx-timeshare-20261012/results/statistics.json','research/pplx-decider-20261011/results/statistics.json'])
sections=re.findall(r'<section class="slide.*?</section>',old,re.S)
def reuse(n,title,sub,note,sec='模型与接口'):
    s=sections[n-1];svg=re.search(r'<div class="art">(.*?)</div>',s,re.S).group(1)
    body=re.sub(r'^<svg[^>]*>|</svg>$','',svg)
    # Editorial wording is positive; retain the correct first-token computation.
    body=body.replace('不能断言“单字母Chat必比Decision多一次模型前向”；剩余差异需从实际执行与调度测量。','同一骨干、同一输入前向；Decision直接返回候选分布，Chat输出答案内容。')
    body=body.replace('机制示意，不是时长比例；通用Decision没有自动变成专有Jev架构。','机制示意：展示输入与输出职责；方框宽度不代表实测时长。')
    f=re.search(r'class="walk-data">(.*?)</script>',s,re.S);steps=json.loads(f.group(1)) if f else None
    add(sec,title,sub,body,note,source='项目实测与执行源码 · 开发者简报',steps=steps)

# Plan is declared before writing the final HTML.
titles=['把模型判断变成软件可调用的概率接口','同一份证据，直接得到可编排的选择结果','适合把重复判断接入Agent工作流','从文本生成，转为类型化概率读出','共用输入计算，按应用选择返回方式','四任务八步预热：完成时间减少7.7%–11.0%','PPLX对照说明：显卡与推理引擎共同决定体验','部署预算包含权重、激活、KV和状态池','用状态池与运行指标支撑四任务并发','用LoRA适配9B：训练约531万参数','先审核标签，再冻结机制分组与数据版本','一条训练样本：输入、候选和target分开','参考微调：396微步、99次更新','RLCD把选项分布转为监督更新信号','两份skill，覆盖数据到模型服务','从可调用模型，到可复现的开发交付']
(HERE/'说明.md').write_text('# Jev开发者与管理层简报\n\n16页，建议15–20分钟。面向模型能力、实测效率、资源投入与开发路线。训练命令、标签规则和验收细节放入两份skill。\n\n|页|结论|\n|---:|---|\n'+'\n'.join(f'|{i}|{t}|' for i,t in enumerate(titles,1))+'\n\n3/4/5/14页有教学步动画；P播放，J/K走步，离页停止。实测效率限定为相同权重、单字母Chat、四任务八步预热、每格5次。PPLX两轮放置数据与同GPU跨引擎对照分别标注。详细证据入口在资料来源，不在正文逐条讲审计与历史失败。\n',encoding='utf-8')
add('价值与应用',titles[0],'Jev-like Decision：将有限判断接入业务代码与定位Agent。',
    txt(55,130,'输入证据',66,INK,600)+arrow(380,110,490,110)+txt(550,130,'候选概率',66,BLUE,600)+arrow(930,110,1040,110)+txt(1100,130,'软件动作',66,INK,600)+box(55,290,450,170,'可直接编排',['选择、排序、条件分支'])+box(575,290,450,170,'有实测依据',['效率与资源配置分别记录'],True)+box(1095,290,450,170,'开发路径明确',['数据 → LoRA → 服务 → 验收']),
    '这份简报介绍本地已实现的Jev-like概率接口及开发方法。应用价值是把明确候选下的判断变成可编排结果，围绕接口收益、推理基础设施和可复现微调展开。')
add('价值与应用',titles[1],'接口示例：输入日志、问题与候选，返回有限分布。',
    box(40,50,700,350,'输入：证据 + 问题 + 候选',['日志：KASAN use-after-free（合成）','问题：第一诊断属于什么家族？','候选：生命周期 / 锁 / RCU','模型读取证据，完成选择'],True,size=31)+arrow(760,225,825,225)+box(845,50,710,350,'输出：程序可读取的结果',['choice: memory_lifetime','生命周期0.90 / 锁0.06 / RCU0.04','业务代码据此路由工具或后续调查','示意概率，不是一次真实调用'],size=27),
    '这里的0.90、0.06、0.04只是合同示例，不是保存的实测概率。软件无需从长解释中提取类别。候选由业务定义，输出格式是有限概率结果。')
add('价值与应用',titles[2],'明确候选的判断交给Decision，证据调查与报告由Agent继续完成。',
    box(40,70,420,190,'输入材料',['日志 / 源码 / 编译产物','工具提取任务所需证据'],size=31)+arrow(480,165,550,165)+box(570,70,440,190,'Decision选择',['首诊断家族 / 候选排序','供程序分支与工具路由使用'],True,size=31)+arrow(1030,165,1100,165)+box(1120,70,440,190,'后续Agent',['读源码 / 符号化 / 比对','形成带引用的分析报告'],size=31)+txt(60,410,'开发者把候选、工具和验证器编排成完整应用。',40,BLUE,600),
    '本项目训练监督为首诊断choice。阶段、组件、工具排序可以作为接口应用设计，但应按各自任务准备样本与标签，不将一种分类能力自动等同全部定位能力。')
reuse(3,titles[3],'长答案节省解码工作；Decision直接提供所有候选的分数。','重点比较输入前向与输出职责。单字母Chat的首字母也可来自prefill；使用Decision的直接收益是有限概率契约与减少文本生成/解析，实际时延由下一页固定条件数据说明。')
reuse(4,titles[4],'输入prefill产生隐藏状态与KV；Decision读出分布，Chat返回内容。','这张图说明两条返回路径共有输入计算，不将所有加速归因于少一次完整模型前向。按场景选择接口：有限判断用概率分布，开放式解释用Chat。')
fig,axs=plt.subplots(1,2,figsize=(16,5),layout='constrained')
for ax,(name,a,b) in zip(axs,[('27B · 四任务×八步 · 预热',3.634,4.085),('微调9B · 四任务×八步 · 预热',1.2802849046,1.3876212164)]):
    ax.bar(['Decision','单字母Chat'],[a,b],color=[BLUE,'#AAB2BD'],width=.5);ax.set_ylim(0,max(a,b)*1.34);ax.set_ylabel('整批完成时间 / 秒');ax.set_title(name,pad=22)
    for i,v in enumerate([a,b]):ax.text(i,v+max(a,b)*.04,f'{v:.3f}s',ha='center',fontsize=23)
    ax.text(.5,.92,f'耗时减少 {(b-a)/b*100:.1f}%',ha='center',transform=ax.transAxes,color=BLUE,fontsize=21)
savefig(fig,'简报_实测效率')
add('性能与基础设施',titles[5],'同权重、相同prompt · 对照Chat关闭thinking且仅生成1token · 每格5次均值。','',
    '两图是独立27B和9B实验，均为四个任务同时发起、每任务八步顺序决策、题干预热、选项变化。整批最后完成时间分别减少约11.0%和7.7%。单次Decision测完整概率可用，Chat另记首个非空内容，不把此图改称长篇报告提速。只展示明确条件下的效率收益，不做跨模型纯尺寸归因。',source='27B / 9B冻结并发实测 · 四任务×八步预热',figure='简报_实测效率')
add('性能与基础设施',titles[6],'同一A100 80GB上的已测配置；PPLX BF16权重本身占48.59GiB。',
    box(35,50,490,360,'放置方式决定传输成本',['PPLX CPU卸载：19.455s','PPLX全GPU：5.672s','两轮独立测量；同为参考实现','GPU驻留减少跨设备搬运'],True,size=27)+box(555,50,490,360,'引擎决定服务效率',['同轮全GPU通用SGLang：2.563s','同轮全GPU PPLX参考：5.672s','两端均9/9唯一test案例匹配','内核、批处理、读出均需适配'],size=26)+box(1075,50,490,360,'资源决定可部署范围',['PPLX权重：48.59GiB BF16','还需KV / 状态 / 工作空间','本项目验证卡：A100 80GB','按上下文与并发留运行余量'],size=27),
    'PPLX展示推理基础设施的重要性。CPU卸载与全GPU是不同轮次的放置测量，不能只按倍数宣称纯硬件因果收益。同轮对照两端test均9个唯一案例各重复3次正确；PPLX仍为参考Transformers路径，通用模型使用SGLang，所以2.563对5.672体现实际部署栈差异。48.59GiB是PPLX参数字节，不是服务总显存；80GB为已验证硬件，不声称所有配置的最低门槛。',source='PPLX两轮部署与全GPU分时对照 · runtime参数设备记录')
add('性能与基础设施',titles[7],'按训练与推理分别预算，显卡容量服务于模型、上下文和并发。',
    txt(45,85,'显存预算 = 权重 + 激活 + KV + 状态 + 工作空间',40,BLUE,600)+box(45,175,730,270,'9B LoRA训练 · 本轮实测',['可训练参数：5,308,416','torch allocated峰值：18.74GiB','保留完整BF16预训练骨干','另预留驱动、workspace与导出空间'],size=30)+box(825,175,730,270,'9B服务 · 本轮配置',['SGLang static比例0.55 / 32状态槽','NVML resident约47.5GiB','上下文8k用于接口性能，32k用于完整Agent','本项目在A100 80GB完成验证'],size=28),
    '训练allocated峰值不等于部署resident，更不是最小显卡承诺。LoRA只减少要更新的参数，不会只加载适配器。推理的静态池、上下文和并发决定预分配量；开发者应记录每种配置的实际显存与吞吐。')
add('性能与基础设施',titles[8],'正式隔离实例：32个线性状态槽，确认有效并发4。',
    box(40,95,450,220,'配置容量',['max-running-requests=4','max-mamba-cache-size=32','静态池与上下文同时规划'],True,size=31)+arrow(510,205,575,205)+box(595,95,450,220,'确认实际调度',['从启动日志读取有效上限','检查scheduler实际批次','避免只按CLI推断容量'],size=31)+arrow(1065,205,1120,205)+box(1140,95,420,220,'记录服务指标',['请求排队 / prefill','KV / 状态 / GPU显存','TTFT / 完整概率响应'],size=29),
    '原27B正式实验配置32状态槽，并确认有效上限和实际最大批次为4。并发服务不仅要设请求上限，还要分配状态容量并观测实际调度。资源监控让模型能力稳定交付到应用。')
reuse(17,titles[9],'rank8 / alpha16 · 48处投影 · 约占总参数0.056%。','复用预训练Qwen3.5-9B骨干，只在32个down_proj和8+8个q/v_proj上训练LoRA。现有LM字母读出保留。A随机、B初始零；有效权重W+2BA，合并后用标准模型架构部署。','开发与微调')
add('开发与微调',titles[10],'数据skill将审核后的样本导出为可训练的新版本。',
    ''.join(group(i,box(35+(i%3)*520,40+(i//3)*255,490,190,a,b,i==2,size=28)) for i,(a,b) in enumerate([('定义任务与标签',['明确第一诊断，而非注入名称','记录证据片段与审核者']),('脱敏与输入选择',['日志窗口只保留任务证据','不拼入case / split / gold']),('按机制冻结划分',['跨内核近似机制归同组','train / dev / test不交叉']),('校验与类别盘点',['检查重复、标签边界、缺类','生成validation与输入哈希']),('训练时扩增候选',['5 / 8 / 12候选随机排列','target随正确项位置更新']),('交付给训练skill',['private文本保留本地','public清单记录哈希和支持数'])])),
    '数据准备的操作规范和实际校验脚本在数据skill中。标签先审核，机制分组先于候选扩增；训练输入只有证据、问题和候选，清单字段留给训练器和评测器。',steps=['定义可审核的标签语义','脱敏后确定模型可见窗口','按机制分组冻结三个集合','校验重复与类别覆盖','扩增候选并交付带哈希的数据版本'])
reuse(15,titles[11],'JSONL样本由证据、候选问题和人工标签组成；标注格式见数据skill。','此页为合成格式示例。模型看到日志窗口和选项，训练器保留正确标签；当前排列C对应target2。开发者应使用真实审核数据，不用演示样例声称能力。','开发与微调')
add('开发与微调',titles[12],'本轮：33条训练案例，每轮4种候选构造，训练3轮。',
    box(35,65,490,265,'训练骨干适配',['48处rank8 LoRA','BF16骨干 / FP32适配器','AdamW lr=1e−4','累计4微步更新一次'],True,size=31)+box(555,65,490,265,'目标与更新',['第0轮：交叉熵CE','第1–2轮：CE + RLCD','396个微步 / 99次更新','逐步记录loss / 时间 / 显存'],size=30)+box(1075,65,490,265,'验证与模型交付',['用独立dev选择epoch','保存适配器、合并BF16模型','记录模型与脚本SHA','SGLang启动后做接口验收'],size=29)+txt(55,455,'新数据N条train：参考日程产生12N微步、3N次更新。',34,BLUE,600),
    '33案例是历史参考规模，不是推荐训练样本上限。新训练采用审核标签并充分准备开发集。skill计划会按新train数量计算微步与更新预算，支持CE-only同预算对照。训练命令、合并与服务验收均放在复现文档。')
reuse(19,titles[13],'训练输入为可微logits、正确索引与扰动幅度；完整计算与代码见微调skill。','选项概率在训练内部由logits加扰动后归一化，结合真标签形成reward和优势。损失通过logdensity项与CE回到LoRA；普通HTTP概率JSON不是直接反传入口。公式细节和停止梯度说明见skill复现指导。','开发与微调')
links='<div class="doc-links"><a href="../../skills/ai4loc-decision-data/SKILL.md">打开数据准备skill ↗</a><a href="../../skills/ai4loc-decision-finetune/SKILL.md">打开微调部署skill ↗</a><a href="../../docs/决策模型开发与微调复现指南_20261018.md">完整复现指导 ↗</a></div>'
add('开发交付',titles[14],'执行细节独立交付，slide只介绍开发路线与成果。',
    box(40,45,730,370,'Skill 1 · 数据准备与标签',['reviewed JSONL → 检查 → 冻结run','字段、证据、审核者与机制分组','跨集合去重、标签边界校验','输出private / frozen / validation'],True,size=31)+box(830,45,730,370,'Skill 2 · 微调与服务验收',['训练计划 → GPU执行 → 合并','CE / CE+RLCD同预算训练入口','独立SGLang启动与API探针','评测、哈希与资源记录'],size=31),
    '两份skill可随项目分发，也可安装到Codex个人skills目录。默认训练命令只生成计划，不下载权重、不占GPU；开发者明确执行训练时才增加--execute。全套复现命令在引用文档，台上不用逐行讲命令。')
slides[-1]=slides[-1].replace('</section>',links+'</section>')
add('开发交付',titles[15],'模型接口 + 推理基础设施 + 审核数据 + 可执行流程。',
    txt(65,70,'分类：9B从66/87提高至78/87（原冻结首诊断标签）',36,BLUE,600)+txt(65,170,'效率：八步预热下，整批完成时间减少7.7%–11.0%',39,BLUE,600)+txt(65,270,'资源：PPLX权重48.59GiB，GPU驻留与执行引擎共同影响时延',35,INK,600)+txt(65,370,'开发：审核标签 → LoRA训练 → 合并服务 → 独立验收',39,INK,600)+txt(65,475,'完整步骤、样本合同、脚本与实测来源：见配套文档。',30,GRAY),
    '这份简报以明确场景下的实测收益和资源条件帮助做技术选择。开发者可从两份skill开始，用自有审核数据形成可复现模型交付。完整定位仍由证据工具与Agent工作流完成，不把有限分类数字当成所有根因场景的承诺。')
# Connect the chronological studies and restore the frozen classification gain.
add('实验主线','先验证接口，再优化部署，最后用任务数据适配9B','四轮实验各回答一个问题，结果使用各自对照，不跨轮混算。',
    ''.join(group(i,box(35+(i%2)*790,35+(i//2)*240,740,190,a,b,i==3,size=29)) for i,(a,b) in enumerate([
      ('① 通用27B：接口有没有价值？',['Decision直接给概率；Chat输出文本','结构化三问：1.145s 对 2.075s']),
      ('② PPLX：专用权重要怎样交付？',['CPU卸载 → 全GPU；再看引擎适配','全GPU同轮：PPLX 5.672s / 通用2.563s']),
      ('③ 严格限输出：优势还剩多少？',['Chat关闭思考、只输出一个字母','四任务八步预热：27B减少11.0%耗时']),
      ('④ 同一9B：微调能学到任务吗？',['同样本、同SGLang、微调前后对照','分类66/87 → 78/87；另测接口与Agent'])])),
    '把四轮看作一条工程验证链。第一轮比较软件需要的三项结构化回答，文本输出较长；第三轮把Chat压缩到单字母，以检验最强轻量基线。因此44.8%与11.0%不是互相矛盾，也不能相加。PPLX验证了真实专用权重的部署与资源需求，促使后续9B实验统一执行引擎。9B再固定基座与输入，观察任务适配后的分类收益。四轮没有共同的独立盲测集，不构成一个巨大的交叉消融。',
    source='10月11日接口 / 12日PPLX / 16日并发与9B',steps=['先回答接口能提供什么','确认专用权重需要的部署资源','把Chat压缩至单字母再比较','同9B训练前后验证任务适配'])
add('开发与微调','历史微调把124条日志变成三套独立用途的数据','两种内核构建；按机制分组后，再构造选项排列。',
    box(35,60,490,290,'训练集：33条',['模型读取日志、问题与候选','训练器保存正确类别','每条每轮4种候选构造','3轮，共396微步 / 99次更新'],True,size=31)+box(555,60,490,290,'开发集：4条',['用于选择保存的epoch','不参与梯度更新','选定后导出合并BF16权重','新数据应扩大审核与类别覆盖'],size=31)+box(1075,60,490,290,'测试集：87条',['固定模型后评估','每例3种选项排列，多数票','Decision与Chat分别统计','87条仍是87个案例'],size=31)+foot('旧分类采用原冻结首诊断弱标签；新skill要求审核数据。不是提交或根因金标。'),
    '小白可以把三个集合理解为练习题、选版本的小考、最后评分的考卷。训练33条，开发4条，测试87条；124条来自stability和OpenHarmony构建。先按机制隔离，再做候选排列，不能把同一个故障换字母就当独立新题。旧标签由规则生成，新skill增加证据、审核者与边界校验。旧成绩保留原分母，标签已知问题见专门审计文档，不偷偷改标或改分。',source='9B dataset-frozen.json / training-protocol.json')
summ=ns['summ'];acc=summ['accuracy']
fig,axs=plt.subplots(1,3,figsize=(16,5),layout='constrained')
for ax,source,label in zip(axs,['all','stability','openharmony'],['全部测试案例','stability构建','OpenHarmony构建']):
    rows=[next(x for x in acc if x['api']=='decision' and x['source']==source and x['checkpoint']==c) for c in ['base','trained']]
    vals=[100*r['accuracy'] for r in rows]
    ax.bar(['基座9B','微调9B'],vals,width=.52,color=['#AAB2BD',BLUE]);ax.set_ylim(0,132);ax.set_yticks([0,25,50,75,100]);ax.set_ylabel('首诊断分类标签一致性 / %');ax.set_title(label,pad=18)
    for i,(v,r) in enumerate(zip(vals,rows)):ax.text(i,v+3,f"{v:.2f}%\n{r['correct']}/{r['cases']}",ha='center',fontsize=21)
    ax.text(.5,.95,f'+{vals[1]-vals[0]:.2f} 个百分点',ha='center',transform=ax.transAxes,color=BLUE,fontsize=20)
savefig(fig,'简报_9B分类收益')
add('实测收益','9B任务微调：分类从75.86%提高到89.66%','相同87例、相同12类、每例3排列多数票 · 原冻结首诊断标签。','',
    '这是原实验的重要正向结果：基座66/87，微调78/87，净增加12个匹配案例，即13.79个百分点，两个构建分组也都提高。这里展示Decision；关闭thinking的单字母Chat在同两权重上也分别66和78，所以收益来自本次微调方案，不能归给Decision接口。主要增益在显式warning/panic类，8/20到19/20。旧标签含4条已知规则误标，原成绩是对冻结标签的一致性；没有变成专家根因真值。20机制簇区间触及零，不声称新机制显著性。此轮整体微调未单独分离RLCD贡献。',source='9B summary.json · 87案例 / 20机制组 · 原标签审计见配套文档',figure='简报_9B分类收益')
add('实测收益','分类接入Agent后，用工具继续核对源码证据','独立32k流程检查：同三例、同工具、两种权重；两侧均完成报告。',
    group(0,box(40,45,480,200,'先定界',['Decision选择首诊断家族','给后续调查一条可质疑线索'],True,size=31))+arrow(540,145,585,145)+group(1,box(605,45,440,200,'再调查',['Chat读源码、核对符号','保留证据与工具轨迹'],size=31))+arrow(1065,145,1110,145)+group(2,box(1130,45,430,200,'交报告',['输出候选位置与引用','源码命中：均为2/3'],size=31))+
    group(3,box(40,295,730,175,'混合流程：微调前 → 微调后',['模型HTTP：10 → 6 次','三例总耗时：53.464 → 29.247s'],True,size=30))+group(3,box(830,295,730,175,'同轮纯Chat作为完整对照',['微调后：3 HTTP / 23.229s / 2/3命中','按完整流程选方案，接口与根因指标分开'],size=29)),
    '三例是UAF、ABBA锁、hung task。混合流程在微调后少了4次模型HTTP，总时间由53.464降至29.247秒，源码位置命中仍2/3。纯Chat同期23.229秒，也2/3，因此工程上仍需按具体流程比较，不能把首诊断提升等同根因提升。这里保留完整对照帮助决定何时使用概率路由，数值仅来自这三例固定顺序检查，不作为跨项目普遍提速。',source='agent32k/tables · 同修复客户端 / 相同工具 / 三例检查',steps=['定界产生调查线索','调用工具核对源码','输出可检查的位置与引用','比较整个流程的调用与时间'])
assert len(slides)==20
# Reorder by explanation: contract -> experimental questions -> runtime -> data -> training -> gains -> delivery.
order=[1,2,3,17,4,5,6,7,8,9,10,18,11,12,13,14,19,20,15,16]
oldslides=slides.copy();oldnotes=notes.copy();oldplan=plan.copy()
slides[:]=[];notes[:]=[];plan[:]=[]
for n,idx in enumerate(order,1):
    slides.append(re.sub(r'<b>\d+</b>',f'<b>{n:02d}</b>',oldslides[idx-1],count=1))
    notes.append(re.sub(r'^## \d+',f'## {n:02d}',oldnotes[idx-1]))
    row=oldplan[idx-1];plan.append((n,*row[1:]))
active_diagrams=[]
for n,sec in enumerate(slides,1):
    m=re.search(r'<div class="art">(<svg.*?</svg>)</div>',sec,re.S)
    if not m:continue
    name=f'diagram-{n:02d}.svg';active_diagrams.append(name)
    svg=m.group(1).replace('<svg class="sv"','<svg style="font-family:Microsoft YaHei,sans-serif"');pos=svg.index('>')+1
    (HERE/'media'/name).write_text(svg[:pos]+DEFS+svg[pos:],encoding='utf-8')
(HERE/'active-diagrams.json').write_text(json.dumps(active_diagrams,indent=2),encoding='utf-8')
(HERE/'说明.md').write_text('# Jev实验与开发路线简报\n\n20页，建议20–25分钟。主线：接口契约 → 四轮实验 → 推理基础设施 → 数据与微调 → 分类与Agent结果 → 复现skill。\n\n|页|内容|\n|---:|---|\n'+'\n'.join(f'|{n}|{t}|' for n,sec,t,fig in plan)+'\n\n分步动画：4/5/6/13/16/18页。P播放暂停，J/K走步，离页停止。9B分类采用原冻结首诊断标签；不是根因或提交准确率。完整说明见实验主线文档。\n',encoding='utf-8')

template=(ROOT/'tools/kelip-slide/assets/deck-template.html').read_text(encoding='utf-8');a=template.index('<!-- ===== 1 ');b=template.index('<div id="nav-hot"');template=template[:a]+'\n'.join(slides)+'\n</div>\n'+template[b:]
template=template.replace('【这里写：系列 · 第 N 期 · 主题】','Jev-like决策模型：价值、基础设施与开发路径').replace('"PingFang SC","SF Pro Display"','"PingFang SC","Microsoft YaHei","SF Pro Display"')
css=re.search(r"css='''(.*?)'''",src,re.S).group(1)+'\n.doc-links{display:flex;gap:25px;margin-top:16px;font-size:25px}.doc-links a{color:var(--accent)}'
template=template.replace('</style>',css+'\n</style>');a=template.index('  // ---- 分步动画：');b=template.index('  const navBtn=',a);template=template[:a]+(HERE/'animation.js').read_text(encoding='utf-8')+template[b:]
template=template.replace("if(e.target.closest('a,#nav-panel,#nav-btn,#nav-hot'))","if(e.target.closest('a,button,.walk-controls,#nav-panel,#nav-btn,#nav-hot'))").replace("else if(e.key==='g'||e.key==='G')","else if(e.key==='p'||e.key==='P'){if(anim)anim.toggle();}\n    else if(e.key==='g'||e.key==='G')")
template=template.replace("addEventListener('keydown',e=>{","addEventListener('keydown',e=>{\n    if(e.target.closest('button')&&[' ','Enter'].includes(e.key))return;")
(HERE/'deck.html').write_text(template,encoding='utf-8');(HERE/'逐页讲稿.md').write_text('# 决策模型开发简报逐页讲稿\n\n20页，建议20–25分钟。分类收益和接口效率分别阅读。具体训练操作见两份skill和完整复现指南。\n\n'+'\n'.join(notes),encoding='utf-8')
(HERE/'source-provenance.json').write_text(json.dumps({'edition':'experiment-story-20','date':'2026-10-18','new_model_calls':0,'sources':[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(USED)],'measurement_scope':'warm4x8 n5 per arm; PPLX placement rounds and same-GPU cross-runtime comparison separately labelled'},ensure_ascii=False,indent=2),encoding='utf-8')
for p in USED:
    dst=HERE/'evidence'/p.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
print('BRIEF_READY',len(slides))
