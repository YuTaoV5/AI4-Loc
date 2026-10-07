const crypto=require('crypto');
const definitions=[
 {id:'memory-oob',name:'KASAN 越界分析',category:'内存越界',patterns:['slab-out-of-bounds','out-of-bounds'],guidance:'核对访问大小、对象分配大小及越界偏移，检查索引、长度与对象类型转换。'},
 {id:'memory-uaf',name:'对象生命周期分析',category:'释放后使用',patterns:['use-after-free'],guidance:'对照 Allocated by / Freed by 调用栈，检查引用计数、RCU 宽限期与异步回调生命周期。'},
 {id:'hung-task',name:'阻塞任务分析',category:'任务挂起',patterns:['blocked for more than','INFO: task hung'],guidance:'识别 D 状态任务的等待点，收集持锁者和所有 CPU 栈，验证完成量或 task_work 是否可能无法执行。'},
 {id:'lockdep',name:'锁依赖分析',category:'锁依赖',patterns:['circular locking dependency','possible deadlock'],guidance:'提取 existing dependency chain 和持锁顺序，区分锁类别误报与可复现 ABBA 死锁。'},
 {id:'rcu-stall',name:'RCU / watchdog 分析',category:'RCU / 锁死',patterns:['rcu detected stall','soft lockup','hard LOCKUP'],guidance:'核对长时间关中断、抢占关闭和循环路径；结合所有 CPU 栈分析 RCU grace period。'},
 {id:'oom',name:'内存压力分析',category:'OOM',patterns:['Out of memory','oom-kill','invoked oom-killer'],guidance:'检查 Mem-Info、cgroup 限额和分配阶数，区分容量耗尽、泄漏和内存碎片。'}
];
const builtins=definitions.map(s=>({...s,version:'1.0.0',contributor:'项目内置规则',team:'Linux Reliability',status:'active',createdAt:'2026-10-06',evaluation:null}));
function inspect(log){
 const lines=log.split(/\r?\n/);
 const frames=[];for(let i=0;i<lines.length;i++){const m=lines[i].match(/\b([a-zA-Z_][\w.]*)\+(0x[a-f0-9]+)\/(0x[a-f0-9]+)(?:\s+([\w./-]+\.[ch]):(\d+))?/);if(m&&!frames.some(f=>f.symbol===m[1]))frames.push({symbol:m[1],offset:m[2],file:m[4]||null,line:m[5]?Number(m[5]):null,logLine:i+1});if(frames.length>=30)break;}
 const version=log.match(/(?:Not tainted|Tainted:[^\n]*?)\s+(\d+\.\d+(?:\.\d+)?[^\s]*)/)?.[1] || log.match(/Linux version\s+(\S+)/)?.[1] || null;
 const commit=log.match(/-g([a-f0-9]{12,40})\b/)?.[1] || null;
 return {lines,frames,version,commit};
}
function analyze(log,skills,cases,context){
 const {lines,frames,version,commit}=context||inspect(log);
 const matched=skills.filter(s=>s.status==='active' && s.patterns.some(p=>log.toLowerCase().includes(p.toLowerCase())));
 const diagnostic=/\bBUG:|\bWARNING:|\bOops:|INFO:\s*(?:task.*(?:hung|blocked)|possible|rcu)|rcu.*(?:detected|self-detected).*stall|blocked for more|invoked oom-killer|oom-kill:|Out of memory|unreferenced object|kmemleak:.*[1-9][0-9]* new suspected|Kernel panic/i;
 const evidence=[];for(let i=0;i<lines.length;i++){if(diagnostic.test(lines[i])||/Not tainted|Tainted:|Call Trace|Allocated by|Freed by/i.test(lines[i]) || matched.some(s=>s.patterns.some(p=>lines[i].toLowerCase().includes(p.toLowerCase())))){evidence.push({line:i+1,text:lines[i]});if(evidence.length>=40)break;}}
 const category=matched[0]?.category || '待专家分析';
 const candidates=cases.filter(c=>c.category===category && new RegExp(`\\b${c.symbol}\\b`).test(log)).map(c=>({...c,matchBasis:'异常类别 + 调用符号匹配；不是根因证明',sameRevision:!!c.kernelCommit&&!!commit&&(c.kernelCommit.startsWith(commit)||commit.startsWith(c.kernelCommit))}));
 const headline=evidence.find(e=>diagnostic.test(e.text))?.text.replace(/^\s*\[.*?\]\s*/,'') || '未识别到已支持的内核异常，需要专家补充分析';
 const normalized=lines.map(l=>l.replace(/^\s*\[\s*[\d.]+\]\s*/,''));
 const stableStack=frames.slice(0,8).map(f=>f.symbol).join('|');
 const stableHeadline=headline.replace(/0x[a-f0-9]+|\b\d+\b/g,'#').replace(/task\s+[^\s:]+:?/,'task ');
 const signature=crypto.createHash('sha256').update(category+'|'+(version||'unknown')+'|'+(commit||'unknown')+'|'+stableStack+'|'+stableHeadline+(category==='待专家分析'?'|'+log:'')).digest('hex').slice(0,16);
 return {headline,category,kernelVersion:version,kernelCommit:commit,repository:version?.includes('-next-')?'next':'mainline',evidence,frames,candidates,skills:matched.map(s=>({id:s.id,name:s.name,version:s.version,contributor:s.contributor,team:s.team,guidance:s.guidance})),signature,lineCount:lines.length,engine:'deterministic-triage-v1',limitations:'规则分诊与社区案例检索，尚未接入 LLM 或复现环境。候选根因需核对源码与补丁、复现并人工确认。'};
}
module.exports={analyze,inspect,builtins};
