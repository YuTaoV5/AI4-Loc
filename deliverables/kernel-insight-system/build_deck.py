#!/usr/bin/env python3
"""Build the offline Kelip deck and research figures from frozen project evidence."""
import csv
import hashlib
import html
import json
import pathlib
import re
from collections import Counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy.stats import beta, binomtest
import research_figures
import deck_revision

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MEDIA = HERE / 'media'
MEDIA.mkdir(exist_ok=True)
INK, GRAY, BLUE, LIGHT = '#1D1D1F', '#6E6E73', '#0071E3', '#D2D2D7'
FONT = pathlib.Path('C:/Windows/Fonts/msyh.ttc')
if FONT.exists():
    font_manager.fontManager.addfont(str(FONT))
    plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(FONT)).get_name()
plt.rcParams.update({'font.size': 19, 'axes.spines.top': False,
    'axes.spines.right': False, 'axes.spines.left': False,
    'axes.edgecolor': LIGHT, 'text.color': INK, 'axes.labelcolor': GRAY,
    'xtick.color': GRAY, 'ytick.color': INK, 'svg.fonttype': 'path',
    'figure.facecolor': 'white', 'axes.facecolor': 'white', 'axes.unicode_minus': False})

def source_file(rel):
    """Prefer the public frozen report evidence shipped alongside the deck."""
    snapshot=HERE/'evidence'/rel
    return snapshot if snapshot.is_file() else ROOT/rel

def read(rel):
    return json.loads(source_file(rel).read_text(encoding='utf-8-sig'))

source_paths = {
    'S1': 'docs/SYSTEM_DESIGN.md',
    'S2': 'docs/project-data-inventory-20261007.json',
    'S3': 'docs/agent-iteration-20261007.json',
    'S4': 'docs/kernel-localization-benchmark-20261007.json',
    'S5': 'docs/website-acceptance-20261007.json',
    'S6': 'data/datasets/stability-v1/manifest.json',
    'S7': 'data/datasets/stability-v1/cases/corrupt_uaf_kmalloc/ground-truth.json',
    'S8': 'data/datasets/stability-v1/cases/pressure_oom/ground-truth.json',
}
sources = {k: {'path': v, 'sha256': hashlib.sha256(source_file(v).read_bytes()).hexdigest(),
              'reportEvidence': str(source_file(v).relative_to(HERE)).replace('\\','/') if source_file(v).is_relative_to(HERE) else None}
           for k,v in source_paths.items()}
iteration, inventory, manifest = read(source_paths['S3']), read(source_paths['S2']), read(source_paths['S6'])
history = read(source_paths['S4'])
ready = [c for c in manifest['cases'] if c['status'] == 'ready']
family = Counter(c['family'] for c in ready)
pairs = iteration['pairedRuns']
labels = ['UAF', '内存泄漏', '锁顺序', '原子态睡眠', 'OOM', '健康基线']
ci = lambda k,n: [float(beta.ppf(.025,k,n-k+1)) if k else 0.0,
                  float(beta.ppf(.975,k+1,n-k)) if k<n else 1.0]
counts = {}
for side in ['before','after']:
    ms = [p[side]['metrics'] for p in pairs]
    req = [r for m in ms for r in m['requests']]
    counts[side] = {k: sum(m[k] for m in ms) for k in
        ['modelRequests','toolCalls','preflightToolCalls','modelToolCalls']}
    counts[side].update({'localizationSeconds': sum(m['localizationSeconds'] for m in ms),
        'observedPromptTokens': sum(r.get('usage',{}).get('promptTokens',0) for r in req),
        'observedOutputTokens': sum(r.get('usage',{}).get('outputTokens',0) for r in req),
        'requestsWithUsage': sum('usage' in r for r in req)})
assert len(ready)==60 and len(manifest['cases'])==68
assert counts['before']['modelRequests']==21 and counts['after']['modelRequests']==6
assert abs(counts['before']['localizationSeconds']-181.347)<1e-6
assert abs(counts['after']['localizationSeconds']-95.834)<1e-6
analysis = {'schema': 'kernel-insight-deck-evidence/v1', 'date': '2026-10-07',
    'sources': sources, 'dataset': {'versions': inventory['datasets'], 'readyFamilies': dict(family),
        'build': manifest['build'], 'ready': len(ready), 'excluded': 8},
    'paired': pairs, 'aggregates': counts, 'reported': {k: iteration[k] for k in ['before','after','improvement']},
    'extra': [{'caseId': r['caseId'], 'split': r['split'], 'hit': r['scores']['codeLocationHit'],
        'requests': r['metrics']['modelRequests'], 'seconds': r['metrics']['localizationSeconds']}
        for r in iteration['holdout']['runs']],
    'uncertainty': {'method': 'two-sided exact binomial Clopper-Pearson, alpha=.05',
        'before3of5': ci(3,5), 'after5of5': ci(5,5), 'extra2of3': ci(2,3),
        'pairedExactMcNemarP': float(binomtest(2,2,.5).pvalue),
        'assumption': 'IID/exchangeability is not established; intervals illustrate small-sample uncertainty.'},
    'limitations': iteration['limitations'],
    'newModelExperimentsExecuted': False}
