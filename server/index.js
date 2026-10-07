const express=require('express'),multer=require('multer'),fs=require('fs'),path=require('path'),crypto=require('crypto');
const {execFile}=require('child_process');const {promisify}=require('util');const run=promisify(execFile);
const kernels=require('./kernels');const {analyze,inspect,builtins}=require('./analyzer');
const agent=require('./agent');
const jevRouter=require('./jev-router');
const root=path.join(__dirname,'..'),data=process.env.KERNEL_INSIGHT_DATA_DIR||path.join(root,'data'),uploads=path.join(data,'uploads'),reports=path.join(data,'reports'),benchmarkDir=process.env.KERNEL_BENCHMARK_DIR||path.join(root,'data/benchmark');
for(const p of [data,uploads,reports])fs.mkdirSync(p,{recursive:true});
const statePath=path.join(data,'state.json');let state=fs.existsSync(statePath)?JSON.parse(fs.readFileSync(statePath)): {jobs:[],skills:builtins};
for(const j of state.jobs)if(['queued','running'].includes(j.status)){j.status='failed';j.error='服务重启，请重新提交';}
const save=()=>{fs.writeFileSync(statePath+'.tmp',JSON.stringify(state,null,2));fs.renameSync(statePath+'.tmp',statePath);};
const benchmark=()=>fs.existsSync(path.join(benchmarkDir,'manifest.json'))?JSON.parse(fs.readFileSync(path.join(benchmarkDir,'manifest.json'))):{version:'linux-community-v1',cases:[]};
const app=express();app.use(express.json({limit:'8mb'}));app.use(express.static(path.join(root,'public')));
app.use('/vendor/mermaid',express.static(path.join(root,'node_modules/mermaid/dist')));
app.get('/vendor/highlight.css',(_,res)=>res.sendFile(path.join(root,'node_modules/highlight.js/styles/github.css')));
app.use((req,res,next)=>{if(req.method!=='GET'&&req.headers.origin&&!/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(req.headers.origin))return res.status(403).json({error:'只允许本地工作台写入'});next();});
app.use((req,res,next)=>{
 if(req.method==='POST'&&(/^\/api\/analyze$/.test(req.path)||/^\/api\/benchmark\/[^/]+\/analyze$/.test(req.path))){
  try{const stat=fs.statfsSync(data),available=Number(stat.bavail)*Number(stat.bsize),needed=512*1024*1024+Number(req.headers['content-length']||0);if(available<needed)return res.status(507).json({error:'服务器磁盘空间不足，暂不接收新分析任务；原有报告仍可查看'});}catch(error){return next(error);}
 }
 next();
});
const upload=multer({dest:uploads,limits:{fileSize:64*1024*1024,files:20},fileFilter:(_,f,cb)=>/\.(log|txt|zip|gz|tgz|tar)$/i.test(f.originalname)?cb(null,true):cb(Error('支持 .log .txt .zip .tar .gz .tgz'))});
require('./accounts')(app,{data,state,save});
const materials=require('./materials')(app,{data});
require('./experience').install(app,{state,data});
const taskProgress=require('./task-progress')({state,save});
const ownerId=req=>req.user?.id||null;
for(const j of state.jobs)if(j.error==='服务重启，请重新提交'&&j.agent?.status==='running')taskProgress.step(j,'failed',j.progress||0,j.error,'failed');
app.post('/api/me/claim-skill',(req,res)=>{const id=ownerId(req),s=state.skills.find(s=>s.id===req.body.id);if(!id||!s?.ownerToken||crypto.createHash('sha256').update(String(req.body.token||'')).digest('hex')!==crypto.createHash('sha256').update(s.ownerToken).digest('hex'))return res.status(403).json({error:'投稿凭据不匹配'});if(s.ownerId&&s.ownerId!==id)return res.status(409).json({error:'投稿已绑定其他个人空间'});s.ownerId=id;save();res.json({ok:true});});
app.get('/api/me',(req,res)=>{const id=ownerId(req);if(!id)return res.status(400).json({error:'缺少本地个人标识'});res.json({jobs:state.jobs.filter(j=>j.ownerId===id),skills:state.skills.filter(s=>s.ownerId===id).map(({ownerToken,content,...s})=>s),benchmarkRuns:(state.skillRuns||[]).filter(r=>r.ownerId===id),legacyCount:req.user.role==='admin'?state.jobs.filter(j=>!j.ownerId).length:0});});
const wrap=fn=>(req,res,next)=>Promise.resolve(fn(req,res,next)).catch(next);
const skillWorkflow=require('./skill-workflow')(app,{state,save,data,benchmark,benchmarkDir});
app.get('/api/health',wrap(async(_,res)=>{let llmConnected=false;if(agent.enabled()){try{const native=agent.configuration().transport==='ollama-native',base=(process.env.KERNEL_AGENT_BASE_URL||(native?'http://127.0.0.1:11434':'http://127.0.0.1:11434/v1')).replace(/\/$/,'');const response=await fetch(base+(native?'/api/tags':'/models'),{signal:AbortSignal.timeout(3000)});const models=await response.json();llmConnected=response.ok&&(native?models.models?.some(m=>(m.name||m.model)===agent.configuration().model):models.data?.some(m=>m.id===agent.configuration().model));}catch{}}res.json({ok:true,...agent.configuration(),llmConnected});}));
app.get('/api/benchmark',(_,res)=>{const b=benchmark();res.json({...b,total:b.cases.length});});
app.get('/api/benchmark/:id/log',(req,res)=>{const c=benchmark().cases.find(c=>c.id===req.params.id);if(!c)return res.status(404).json({error:'案例不存在'});res.type('text/plain').sendFile(path.resolve(benchmarkDir,c.logPath));});
app.get('/api/jobs',(req,res)=>res.json(state.jobs.filter(j=>req.user.role==='admin'||j.ownerId===req.user.id)));
app.get('/api/jobs/:id/progress',(req,res)=>{const j=state.jobs.find(j=>j.id===req.params.id);if(!j)return res.status(404).json({error:'任务不存在'});res.json(taskProgress.snapshot(j));});
app.get('/api/jobs/:id/events',(req,res)=>{const j=state.jobs.find(j=>j.id===req.params.id);if(!j)return res.status(404).json({error:'任务不存在'});taskProgress.stream(req,res,j);});
app.get('/api/kernels',(_,res)=>res.json(kernels.list()));
app.get('/api/kernels/:key/source',wrap(async(req,res)=>{
 const k=kernels.list().find(k=>k.key===req.params.key);if(k?.status!=='ready')return res.status(409).json({error:'源码尚未就绪'});
 const file=String(req.query.file||''),line=Number(req.query.line||1);if(!/^[a-zA-Z0-9_./,-]+$/.test(file)||file.startsWith('/')||file.split('/').includes('..')||!Number.isInteger(line)||line<1)return res.status(400).json({error:'非法源码路径或行号'});
 const sourceRoot=fs.realpathSync(k.sourcePath),target=path.resolve(sourceRoot,file);if(!target.startsWith(sourceRoot+path.sep))return res.status(400).json({error:'路径超出源码目录'});
 if(!fs.existsSync(target))return res.status(404).json({error:'该版本源码中不存在此文件'});const real=fs.realpathSync(target);if(!real.startsWith(sourceRoot+path.sep)||!fs.statSync(real).isFile()||fs.statSync(real).size>2*1024*1024)return res.status(400).json({error:'源码文件不可读取'});
 const lines=fs.readFileSync(real,'utf8').split(/\r?\n/);if(line>lines.length)return res.status(400).json({error:'行号超出源码文件范围'});const start=Math.max(1,line-8),end=Math.min(lines.length,line+8);res.json({file,line,version:k.version,commit:k.commit,lines:lines.slice(start-1,end).map((text,i)=>({line:start+i,text}))});
}));
app.post('/api/kernels',wrap(async(req,res)=>res.status(202).json(kernels.ensure(req.body))));
app.get('/api/dashboard',(_,res)=>{
 const submitted=state.jobs.filter(j=>!j.isBenchmark);
 const groups=new Map();for(const j of submitted){const key=j.analysis?.signature||j.id;const prev=groups.get(key);if(!prev||j.status==='resolved'&&prev.status!=='resolved')groups.set(key,j);}
 const jobs=[...groups.values()],resolved=jobs.filter(j=>j.status==='resolved');
 const paired=resolved.filter(j=>Number(j.review?.baselineMinutes)>0);const avg=a=>a.length?a.reduce((s,n)=>s+n,0)/a.length:null;
 const avgBaseline=avg(paired.map(j=>j.review.baselineMinutes)),avgActual=avg(paired.map(j=>(new Date(j.resolvedAt)-new Date(j.createdAt))/60000));
 const categories={};for(const j of jobs){const k=j.analysis?.category||'等待分析';categories[k]=(categories[k]||0)+1;}
 const trend=Array.from({length:7},(_,i)=>{const d=new Date();d.setDate(d.getDate()-6+i);const day=d.toLocaleDateString('en-CA',{timeZone:'Asia/Shanghai'});return {day,total:resolved.filter(j=>new Date(j.resolvedAt).toLocaleDateString('en-CA',{timeZone:'Asia/Shanghai'})===day).length};});
 res.json({total:jobs.length,submitted:submitted.length,resolved:resolved.length,pending:jobs.filter(j=>j.status!=='resolved').length,avgMinutes:avg(resolved.map(j=>(new Date(j.resolvedAt)-new Date(j.createdAt))/60000)),avgBaseline,avgActual,improvement:avgBaseline?100*(1-avgActual/avgBaseline):null,pairedCount:paired.length,duplicates:submitted.length-jobs.length,categories,trend,benchmarkTotal:benchmark().cases.length,readyKernels:kernels.list().filter(k=>k.status==='ready').length,refreshedAt:new Date().toISOString(),definition:'真实上传任务按版本、commit、异常和调用链归并；排除 benchmark 试跑。平均耗时从提交到人工确认；提升率只比较填有人工基线的同一批问题。'});
});
async function readLog(file){
 if(/\.(txt|log)$/i.test(file.originalname))return fs.readFileSync(file.path,'utf8');
 if(/\.gz$/i.test(file.originalname)&&!/(\.tar\.gz|\.tgz)$/i.test(file.originalname)){const zlib=require('zlib');const raw=fs.readFileSync(file.path);try{return zlib.gunzipSync(raw,{maxOutputLength:32*1024*1024}).toString('utf8');}catch{} }
 const {stdout}=await run('tar',['-tf',file.path],{maxBuffer:2*1024*1024,timeout:30000});
 const names=stdout.trim().split(/\r?\n/).filter(n=>/\.(log|txt)$/i.test(n));
 if(!names.length)throw Error('压缩包中未找到 .log / .txt 文件');if(names.length>100)throw Error('单个压缩包最多 100 个日志');
 if(names.some(n=>n.startsWith('/')||n.includes('\\')||n.split('/').includes('..')||/^[A-Za-z]:/.test(n)))throw Error('压缩包路径不安全');
 let combined='';for(const n of names){const r=await run('tar',['-xOf',file.path,'--',n],{maxBuffer:32*1024*1024,timeout:30000});combined+=`\n# FILE: ${n}\n${r.stdout}`;if(Buffer.byteLength(combined)>32*1024*1024)throw Error('解压日志超过 32MB');}return combined;
}
function createJob(name,options={}){const j={id:crypto.randomUUID(),name,createdAt:new Date().toISOString(),status:'queued',progress:0,ownerId:options.ownerId||null,benchmarkCaseId:options.benchmarkCaseId||null,machine:options.machine||'未指定机器',isBenchmark:!!options.isBenchmark,reportReady:false};state.jobs.unshift(j);taskProgress.step(j,'queued',0,'任务已接收，等待分析执行','queued');return j;}
function report(j){const a=j.analysis;return [`# ${j.name}`,``, `状态：${j.status} · 分析引擎：${a.engine}`,``, `## 初步定位`,a.headline,`类别：${a.category}；内核：${a.kernelVersion||'未识别'}；commit：${a.kernelCommit||'未识别'}`,``, `## 分析选用组合`,`组合：${j.skillSelection?.preset||'recommended'}；Skill ID：${(j.skillSelection?.ids||[]).join(', ')}`,``, `## Skill 贡献者`,...a.skills.map(s=>`- ${s.name} v${s.version} — ${s.contributor} / ${s.team}\n  ${s.guidance}`),``, `## 日志证据`,...a.evidence.map(e=>`- L${e.line}: ${e.text}`),``, `## 社区候选根因（待核实）`,...a.candidates.map(c=>`- ${c.rootCause}\n  来源：${c.sourceUrl}\n  修复：${c.fixTitle} (${c.fix})\n  匹配依据：${c.matchBasis}`),``, ...(a.agent?[`## dsh / Qwen 分析`,`模型：${a.agent.model}；${a.agent.harness}；耗时 ${a.agent.elapsedSeconds} 秒`,a.agent.summary,...a.agent.hypotheses.map(h=>`- ${h.cause}（${h.confidence}）\n  日志行号：${h.evidenceLines.join(", ")}\n  验证：${h.verification}`),`### 后续步骤`,...a.agent.nextSteps.map(s=>`- ${s}`),`### 模型限制`,...a.agent.limitations.map(s=>`- ${s}`)]:[]),`## 分析边界`,a.limitations,``, `输入 SHA256：${j.inputHash}`,j.review?`审核：${j.review.note}；人工基线：${j.review.baselineMinutes||'未填'} 分钟`: '尚未人工确认'].join('\n');}
async function processJob(j,log,options={}){
 try{j.status='running';taskProgress.step(j,'reading',10,'正在读取和校验输入日志');await new Promise(r=>setImmediate(r));if(!log.trim()||log.includes('\u0000'))throw Error('请提供非空文本日志');j.inputHash=crypto.createHash('sha256').update(log).digest('hex');fs.writeFileSync(path.join(reports,j.id+'.log'),log);
 taskProgress.step(j,'extracting',30,'提取异常特征、版本和调用链');await new Promise(r=>setImmediate(r));
 const inspection=inspect(log);taskProgress.step(j,'matching',55,'匹配选定 Skill 和社区修复案例');await new Promise(r=>setImmediate(r));j.analysis=analyze(log,options.selectedSkills||state.skills,benchmark().cases,inspection);j.skillSelection={preset:options.skillPreset||'recommended',ids:(options.selectedSkills||state.skills.filter(s=>s.status==='active')).map(s=>s.id)};j.progress=70;
 const previous=state.jobs.find(x=>x.id!==j.id&&x.ownerId===j.ownerId&&!x.isBenchmark&&x.analysis?.signature===j.analysis.signature);if(previous)j.duplicateOf=previous.id;
 const spec=options.sourceSpec || {version:j.analysis.kernelVersion,commit:j.analysis.kernelCommit,repository:options.repository||j.analysis.repository};
 taskProgress.step(j,'source',75,options.autoSource!==false?'解析源码版本并提交缓存下载任务':'本次未启用源码下载');await new Promise(r=>setImmediate(r));
 if(options.autoSource!==false){try{j.kernelKey=kernels.ensure(spec).key;}catch(e){j.sourceError=e.message;}}
 if(agent.enabled()){
  j.agentSourceSpec=spec;
  if(jevRouter.enabled()&&agent.configuration().engine!=='closed-loop'){taskProgress.step(j,'routing',78,'SGLang 正在进行结构化多问题分诊');try{j.analysis.routing=await jevRouter.route(log);}catch(e){j.analysis.routingError=e.message;}}
  j.agentName=agent.configuration().engine+' · '+agent.configuration().model;taskProgress.step(j,'agent',80,'排队进入定位 Agent 模型分析');
  const output=await agent.execute({job:j,log,skills:options.selectedSkills||state.skills.filter(s=>s.status==='active'),data,stageMaterials:dir=>materials.stage(options.materials,dir),onEvent:event=>taskProgress.activity(j,event.message,event.phase)});
  j.analysis.ruleCategory=j.analysis.category;j.analysis.category=output.category;j.analysis.agent=output;j.analysis.engine=agent.configuration().engine;j.analysis.limitations='dsh / Qwen 根据日志与选定经验生成待验证假设；社区候选另行检索，未向模型提供 Benchmark 答案。需要核对精确版本源码、符号信息与复现结果。';
 }
 taskProgress.step(j,'report',90,'整理证据与贡献者署名，生成报告');await new Promise(r=>setImmediate(r));
 j.status='needs_review';j.progress=100;j.reportReady=true;j.analyzedAt=new Date().toISOString();j.analysisSeconds=(Date.now()-new Date(j.createdAt))/1000;fs.writeFileSync(path.join(reports,j.id+'.md'),report(j));taskProgress.step(j,'complete',100,'分析已完成，等待人工核对与验证','completed');
 }catch(e){j.status='failed';j.error=e.message;taskProgress.step(j,'failed',j.progress||0,e.message,'failed');}
}
const engineFingerprint=crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,'analyzer.js'))).update(agent.identity()).digest('hex');
function enqueueAnalysis(name,log,options,force=false){
 const fingerprint=crypto.createHash('sha256').update(JSON.stringify({owner:options.ownerId,preset:options.skillPreset||'recommended',log:log.replace(/\r\n/g,'\n').trimEnd(),skills:(options.selectedSkills||state.skills.filter(s=>s.status==='active')).map(({id,version,category,patterns,guidance})=>({id,version,category,patterns,guidance})),source:options.sourceSpec||null,materials:options.materials||null,repository:options.repository||null,autoSource:!!options.autoSource,benchmark:!!options.isBenchmark,caseId:options.benchmarkCaseId||null,dataset:benchmark(),engine:engineFingerprint})).digest('hex');
 const previous=state.jobs.find(j=>j.dedupKey===fingerprint&&j.status!=='failed'&&(['queued','running'].includes(j.status)||j.reportReady));
 if(previous&&(!force||['queued','running'].includes(previous.status))){previous.reuseCount=(previous.reuseCount||0)+1;previous.lastSubmittedAt=new Date().toISOString();previous.submissions=previous.submissions||[];previous.submissions.push({name,machine:options.machine||'',at:previous.lastSubmittedAt});save();return {...previous,reused:true};}
 const j=createJob(name,options);j.materials=options.materials?{id:options.materials.id,files:options.materials.files}:null;j.dedupKey=fingerprint;j.reuseCount=0;j.submissions=[{name,machine:options.machine||'',at:j.createdAt}];save();setImmediate(()=>processJob(j,log,options));return {...j,reused:false};
}
app.post('/api/analyze',upload.array('logs',20),wrap(async(req,res)=>{
 if(!req.files?.length&&!req.body.logText?.trim())return res.status(400).json({error:'请选择日志或粘贴日志内容'});
 const options={ownerId:ownerId(req),machine:String(req.body.machine||'').slice(0,120),autoSource:req.body.autoSource!=='false',repository:['stable','next'].includes(req.body.repository)?req.body.repository:null,sourceSpec:req.body.kernelCommit||req.body.kernelVersion?{version:req.body.kernelVersion,commit:req.body.kernelCommit,repository:req.body.repository||'mainline'}:null};
 options.selectedSkills=skillWorkflow.select(req.body).map(s=>({...s,patterns:[...s.patterns]}));options.skillPreset=req.body.skillPreset||'recommended';
 options.materials=materials.resolve(req.body.materialsId,req.user);
 const submitted=[];for(const f of req.files||[]){try{submitted.push(enqueueAnalysis(f.originalname,await readLog(f),options,req.body.forceRerun==='true'||req.body.forceRerun===true));}finally{fs.unlinkSync(f.path);}}
 if(req.body.logText?.trim())submitted.push(enqueueAnalysis('粘贴的 kernel 日志',req.body.logText,options,req.body.forceRerun==='true'||req.body.forceRerun===true));res.status(202).json(submitted);
}));
app.post('/api/benchmark/:id/analyze',wrap(async(req,res)=>{const c=benchmark().cases.find(x=>x.id===req.params.id);if(!c)return res.status(404).json({error:'案例不存在'});const options={isBenchmark:true,ownerId:ownerId(req),benchmarkCaseId:c.id,machine:'社区 benchmark',autoSource:req.body.autoSource===true,sourceSpec:{version:c.kernelVersion,commit:c.kernelCommit,repository:c.repository},selectedSkills:skillWorkflow.select({}).map(s=>({...s,patterns:[...s.patterns]}))};res.status(202).json(enqueueAnalysis(c.id+' · '+c.symbol,fs.readFileSync(path.join(benchmarkDir,c.logPath),'utf8'),options,req.body.forceRerun===true));}));
app.get('/api/reports/:id',(req,res)=>{const j=state.jobs.find(x=>x.id===req.params.id);if(!j?.analysis)return res.status(404).json({error:'报告未就绪'});res.type('text/markdown').send(report(j));});
app.get('/api/jobs/:id/evidence',(req,res)=>{const j=state.jobs.find(x=>x.id===req.params.id);if(!j?.analysis?.agent?.evidence)return res.status(404).json({error:'工具证据尚未生成'});res.json(j.analysis.agent.evidence);});
app.get('/api/jobs/:id/log',(req,res)=>{const j=state.jobs.find(x=>x.id===req.params.id);if(!j?.reportReady)return res.status(404).json({error:'日志不存在'});res.type('text/plain').sendFile(path.join(reports,j.id+'.log'));});
app.post('/api/jobs/:id/review',wrap(async(req,res)=>{const j=state.jobs.find(x=>x.id===req.params.id);if(!j?.reportReady)return res.status(409).json({error:'报告尚未就绪'});if(!String(req.body.note||'').trim())return res.status(400).json({error:'请填写验证结论或退回原因'});const baseline=req.body.baselineMinutes===''||req.body.baselineMinutes==null?null:Number(req.body.baselineMinutes);if(baseline!==null&&(!Number.isFinite(baseline)||baseline<=0))return res.status(400).json({error:'人工基线必须大于 0'});if(typeof req.body.accepted!=='boolean')return res.status(400).json({error:'审核结果必须是布尔值'});const rating=req.body.rating===''||req.body.rating==null?null:Number(req.body.rating);if(rating!==null&&(!Number.isInteger(rating)||rating<1||rating>5))return res.status(400).json({error:'满意度评分必须为 1–5 的整数'});j.review={rating,accepted:req.body.accepted,note:String(req.body.note).slice(0,4000),baselineMinutes:baseline,at:new Date().toISOString()};j.status=j.review.accepted?'resolved':'needs_expert';if(j.review.accepted)j.resolvedAt=j.resolvedAt||new Date().toISOString();else delete j.resolvedAt;taskProgress.settle(j);res.json(j);}));
app.use('/api',(_,res)=>res.status(404).json({error:'API 不存在'}));
app.use((err,req,res,next)=>res.status(err instanceof multer.MulterError?413:400).json({error:err.message}));
app.get('*',(_,res)=>res.sendFile(path.join(root,'public/index.html')));
const port=process.env.PORT||8787;if(require.main===module)app.listen(port,'127.0.0.1',()=>console.log(`Kernel Insight: http://localhost:${port}`));
module.exports=app;