(HERE/'analysis-data.json').write_text(json.dumps(analysis,ensure_ascii=False,indent=2),encoding='utf-8')
with (HERE/'paired-results.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['case','side','status','code_hit','model_requests','automatic_tools','model_tools','seconds'])
    for p in pairs:
        for side in ['before','after']:
            r=p[side];m=r['metrics'];w.writerow([p['caseId'],side,r['status'],r['codeLocationHit'],m['modelRequests'],m['preflightToolCalls'],m['modelToolCalls'],m['localizationSeconds']])
with (HERE/'dataset-coverage.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['family','ready_cases']);w.writerows(family.items())

def savefig(name,fig):
    fig.savefig(MEDIA/f'{name}.svg',bbox_inches=None)
    fig.savefig(MEDIA/f'{name}.png',dpi=140)
    plt.close(fig)

def clean(ax):
    ax.set_axisbelow(True);ax.grid(axis='x',color='#E9E9ED',linewidth=1)
    ax.tick_params(axis='both',length=0,pad=12)

# All chart values are frozen observations, with no invented variance.
names={'protection':'保护 / 非法访问','refcount':'引用计数','memory_uaf':'释放后使用','usercopy':'用户态拷贝',
       'memory_leak':'内存泄漏','memory_oob':'内存越界','watchdog':'看门狗','lock_order':'锁顺序',
       'atomic_sleep':'原子态睡眠','hung_task':'任务挂起','rcu_stall':'RCU 停滞','oom':'OOM','healthy':'健康基线'}
research_figures.build(MEDIA, pairs, family, counts, ci, labels, names)

E=html.escape
def text(x,y,s,size=30,color=INK,weight=400,anchor='start',mono=False):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}"'+(' class="mono"' if mono else '')+f'>{E(str(s))}</text>'
def rect(x,y,w,h,accent=False,dash=False):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="'+('#E8F0FE' if accent else '#F5F5F7')+f'" stroke="{BLUE if accent else LIGHT}" stroke-width="{2 if accent or dash else 0}"'+(' stroke-dasharray="8 6"' if dash else '')+'/>'
def box(x,y,w,h,title,lines=(),accent=False,dash=False):
    z=rect(x,y,w,h,accent,dash)+text(x+28,y+52,title,32,BLUE if accent else INK,600)
    for i,line in enumerate(lines):z+=text(x+28,y+99+i*38,line,25,GRAY)
    return z
def arrow(x1,y1,x2,y2,accent=False):
    return f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{BLUE if accent else "#8E8E93"}" stroke-width="3" marker-end="url(#{"arB" if accent else "ar"})"/>'
def svg(inner,vh=600):
    return f'<div class="diagbox pad"><svg class="sv" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 {vh}" preserveAspectRatio="xMidYMid meet">{inner}</svg></div>'
def table(headers,rows,cls='left wrap',high=None):
    return '<div class="tblwrap"><table class="tbl '+cls+'"><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr'+(' class="hi"' if i==high else '')+'>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for i,row in enumerate(rows))+'</tbody></table></div>'
def stats(items):
    return '<div class="stats'+(' two' if len(items) in [2,4] else '')+'">'+''.join(f'<div class="stat {"dim" if i else ""}"><div class="n">{n}</div><div class="l">{l}</div></div>' for i,(n,l) in enumerate(items))+'</div>'
def fig(name,alt):
    return f'<div class="fig card"><img src="media/{name}.svg" alt="{E(alt)}"></div>'
def two(left,right):
    return '<div class="two">'+''.join('<div class="col"><div class="h2">'+title+'</div>'+''.join('<div class="li">'+t+'</div>' for t in lines)+'</div>' for title,lines in [left,right])+'</div>'
slides=[];notes=[]
def add(sec,title,body,sub='',src='S1 · 系统方案',note='',kind=''):
    i=len(slides)+1
    slides.append(f'<section class="slide {kind}" data-sec="{E(sec)}" data-title="{E(re.sub("<[^>]*>","",title))}"><div class="kicker"><b>{i:02d}</b>{E(sec)} · {E(src)}</div><h1>{title}</h1>'+ (f'<div class="sub">{sub}</div>' if sub else '')+body+'</section>')
    notes.append(f'## {i:02d} {re.sub("<[^>]*>","",title)}\n\n{note}\n\n来源：{src}。\n')

A='摘要与背景';D='数据与方法';I='系统实现';R='实验结果';C='讨论与结论'
# 01–08: abstract, introduction, and theoretical framing.
cover=box(20,150,430,240,'日志 · 源码 · 编译产物',['保留原始故障现场','允许材料缺失'])+arrow(475,270,560,270)+box(590,150,420,240,'有界工具 Agent',['先定界，再定位','每一步都有证据'],True)+arrow(1035,270,1120,270)+box(1150,150,430,240,'可审核的代码候选',['位置 / 证据 / 缺口','机制复核与失败回归'])+text(800,495,'Kernel Insight  ·  系统设计与实证分析',28,GRAY,anchor='middle')
add(A,'从故障现场到<span class="acc">有证据的定位</span>',svg(cover),'面向 Linux / OpenHarmony 内核 · 论文式系统报告 · 2026-10-07','项目设计 + 冻结实验',
    '研究对象是日志、源码和构建产物条件不完备时的内核故障定位。系统输出定界结果及证据支持的代码候选，保留人工审核入口。本报告不是自动根因证明已经完成的声明。数据来自现有项目记录，未为本报告新跑模型。')
add(A,'摘要：一次小样本迭代，同时改善三项指标',stats([('3/5 → 5/5','故障代码位置命中<br>固定 5 个故障；另含 1 个健康基线'),('21 → 6','六例实际模型请求<br>减少 71.4%；含失败与格式修复'),('181 → 96 s','六例定位总时间<br>精确值 181.347 → 95.834 秒')]),'结论适用于固定六例试验；机制准确率与引入提交准确率仍为未知。','S3 · 配对迭代',
    '前后都使用日志加源码，模型和预算相同。代码准确率只计算五个故障，失败留在分母；请求和时间汇总包括健康样本。v10 的 5/5 不代表全量 60 个有效样本，更不代表生产环境准确率。rootCauseAccuracy=null。')
add(A,'研究问题与实现形成一一对应',table(['研究问题','系统选择','可验证证据'],[
    ['RQ1：怎样让候选位置可审核？','材料身份门禁 + 读取范围约束','输入哈希、工具轨迹、文件 / 函数 / 行号'],
    ['RQ2：怎样减少重复模型交互？','首诊断预检 + 日志引导源码预检','同条件配对的请求数与定位耗时'],
    ['RQ3：缺材料时怎样保持诚实？','按材料开放工具，输出缺口或拒答','七种输入视图；历史缺失实验'],
    ['工程贡献：怎样持续迭代？','封版数据 + 独立评分 + 专家复核','失败队列、版本指纹、网站自检']]),src='S1 / S3 / S4',note='贡献是可复现的数据合同、受证据约束的工具流程与可审核的产品集成。未声称发明新的通用定位算法；小样本配对仅提供工程可行性证据。')
add(A,'最后的 panic，可能离错误起点很远',svg(box(30,140,460,230,'故障所有者',['释放对象后继续访问','或线程持锁 / 禁抢占循环'])+arrow(510,255,565,255)+box(590,140,430,230,'检测组件',['KASAN / lockdep / RCU','发现违反约束的现场'],True)+arrow(1045,255,1100,255)+box(1125,140,445,230,'终止与次生现场',['panic / watchdog / dump_stack','便于停止，但未必是致错代码'])+text(800,465,'先记录最早诊断及上下文，再沿数据与控制关系追查所有者',32,GRAY,anchor='middle')),
    '设计背景：检测位置、受影响组件与致错位置，需要分别描述。','S1 / S7 / S8 · 机制示意',
    '这是一张机制示意，不是所有故障共用的严格时间序列。UAF 的检测器是 KASAN，候选所有者是外部 ki_bench；OOM 的内核 out_of_memory 是处理路径，压力源来自用户态 pressure.c。保留第一可观测诊断不意味着找到了最早因果事件。')
add(A,'输入可以缺失，输出必须分为两层',svg(box(30,70,450,150,'E = (L, A, S)',['日志、产物、源码'])+box(30,280,450,170,'m ∈ {0,1}³ ∖ {000}',['7 种非空输入组合'])+arrow(505,275,590,275)+box(615,65,950,200,'定界 B = (阶段, 检测器, 所有者, 第一现场)',['运行 / 启动 / 未知；日志行号与 CPU / 任务上下文'],True)+box(615,320,950,200,'定位 Z = (文件, 函数, 区间, 提交候选, 证据)',['位置需要实际读取支持；提交仍需因果验证'])),
    '目标是逐步收窄问题范围，并使每一个定位声明可追溯。','S1 · 任务定义',
    'L 是原始日志；A 是 vmlinux、模块、配置等编译材料；S 是对应源码状态。定界与定位是不同的输出契约。未知字段显式保留 unknown 或 null。所有者可以只是候选，不能把检测器名称直接替代它。')
add(A,'理论支撑转化为明确的工程约束',table(['依据','采用的思想','在本系统中的边界'],[
    ['ReAct · ICLR 2023 [R1]','观察—动作交替，工具补充外部证据','实现有界工具交互；不声称复现其全部机制'],
    ['选择性分类 · 2017 [R2]','覆盖率与风险可通过拒答权衡','当前是材料规则拒答；没有已校准风险保证'],
    ['Delta Debugging · TSE 2002 [R3]','以失败 / 通过干预隔离相关条件','用于下一阶段因果验证设计；尚未实现'],
    ['SWE-bench · ICLR 2024 [R4]','真实仓库任务应有独立执行评测','借鉴验证原则；内核数据与分数不作横比'],
    ['Linux Bug hunting [R5]','用 vmlinux / 调试信息映射源位置','增加 Build ID 与源码状态门禁']]),src='R1–R5 · 一手文献与官方文档',
    note='引用说明设计为何合理，不构成系统准确率或最优性的证明。ReAct 支持交互获取证据的动机；选择性分类提醒同时看覆盖与错误风险，但本实现没有训练选择器或提供统计风险界。Delta Debugging 的失败/通过最小差异是后续干预验证的参考。SWE-bench 的任务与内核定位不同，不能比模型分数。')
add(A,'优化目标：在证据约束下减少交互成本',svg(text(800,95,'min  E[定位损失] + λ · N模型请求 + μ · T定位',48,INK,600,'middle')+box(40,175,730,260,'正确性约束',['位置 ∈ 实际读取的源码窗口','符号化要求运行身份与 ELF 身份匹配','材料不足 → 降级输出 / 拒答'],True)+box(830,175,730,260,'成本约束',['默认最多 8 次模型 HTTP 尝试','默认定位预算 240 秒','失败、重试、格式修复同样计数'])+text(800,520,'这是设计目标；当前采用规则预检和有界循环，未实现最优策略求解',27,GRAY,anchor='middle')),
    '把“少调用”与“有证据”同时写入设计，而非仅优化报告长度。','S1 · 概念目标 / 现有实现',
    '目标函数是概念性形式化：λ、μ 未由实验拟合，系统未实现贝叶斯信息增益优化器，也没有最优性定理。实际优化是基于日志可观测文件名和栈帧的确定性源码预检。约束保证可追溯性，不能保证语义正确。')
add(A,'证据越强，允许的结论才越强',svg(''.join(box(30+i*310,285-i*43,295,205,t,ls,i==2,i>2) for i,(t,ls) in enumerate([
    ('识别诊断',['异常类别 / 第一现场','日志行支持']),('代码候选',['文件 / 函数 / 区间','实际读到的源码']),('身份匹配',['符号与构建一致','ELF / 源码核验']),('机制复核',['专家独立审核','排除次生路径']),('因果验证',['干预 / 重放 / bisect','补丁前后结果'])]))+text(800,550,'当前支持候选与身份核验；机制准确率、提交准确率尚不可报告',30,GRAY,anchor='middle')),
    '路径合法、符号吻合、代码命中，均不自动等于根因正确。','S1 / S3 · 能力层级（非必经串行步骤）',
    '阶梯表达证据强度，不代表每例执行过所有步骤。日志加源码实验没有提供 artifacts，不能宣称这些试验完成了 Build ID 符号映射。evidence_verified 是数据合同下的一致性，不是独立专家机制审核。当前 rootCauseVerified=false，提交真值不存在。')

# 09–13: data and input contracts.
add(D,'四个版本，存在包含关系与场景重叠',table(['版本','库存 / 划分','用途与主要边界'],[
    ['社区 v1','6；train 3 / test 3','真实社区报告；缺逐例匹配的完整产物'],
    ['旧注入 v1','64；train 43 / test 21','历史网站回归；从 67 个原始场景选入'],
    ['网站 v2','80；train 59 / test 21','旧 64 + 启动/配置 16；新增全部 train'],
    ['严格 stability-v1','68 场景 → 60 ready / 8 excluded','59 故障 + 1 健康；ready 划分 51 / 9']]),
    '旧集与严格集共享 59 个有效场景并重新采集；这些数量不能相加为独立根因数。','S1 / S2 / S6 · 数据库存',
    '三个主要来源/采集脉络保留四个版本。备份、网站格式副本和迭代工作目录不算新的数据集。网站 v2 新增 15 条启动日志加 1 个配置变体；15 条启动日志包含重复签名，新增 test 数量为零。严格集用于当前代码定位实验；不要跨版本汇总分数。')
add(D,'数据完整性必须由机器核验',svg(box(25,130,340,260,'隔离采集',['QEMU TCG / 2 GiB','2 vCPU / 禁网络','无宿主共享'])+arrow(385,260,430,260)+box(450,130,340,260,'材料合同',['日志、run.json','源码 / 配置 / ELF','SHA256 / 字节数'],True)+arrow(810,260,855,260)+box(875,130,340,260,'语义门禁',['诊断精确行','因果函数区间','机制组 split'])+arrow(1235,260,1280,260)+box(1300,130,275,260,'不可变封版',['60 ready','8 excluded','新版本扩增'])+text(800,495,'本地深验：423 个合同文件，0 个错误',40,BLUE,600,'middle')),
    '文件齐全、身份一致、标签可检查；失败场景保留但不进入有效定位分母。','S2 / S6 · 已保存的校验结果',
    '423 是合同校验所检查的文件数，不是全部 materialized 文件数。合同还检查路径逃逸、诊断行与实际文本、代码范围、客体参数、运行 GNU notes 与构建身份。当前标注 v2 修复了 debug: 中 bug: 误匹配，v1 历史保留。严格集的物理完整性不扩展为社区集也有完备编译产物。')
add(D,'覆盖 12 类故障，保护类仍占近一半',fig('coverage','stability-v1 的 60 个 ready 样本按故障族分布'),
    '保护 / 非法访问 27/59 = 45.8%；健康样本仅 1/60 = 1.7%。','S6 · ready 样本统计',
    '柱图从 manifest 的 status=ready 按 family 计数，12 个故障族外加一个 healthy。不同检测器和注入变体可能共享源码，不能假设 59 个故障都是独立机制。当前偏斜意味着微平均分数可能掩盖小类失败，应在全量评测报告每族表现和宏平均，并扩充健康、噪声及真实问题。')
add(D,'版本号相同，还不足以信任源码映射',svg(box(40,75,710,180,'运行侧',['release：5.10.210+','run.json 的 GNU Build ID'])+box(850,75,710,180,'构建侧',['vmlinux / bzImage / .ko / config','各文件哈希与独立模块身份'],True)+arrow(780,165,820,165)+box(40,320,1520,195,'源码侧：commit + patch + 外部程序',['f88704ae…77d + shared/source.patch + ki_bench.c / pressure.c','GNU Build ID：4bae92d13e7edbe54f2de539b0aef72c89615511'])+text(800,575,'启动配置变体另有补丁和 bzImage；不能沿用本页身份',27,GRAY,anchor='middle')),
    '同一 commit 的干净树、后续工作树与实际构建源码，不能互相替代。','S6 · 冻结构建身份',
    '本构建是 OpenHarmony 指定 commit 加本地补丁和外部程序。匹配 vmlinux 约 1.017 GB，冻结源码包约 191 MB。Build ID 用于二进制映射；源码包哈希和 patch 用于实际源码状态。未知厂商 revision 不静默转换为 torvalds commit；模块不能拿内核 Build ID 替代。')
add(D,'缺失材料决定能声明到哪一层',table(['日志 L','产物 A','源码 S','允许的结果 / 必须保留的缺口'],[
    ['有','有','有','定界 + 已读代码候选 + 身份门禁后的符号映射'],
    ['有','有','无','定界 / 函数候选；不能声称读过具体源码'],
    ['有','无','有','定界 / 已读代码候选；产物映射未验证'],
    ['有','无','无','日志支持的组件 / 函数候选'],
    ['无','有','有','拒绝故障实例定位；同一构建对应多种运行'],
    ['无','有','无','材料检查；需要补日志'],
    ['无','无','有','源码检查；需要补故障现场']]),src='S1 / S6 · 七种输入合同',
    note='这是能力约束矩阵，不是七种组合的全部实测成功率。三种无日志输入在历史 v6 实验中均完成缺口/拒答。一个构建可同时支持多个不同故障实例，因此只有构建材料不能唯一识别本次事件。source-only 静态审计是另一项任务，不作为实例定位成绩。')

# 14–21: implementation and user-facing loop.
add(I,'网站编排、工具定位与独立评测各司其职',svg(box(25,70,350,195,'浏览器 / Node API',['上传、权限、任务队列','SSE 进度、报告与审核'])+arrow(395,165,440,165)+box(465,70,620,195,'Python 定位 Agent',['材料门禁 → 预检 → 模型 / 工具循环','位置 / 引用校验 → 结果 + 原始轨迹'],True)+arrow(1105,165,1150,165)+box(1175,70,400,195,'本地模型服务',['Ollama 原生结构化输出','单机并发 1，控制预算'])+box(25,355,430,175,'QEMU 数据工厂',['冻结日志、源码、产物、标签'])+arrow(475,440,520,440)+box(545,355,475,175,'独立 Evaluator',['仅它读取评分标签','代码命中、请求、用时'])+arrow(1040,440,1085,440)+box(1110,355,465,175,'专家复核 / 失败回归',['机制审核 / Skill 经验','新版本 → 固定集重跑'])+arrow(780,285,780,325)),
    '当前是单机、单网站进程、文件存储；尚未扩展为分布式服务。','S1 · 实现架构',
    'Node/Express 管理身份归属、队列、去重、SSE 和业务状态；Python 子进程执行只读定位工具。模型服务由平台管理。Evaluator 的标签文件不进入 Agent 输入。上线的人工审核和 Skill 迭代是工程闭环，独立根因机制审核与修复干预仍待完善。')
gt_uaf=read(source_paths['S7']);uafline=gt_uaf['diagnosticEvidence'][0]['text']
add(I,'第一现场保留最早诊断，而非最后栈顶',svg(box(35,65,1530,145,'原始日志 · 第 448 行',[uafline.replace('[   33.794370] ','')],True)+box(35,285,470,215,'阶段与检测器',['runtime','KASAN'])+box(565,285,470,215,'受影响组件',['ki_bench（外部模块）','ki_uaf_kmalloc'])+box(1095,285,470,215,'上下文与引用',['访问 / 分配 / 释放栈','日志行号 + 工具证据 ID'])),
    'firstSceneSeconds 记录确定性诊断提取时间，不是模型推理耗时。','S7 · UAF 原始诊断；S1 · 输出契约',
    '第一现场是第一可观测有效诊断。解析需避免 debug: 等字符串误命中 BUG。提取结果包括发生阶段、检测器和原始上下文，但模型仍需结合源码判断候选所有者。健康日志可返回无诊断。不能把毫秒级提取时间包装为毫秒级根因推理。')
add(I,'八种只读工具，八种可追溯观察',table(['工具','观察内容','主要约束'],[
    ['incident','首诊断、栈、尾部摘要','无诊断可显式为空'],
    ['log_read / log_search','按行读取 / 检索原始日志','参数、输出、窗口有界'],
    ['source_search / source_read','检索源码 / 读取行窗口','工作区路径；保存读过的范围'],
    ['symbolize','符号 + 偏移 → 源位置','Build ID / 架构 / 配置门禁'],
    ['git_history / git_show','历史候选 / 实际补丁','可信仓库；提交因果性未验证']]),
    '工具能力按输入材料开放；模型不能执行任意 shell 或修改被分析源码。','S1 · localization_agent.py',
    '表中每一组带斜杠的工具分别计数，总计 1+2+2+1+2=8。路径必须在准备的源码工作区内，输出行号范围保存为证据。symbolize 的匹配依赖实际材料身份。Git 工具产生读过补丁的候选提交，不能把存在相关改动写成引入提交已验证。')
loop=box(40,80,310,180,'1 材料 / 预检',['确定性首诊断','日志引导源码读取'])+arrow(370,170,420,170)+box(445,80,310,180,'2 模型选择',['继续取证','或输出 JSON'],True)+arrow(775,170,825,170)+box(850,80,310,180,'3 只读工具',['执行固定动作','返回证据 ID'])+arrow(1180,170,1230,170)+box(1255,80,310,180,'4 报告校验',['引用 / 代码范围','保存失败或候选'])
loop+='<path d="M1000,280 L1000,350 L590,350 L590,280" fill="none" stroke="#8E8E93" stroke-width="3" marker-end="url(#ar)"/>'+text(800,410,'观察不足 → 在预算内继续；最后一次请求禁用工具，要求收敛',28,GRAY,anchor='middle')+text(800,525,'默认预算 8 次实际模型请求 / 240 秒；保留请求失败和格式错误',32,INK,600,'middle')
add(I,'工具观察进入下一轮，报告接受独立校验',svg(loop),src='S1 · 有界循环',note='循环有硬预算和子进程超时保护。预检工具与模型选择工具分别计量。最后一次请求禁用工具只是收敛措施，不保证一定产生有效 JSON；解析失败仍记失败。报告位置必须在工具读过的源码范围内；这些结构校验不能证明解释的因果正确性。')
add(I,'本次优化：把重复源码检索前移',svg(text(45,70,'v9 对照',29,GRAY,600)+box(40,110,420,160,'首诊断预检',['1 次 incident'])+arrow(485,190,550,190)+box(580,110,980,160,'模型发起检索 / 读取 / 报告',['5 个故障共经历 20 次模型请求；健康 1 次'])+text(45,350,'v10 迭代',29,BLUE,600)+box(40,390,720,160,'首诊断 + 有界源码预检',['从日志任务文件名 / 实际栈帧检索与读取'],True)+arrow(785,470,850,470)+box(880,390,680,160,'模型直接形成结构化候选',['本组六例各 1 次模型请求'])),
    '标签、case ID 与注入答案不用于预检；工具读取仍被记录。','S3 · sourceTriage 迭代',
    'eagerBoundary 两组都开启，主要变项为 sourceTriage。v10 把常见、重复的工具选择前移为确定性动作。六例总模型调用从 21 到 6；这组模型选择工具数是零，因此证据更支持“准备证据减少交互”，不支持“模型规划能力提升”。符号命名仍可泄漏注入机制，这是样本局限。')
add(I,'评分标签留在评测器，材料视图交给 Agent',svg(box(45,100,410,330,'封版数据',['serial.log / agent.log','source / ELF / run.json','ground-truth / split'])+arrow(480,210,555,210)+box(585,80,960,190,'Agent 独立输入视图',['只含选定 L / A / S；不含 manifest、case ID 或因果标签'],True)+arrow(480,380,555,380)+box(585,340,960,190,'Evaluator 独立评分',['读取标签及模型结果；失败计入；保存数据 / 代码指纹'])+text(800,590,'避免显式标签泄漏；合成函数名称与数据重复仍需单独控制',27,GRAY,anchor='middle')),
    '数据完整性门禁先通过，再执行导出、定位与评分。','S1 / S6 · 评测隔离',
    'agent.log 去除注入答案提示并保留行号。独立目录隔离防止工具直接看到 ground truth。隔离不是完全去泄漏：外部注入函数叫 ki_uaf_kmalloc，源码本身暴露机制；同机制变体和版本重叠可能造成依赖。正式泛化试验需要来源/机制分组划分和冻结测试。')
ui='<div class="ui-proof"><img src="media/website-agent-v10.jpg" alt="真实网站仅日志 UAF 报告，显示第一现场、函数候选、证据和源码缺口"><div><div class="proof-k">真实验收截图 · 日志输入</div><div class="proof-title">缺源码时，界面明确保留缺口</div><div class="li">第一现场：阶段、检测器、涉及组件</div><div class="li">函数候选：有日志支持，尚无具体源码行</div><div class="li">工具证据：可展开、可追溯</div><div class="li">后续步骤：补源码、核查机制、人工确认</div></div></div>'
add(I,'报告页将证据和定位粒度一起交付',ui,'这个旧网站 UAF 案例没有匹配源码，因此展示函数候选；不算代码行命中。','S5 · website-agent-v10.jpg',
    '截图来自既有真实验收，数值 9.864 秒、1 次模型请求、1 次工具检查属于该网站旧 UAF 案例，不能和六例配对中的 UAF 18.166 秒混为一条记录。本页展示产品可审核性与材料不足时的边界。截图只含合成案例诊断，不包含私有账户或用户材料。')
add(I,'人工审核与失败回归，构成可持续工程闭环',svg(box(25,125,350,270,'分析与报告',['候选 / 证据 / 缺口','试跑不计业务贡献'])+arrow(395,260,440,260)+box(465,125,350,270,'专家审核',['机制解释 / 证据引用','确认或退回'],True)+arrow(835,260,880,260)+box(905,125,310,270,'版本化改进',['失败回归队列','声明式 Skill 经验'])+arrow(1235,260,1280,260)+box(1305,125,270,270,'独立重测',['固定数据指纹','无回归再合入'])+text(800,505,'Skill 的类别 F1、Agent 代码命中与真实业务解决率，分别计量',30,GRAY,anchor='middle')),
    '工程流转已实现；独立机制标签和修复因果验证仍是未完成环节。','S1 · 专家 / Skill / 业务流程',
    '审核结论必须填写；确认后才计入业务解决数。Skill 为声明式经验，不执行投稿代码。冻结测试、管理员审核、手动评测和无回归门禁控制合入，基准变化使旧评测失效。Skill 类别 F1 不能替代 Agent 定位准确率；网站试跑和离线 benchmark 不计真实业务收益。')

# 22–33: actual experiments and interpretation.
add(R,'固定六例、同模型预算，只改变源码预检',table(['条件','v9 对照','v10 迭代'],[
    ['输入 / 案例','日志 + 源码；5 故障 + 1 健康','相同六例与数据指纹'],
    ['模型 / 传输','qwen3.8:27b-kernel-8k / Ollama 原生','相同；think:false / 结构化输出'],
    ['首诊断预检 eagerBoundary','开启','开启'],
    ['源码预检 sourceTriage','关闭','开启'],
    ['最大预算','8 次实际请求 / 240 秒','相同'],
    ['评测限制','单次运行；无随机化 / 重复统计','固定小样本；并非盲测全量 test']]),src='S3 · 配对试验设计',
    note='数据 manifest SHA256=10194de9…85bb63f。配对案例混合 train/test，不能称为未接触的测试集。两个 Agent 文件哈希分别是 b4d5a74c…8ef84 与 b920fab0…c1cd。配置对照控制了主要设置，但没有随机运行顺序、独立重复或稳定负载证据，服务暖机/争用可能影响耗时。')
add(R,'定位准确率、请求与时间，各有固定口径',table(['指标','分母 / 起止 / 计数','必须避免的误读'],[
    ['代码定位命中率','文件 + 函数 + 与标签区间重叠；5 故障','失败仍在分母；健康不进入分母'],
    ['报告完成率','有效报告 / 全部计划 6 例','完成 ≠ 定位正确'],
    ['实际模型请求','每次 HTTP 尝试；六例汇总','错误和格式修复不漏计'],
    ['定位时间','流程开始至落盘前；含接口等待','不含采集、材料准备及网站排队'],
    ['首诊断时间','确定性诊断提取','不能解释为模型语义推理时间'],
    ['机制 / 提交准确率','独立机制审核 / 提交真值后评分','当前均为 null']]),src='S1 / S3 · 评分协议',
    note='区间重叠是当前自动评分的宽松性：命中目标函数范围不证明精确表达式级定位。需要增加行级距离、Top-k、机制正确性和错误归因评审。报告完成和代码命中分别记录。健康误报/拒答和无日志拒答需要独立指标；当前一例健康无法估计真实误报率。')
add(R,'配对结果支持改进方向，尚不足以推断泛化',table(['指标','v9 对照','v10 迭代','观察变化'],[
    ['代码位置命中','3/5 = 60%','5/5 = 100%','+40 个百分点'],
    ['有效报告','5/6','6/6','OOM 不再失败'],
    ['模型请求总数','21','6','−71.4%'],
    ['定位时间总和','181.347 s','95.834 s','−47.2%'],
    ['工具调用总数','25','16','自动预检 6 → 16'],
    ['机制 / 提交准确率','未知 / 未知','未知 / 未知','没有因果闭环分数']]),src='S3 · 固定六例（健康不计代码分母）',
    note='请求减幅=(21-6)/21；时间减幅=(181.347-95.834)/181.347。六例平均流程时间约 30.225→15.972 秒，但平均值仅描述这一组。工具总数由原始 metrics 加总，预检增加不意味着工具总数增加，因为模型反复检索减少。')
add(R,'五个故障中，两项从失败或未命中转为命中',fig('paired-hits','UAF、泄漏、锁顺序保持命中；原子态睡眠和 OOM 改善；健康保持拒答'),
    'UAF、泄漏、锁顺序保持；原子态睡眠与 OOM 改善。健康基线单独观察。','S3 · 逐例结果',
    '原子态睡眠在 v9 生成有效报告但未命中正确代码；OOM 在 v9 请求预算内遭遇 HTTP/格式错误并失败。两项改善、零项退化只能描述本组。健康拒答保持，不算第六个代码命中。')
add(R,'请求减少集中在重复检索与 OOM 收敛',fig('requests','六例配对模型请求数，v9 为 3、3、3、3、8、1，v10 均为 1'),
    'v9：3 + 3 + 3 + 3 + 8 + 1 = 21；v10：六例各 1 次。','S3 · 原始请求轨迹',
    '请求数是网络尝试数，不是聊天轮数或成功次数。OOM 的八次包括接口错误和最终 JSON 解析失败。一次模型请求并不等于零工具工作，下一页工作量分析进一步区分。')
add(R,'定位总时间减少 85.513 秒',fig('latency','六例定位秒数逐例对照，每个样本 v10 均低于 v9'),
    '181.347 → 95.834 秒；本次每例均下降，但未获得重复运行的方差。','S3 · 定位流程计时',
    '六例差值分别约 29.104、10.017、9.289、4.152、28.748、4.203 秒；总差 85.513 秒。总耗时是流程时间加总，不是批任务墙钟时间或用户提交到确认的时间。单次顺序运行缺少方差估计，不能报告显著加速或生产 SLA。')
add(R,'一次模型请求背后，仍有自动取证',fig('tool-work','v9 自动预检 6、模型工具 19；v10 自动预检 16、模型工具 0'),
    '已记录 prompt tokens：100,430（20/21 次有 usage）→ 30,726（6/6）。','S3 · 工具与 usage 轨迹',
    'v9 25 次工具=6 自动+19 模型选择；v10 16 次工具全部自动。v9 有一次 HTTP 500 没有 usage，100430 是可观测 prompt token 合计，不是完整真实消费，不能直接当精确费用或计费 tokens。输出 tokens 的可观测合计 3166→3269，说明请求减少不意味着最终报告变短。未测 GPU 能耗或现金成本。')
add(R,'5/5 的区间仍宽，不能宣称稳定 100%',fig('uncertainty','代码命中率双侧 95% 精确二项区间：3/5 为 14.7%–94.7%，5/5 为 47.8%–100%，2/3 为 9.4%–99.2%'),
    '配对仅 2 项改善、0 项退化；精确 McNemar 双侧 p = 0.50。','S3 + R6 · 小样本不确定性',
    '采用 scipy.stats.beta.ppf 计算双侧 Clopper-Pearson 区间；分别为约[14.663,94.726]、[47.818,100]、[9.430,99.160]百分比。精确 McNemar 在两项不一致结果上等价于 Binomial(2,0.5) 双侧检验，p=0.5。二项模型需要独立同分布/交换性，当前机制依赖和选择样本不保证满足，所以区间仅展示不确定性，不证明总体置信覆盖。未做请求数或耗时显著性检验。')
add(R,'额外三例：2/3 命中，RCU 仍然失败',table(['额外样本','代码命中','模型请求','定位时间'],[
    ['LKDTM 空指针','命中','4','28.464 s'],
    ['堆越界','命中','1','16.992 s'],
    ['RCU stall','未命中','1','18.974 s']]),
    '三例在 manifest 中均为 train；文件名中的 holdout 不代表独立盲测。','S3 · 额外探索（总计 64.430 秒）',
    '额外三例不是六例配对的另一个随机重复，也不与其合并成准确率。RCU 输出错误地落到 perf dump_stack 与 printk 头文件桩定义，未找到实际致错线程，且声称没有日志。它说明读到真实源码仍可能语义误归因。应复核 sourceTriage 的通用框架栈过滤，并保留原失败回归；该修正尚未在本报告实施。额外试验与早期验收并发，耗时可能受服务争用。')
code='\n'.join(f'{r["line"]:>3}  {r["text"].expandtabs(4)}' for r in gt_uaf['causalCode'])
uafbody='<div class="code2 source-proof"><div class="code"><div class="tt">实际冻结源码 · external/ki_bench.c</div><pre>'+E(code)+'</pre></div><div class="code proof"><div class="tt">位置与证据</div><div class="li"><b>日志第 448 行</b><br>KASAN use-after-free，ki_uaf_kmalloc</div><div class="li"><b>实际源码 106–114 行</b><br>分配 → kfree → p[0] 写入</div><div class="li"><b>v10 报告位置</b><br>文件 / 函数 / 区间评分命中</div><div class="li">尚无修复回放或引入提交真值</div></div></div>'
add(R,'UAF：释放后写入，由日志与源码共同支持',uafbody,'真实故障日志、实际源码和报告位置相互吻合；独立机制评分仍未完成。','S7 + S3 · 代码案例',
    '源码截取自冻结 ground-truth 的 causalCode，逐行保留，用于讲解已存在的独立评分标签；这些标签没有作为 Agent 输入。Agent 使用工具准备的对应源码。示例中的 p[0] 在 kfree 之后，提供清楚的程序语义解释。但合成符号显著暴露机制，不能把该容易样本推广为生产根因证明。')
add(R,'OOM：找到压力源，仍需区分目标与实际',svg(box(30,100,470,310,'程序目标',['1024 × 8 MiB = 8 GiB','malloc 后逐页触碰','压力程序 pressure.c'])+box(565,100,470,310,'运行观测',['客体内存 2 GiB','OOM 发生时 RSS 约 1.39 GiB','panic_on_oom=2'])+box(1100,100,470,310,'候选代码',['pressure.c · main','报告 8–13 行命中','独立机制复核：待完成'],True)+text(800,515,'达到程序目标上限 ≠ 本次实际分配量；内核 OOM 处理函数 ≠ 压力源',30,GRAY,anchor='middle')),
    'v9：8 次请求后失败；v10：1 次请求、17.156 秒，位置评分命中。','S8 / S3 · OOM 回归项',
    'ground truth main 范围为5–16行，模型候选8–13行与其重叠。程序保留1024个8MiB块的目标上限为8GiB，但2GiB客体在实际达到该目标前触发OOM。RSS 来自原始任务表、需按客体页面大小换算，仅表示一个时点的常驻内存。既有报告把目标约8GB写得过于确定，回归队列已要求独立审核。代码命中不能掩盖机制描述不严谨。')
add(R,'历史缺失实验支持降级，但不是完整消融',table(['历史试验','已保存观察','可得结论'],[
    ['v6：无日志的 3 种组合','artifacts+source / artifacts / source 均拒绝实例定位','缺日志时材料不足被显式报告'],
    ['v6：日志 + 产物','函数命中，具体源码位置未命中','能映射线索，不应宣称读过源码'],
    ['v6：日志 + 源码','该次运行失败','保留失败；不能用重试成绩覆盖'],
    ['v9：UAF 仅日志','函数命中；无代码行；1 请求 / 31.798 s','材料粒度约束在实际报告中生效']]),
    '这些版本、配置和样本不同，不能据此估计七种组合的平均性能。','S4 · 历史原始实验',
    'v6 ablations 五次运行共4/5完成、12次请求、448.593秒，代码分母只有有源码且有日志的一例且失败。v9 boundary试验的UAF仅日志能定位函数候选，日志加源码另一条记录53.539秒，与本报告配对UAF47.270秒不是同一次。当前尚未完成60×7的全量矩阵；不能把七种输入视图的支持能力写成七种组合已经稳定跑通。')

# 34–40: validation, threats, significance, references, reproducibility.
add(C,'网站验收与 Agent 质量，需要两套证据',stats([('36/36','Node 测试<br>本地整理后的最新记录'),('38/38','Python 测试<br>包含备份安全新增 9 项'),('15/15','隔离网站业务检查<br>最新本地整理记录'),('9/9','既有线上检查<br>属于此前恢复验收时点'),('8/8','既有匹配源码真实模型检查<br>验证流程，不能作定位准确率'),('0','本次为制稿新增的模型实验<br>没有改写既有成绩')]),
    '最新交接中网站按用户要求关闭；本报告引用历史验收，不宣称服务器当前在线。','S2 / S5 · 不同阶段验收',
    '此前网站验收为Node36/Python29、隔离15、线上9、真实模型8。随后本地归档整理加9个Python备份测试，变为38，不是重跑线上模型。流程检查数与故障样本数不同，8个模型验收项不能作为8/8定位准确率。当前站点关闭属于用户操作要求，不影响历史验收记录真实性。')
add(C,'现有证据的四类效度威胁',table(['威胁','对结论的影响','下一步补证'],[
    ['选择偏差与合成泄漏','五个配对故障不代表59个故障；函数名提示机制','全量冻结集 + 去提示 / 真实问题对照'],
    ['内部效度：单次与服务状态','暖机、缓存、运行次序可能影响耗时','随机交错重复；负载与失败统一计数'],
    ['构念效度：区间重叠评分','函数范围命中可能高估精确行定位；未验证解释','行级距离 / Top-k + 独立机制审核'],
    ['外部效度：单构建与类别偏斜','难推断其他版本、硬件和真实业务误报率','多内核 / 来源分组；扩充健康与噪声']]),src='S3 / S6 · 讨论',
    note='此外，旧/新版本重叠造成样本依赖，v2新增全train且重复签名，不能按数量增长推断泛化。每项威胁给出能改变证据强度的补证方式，不声称这些方案已执行。正式预注册评测必须固定案例选择、缺失组合、预算、模型版本、超时和失败处理。')
add(C,'因果闭环还需补上干预与回放',svg(box(25,125,355,265,'先补当前缺口',['RCU 失败回归','OOM 机制独立复核','保留原始模型轨迹'],True)+arrow(400,255,440,255)+box(465,125,350,265,'再扩全量评测',['60 ready × 7 组合','随机重复 / 冻结 test','健康、噪声、真实问题'])+arrow(835,255,875,255)+box(900,125,350,265,'建立因果真值',['引入提交 / 复现条件','配套 vmcore 与身份','补丁前后干预'])+arrow(1270,255,1310,255)+box(1335,125,240,265,'验证闭环',['独立审核','失败 / 通过','回归重放'])+text(800,510,'只有介入改变了可重复的失败结果，才有更强的因果依据',30,GRAY,anchor='middle')),
    '本页是后续实施方案；没有把计划中的 bisect、转储分析或修复回放写成已实现。','S1 + R3 · 后续验证路线',
    '次序是先修正已知语义问题与独立复核，再全量评测，最后构建真实引入提交和补丁前后的实验对照。Delta Debugging 提供失败/通过差异最小化的思路；并非所有内核故障都能通过单次补丁证明，环境与非确定性需要重复和控制。当前没有vmcore或自动bisect的实绩。')
add(C,'切实价值：缩短可审核的初诊路径',two(('已测得的工程收益',[
    '<b>少 15 次模型 HTTP 尝试</b><br>固定六例 21 → 6，失败也计数',
    '<b>少 85.513 秒流程时间总和</b><br>含接口等待，未计材料准备与人工审核',
    '<b>保留证据与缺口</b><br>候选代码可复核，错误能进入回归队列']),
    ('适用条件与扩展方向',[
    '<b>适合受控日志分诊与专家辅助</b><br>材料身份可确认、问题可追溯',
    '<b>规模化需要新的服务基础</b><br>事务存储、持久队列、对象存储',
    '<b>业务收益仍需真实确认数据</b><br>尚无人工节时、现金成本或生产 SLA 结论'])),src='S1 / S3 · 实践意义',
    note='价值是减少专家前置检索负担、提高候选证据可审计性，而不是自动替代专家。当前没有按人时计算的对照试验，也没有云服务计费或GPU能耗数据。不要把局部流程47.2%下降等同于端到端MTTR改善。文件型单进程状态与内存队列限制服务扩展。')
add(C,'结论按证据强度逐条落账',table(['主张','已有支撑','结论状态'],[
    ['数据资产可复现','60 ready；423 文件深验；构建 / 源码冻结','严格集范围内已支持'],
    ['有界预检可减少重复交互','固定六例：21→6 请求；181.347→95.834 秒','支持本组工程改进'],
    ['当前已获得稳定泛化定位能力','额外三例仅2/3；无全量重复 / 盲测','证据不足'],
    ['已完成根因与提交因果闭环','无独立机制准确率 / 引入提交真值 / 修复重放','尚未完成']]),
    '已完成“数据—取证—候选—评分—回归”的工程链；因果验证是下一阶段的核心。','S1 / S2 / S3 · 结论',
    note='本报告的中心结论是受材料合同和证据范围约束的工具定位具有工程可行性，预检在固定案例上有效。数据集覆盖、网站验收、代码位置命中和因果正确是四个不同问题，必须保留各自分母与证据。不得将表中的“尚未完成”省略后对外宣称完整自动根因系统。')
refs=[('R1','Yao et al. · ReAct · ICLR 2023','https://arxiv.org/abs/2210.03629'),
      ('R2','Geifman & El-Yaniv · Selective Classification · 2017','https://arxiv.org/abs/1705.08500'),
      ('R3','Zeller & Hildebrandt · Delta Debugging · TSE 2002','https://www.cs.purdue.edu/homes/xyzhang/fall07/Papers/delta-debugging.pdf'),
      ('R4','Jimenez et al. · SWE-bench · ICLR 2024','https://arxiv.org/abs/2310.06770'),
      ('R5','Linux Kernel Documentation · Bug hunting','https://docs.kernel.org/admin-guide/bug-hunting.html'),
      ('R6','NIST · Proportion Confidence Interval','https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/propconf.htm')]
add(C,'参考文献：设计依据与证据边界可查',table(['编号','一手研究 / 官方资料'],[[r,f'<a href="{u}" target="_blank" rel="noreferrer">{E(t)} ↗</a>'] for r,t,u in refs]),
    '引用用于支撑设计原则；本项目数据不借用文献分数，不声称达到其理论保证。','R1–R6 · 2026-10-07 核对',
    note='网页的参考文献条目可点击；离线浏览不依赖外部资源。完整书目信息、采用的观点及适用限制见资料来源.md。全部图为项目数据生成、机制自绘或实际网站截图，没有复制论文图或长段原文。')
add(C,'复现入口：数据、图表、页面均可追溯',two(('原始证据与身份',[
    '<b>严格集 manifest SHA256</b><br><span class="hash">10194de902204fd6621428e2631f044fc17<br>dada0b4fcea679ba1e00d285bb63f</span>',
    '<b>配对实验</b><br>docs/agent-iteration-20261007.json',
    '<b>原始轨迹归档</b><br>benchmark-traces-v10.tgz；15 个文件']),
    ('本讲解稿附带',[
    '<b>analysis-data.json / paired-results.csv</b><br>真实数值、源文件哈希、统计区间',
    '<b>build_deck.py / media/*.svg</b><br>可复算图表；HTML 使用 Kelip 模板',
    '<b>讲稿 / 来源 / 全页预览 / QA</b><br>逐页口径、边界与渲染检查结果'])),
    '所有模型分数来自既有保存结果；运行制稿脚本不会启动服务器或调用模型。','S3 / S6 · 可复现附录',
    note='先运行数据合同验证器，再按 docs/KERNEL_LOCALIZATION_LOOP.md 准备新输入视图和评测输出目录，避免覆盖冻结数据。模型运行需要原模型服务和匹配源码环境，图表重建仅需要Python/Pillow/Matplotlib/SciPy。结果文件和Agent代码哈希见analysis-data及原始实验JSON。完整讲解稿目录可复制分享；私有账号、任务数据库和完整服务器备份不包含在交付物中。')
assert len(slides)==40
slides, notes = deck_revision.revise(slides, notes, HERE, globals())

template_path=HERE/'vendor/kelip-slide/assets/deck-template.html'
if not template_path.is_file(): template_path=ROOT/'tools/kelip-slide/assets/deck-template.html'
template=template_path.read_text(encoding='utf-8')
start=template.index('<!-- ===== 1 ')
end=template.index('<div id="nav-hot"')
template=template[:start]+'\n'.join(slides)+'\n</div>\n'+template[end:]
template=template.replace('【这里写：系列 · 第 N 期 · 主题】','Kernel Insight · 系统设计与实证分析')
template=template.replace('"PingFang SC","SF Pro Display"','"PingFang SC","Microsoft YaHei","SF Pro Display"')
template=template.replace('font-family:"PingFang SC","Helvetica Neue",sans-serif','font-family:var(--font)')
extra='''
/* Research deck additions; stage, navigation and all base layouts remain Kelip. */
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.kicker{letter-spacing:.06em}.tbl.left th{letter-spacing:.025em}
.tbl.left td{padding:19px 16px;font-size:28px}.tbl td{line-height:1.4}
.tblwrap{padding:32px 44px}.tbl.left td:first-child{min-width:215px}
.tbl.left td:last-child{min-width:230px}.tbl.left td{overflow-wrap:anywhere}
.code pre{font-size:29px;line-height:1.75;margin-top:24px;tab-size:4}
.code.proof{flex:.92}.code .li{font-size:26px;padding:18px 0;line-height:1.35}
.code2.source-proof>.code:first-child{flex:1.4}.code2.source-proof>.code.proof{flex:.8}
.ui-proof{flex:1;min-height:0;margin-top:38px;display:flex;gap:70px;align-items:center;justify-content:center}
.ui-proof>img{height:100%;max-width:650px;object-fit:contain;border-radius:24px;box-shadow:0 14px 48px rgba(0,0,0,.06)}
.ui-proof>div{max-width:850px}.proof-k{font-size:23px;color:var(--muted);margin-bottom:20px}
.proof-title{font-size:43px;font-weight:600;margin-bottom:32px;line-height:1.3}
.hash{font-family:var(--mono);font-size:23px;line-height:1.65;display:inline-block}
@media print{html,body{height:auto;overflow:visible}#stage{position:static;transform:none!important;width:1920px;height:auto}.slide{display:flex!important;position:relative;width:1920px;height:1080px;break-after:page}#nav-hot,#nav-btn,#nav-panel,#hud{display:none!important}@page{size:1920px 1080px;margin:0}}
'''
template=template.replace('</style>',extra+'\n</style>')
template=template.replace('</style>',deck_revision.CSS+'\n</style>')
# Retain the Kelip navigation and replace its demonstration-only animation block.
anim_start=template.index('  // ---- 分步动画：')
anim_end=template.index('  const navBtn=',anim_start)
template=template[:anim_start]+deck_revision.ANIM_JS+template[anim_end:]
template=template.replace("else if(e.key==='g'||e.key==='G')", "else if(e.key==='p'||e.key==='P'){ if(anim) anim.toggle(); }\n    else if(e.key==='g'||e.key==='G')")
template=template.replace("if(e.target.closest('a,#nav-panel,#nav-btn,#nav-hot'))", "if(e.target.closest('a,button,.flow-demo,#nav-panel,#nav-btn,#nav-hot'))")
template=template.replace("addEventListener('keydown',e=>{", "addEventListener('keydown',e=>{\n    if(e.target.closest('button') && [' ','Enter'].includes(e.key)) return;")
# Add a keyboard-only overview jump and offline provenance metadata without remote dependencies.
template=template.replace('</head>','<meta name="description" content="48页系统设计与实证分析，含Windows真实界面、科研统计图和交互流程。">\n</head>')
(HERE/'deck.html').write_text(template,encoding='utf-8')
(HERE/'讲稿.md').write_text('# Kernel Insight 逐页讲稿\n\n适合约 30–40 分钟系统汇报。图表和数值仅来自既有记录；详细数据见 analysis-data.json。\n\n'+'\n'.join(notes),encoding='utf-8')
source_doc='''# 资料来源与论断边界

证据截止：2026-10-07。原始实验没有为制稿重跑；Windows 本地网站已启动用于展示，远端在线状态不由历史验收推断。相同场景/不同版本不合并为独立样本。私有业务备份没有进入本交付物。

## 项目证据

编号 | 工作区文件 | SHA256
---|---|---
'''
source_doc+='\n'.join(f'{k} | `{v["path"]}` | `{v["sha256"]}`' for k,v in sources.items())
source_doc+='''

## 一手文献与官方资料

1. **[R1]** Yao, S. et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR 2023. [arXiv](https://arxiv.org/abs/2210.03629)。采用工具动作获取观察、依据观察更新行动的交互思想。本系统采用有界工具与结构化输出，未复现论文全部方法，未比较其任务分数。
2. **[R2]** Geifman, Y. & El-Yaniv, R. *Selective Classification for Deep Neural Networks*. 2017. [arXiv](https://arxiv.org/abs/1705.08500)。采用覆盖与风险需要共同考虑的拒答思想。当前材料规则拒答没有概率校准或论文中的风险保证。
3. **[R3]** Zeller, A. & Hildebrandt, R. *Simplifying and Isolating Failure-Inducing Input*. IEEE TSE 28(2), 2002. [原论文 PDF 镜像](https://www.cs.purdue.edu/homes/xyzhang/fall07/Papers/delta-debugging.pdf)。以失败/通过差异和输入最小化作为因果验证设计的参考；当前未实现自动 Delta Debugging 或 bisect。
4. **[R4]** Jimenez, C. E. et al. *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* ICLR 2024. [arXiv](https://arxiv.org/abs/2310.06770)。借鉴真实仓库任务需独立验证的评测方向。其问题、编程语言与评分对象不同，不与本项目准确率横比。
5. **[R5]** Linux Kernel Documentation. *Bug hunting*. [官方文档](https://docs.kernel.org/admin-guide/bug-hunting.html)。文档支持使用调试信息、vmlinux / 模块和函数偏移定位源码。Build ID、源码补丁和注册表匹配是本系统的额外工程门禁。
6. **[R6]** NIST Dataplot Reference Manual. *Proportion Confidence Interval*. [官方统计说明](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/propconf.htm)。精确二项区间采用 Clopper–Pearson，双侧95%；使用 SciPy beta.ppf 复算。

所有外部资料于 2026-10-07 核对。正文使用概述，无论文图复制或长段引文。外部文献只支持相应设计原则，不作为本项目效果证明。

## 统计与实验口径

- 代码位置命中：路径、函数、标签函数区间重叠；不是表达式级精确定位，也不是根因机制正确。五个故障为代码分母，健康独立计量。
- 六例耗时是流程时间之和；不含客体故障注入、材料准备、网站排队和专家审核，包含模型接口等待。
- 实际 HTTP 尝试含错误及格式修复；自动预检与模型选择工具分列。
- 95%精确二项区间：下界 B⁻¹(0.025;k,n−k+1)，上界 B⁻¹(0.975;k+1,n−k)，零命中/全命中端点取0/1。其独立同分布假设在当前选择样本中未获保证，只用于展示小样本不确定性。
- 精确 McNemar：不一致配对为2个改善、0个退化，双侧 Binomial(2,0.5) 检验 p=0.50。不能据此声称显著改进。
- 模型按需检索组 prompt usage 只有20/21次；100,430是可观测合计，不能当完整消费或现金费用。
- 额外三例在清单中均为train，命名holdout不能充当独立盲测证据；额外耗时受并发验收争用影响。
- 首诊断耗时只是确定性日志提取；evidence_verified只是合同证据一致性；rootCauseAccuracy 与 introducingCommitCorrect 未获独立真值。
- OOM源码目标上限为8GiB；任务表RSS仅为时点观测，约1.39GiB，不表示程序已达到目标。页大小按客体4KiB；原始任务表保存在该case的agent.log。

## 可复现文件

`build_deck.py` 从上述项目证据提取数据，写 `analysis-data.json` 和 CSV；统计图使用 Matplotlib 输出独立 SVG / PNG。机制图为自绘示意。新增网站图来自 Windows 本地浏览器实拍；截图与裁切来源见 `media/site/provenance.json`。当前六份定位报告为既有真实实验的明确标注回放，没有为截图新增模型调用。`讲稿.md` 给出每页分母、边界与来源。
'''
(HERE/'资料来源.md').write_text(source_doc,encoding='utf-8')
print(json.dumps({'slides':len(slides),'figures':len(list(MEDIA.glob('*.svg'))),'ready':len(ready),'counts':counts,'output':str(HERE/'deck.html')},ensure_ascii=False))
