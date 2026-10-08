const fs=require('fs'),path=require('path'),crypto=require('crypto'),os=require('os'),{spawn,spawnSync}=require('child_process');
const scoring=require('./benchmark-score'),agent=require('./agent');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
module.exports=function(app,{state,save,data,profiles}){
 state.agentBenchmarkRuns ||= [];
 for(const r of state.agentBenchmarkRuns)if(['queued','running'].includes(r.status)){r.status='failed';r.error='服务重启中断；未完成结果不入榜';r.completedAt=new Date().toISOString();}
 let draining=false,current=null;
 const directory=process.env.KERNEL_BENCHMARK_DATASET;
 function suite(){
  const rules=scoring.RULES;let reason=null,m=null,ann=null,manifestSha=null,annotationsSha=null;
  if(process.platform!=='linux')reason='独立沙箱评测需要 Linux + bubblewrap；Windows 可管理组合和查看榜单，完整评测可部署于 Linux / WSL2。';
  else if(!agent.enabled()||agent.configuration().engine!=='closed-loop')reason='需要启用 closed-loop 定位引擎';
  else if(!directory)reason='管理员尚未配置 KERNEL_BENCHMARK_DATASET';
  try{if(directory){const raw=fs.readFileSync(path.join(directory,'manifest.json'));m=JSON.parse(raw);manifestSha=sha(raw);const p=path.join(directory,'benchmark-annotations.json');if(fs.existsSync(p)){const bytes=fs.readFileSync(p);ann=JSON.parse(bytes);annotationsSha=sha(bytes);}}}catch{reason='测试集或评分标注不可读取，请检查服务账号权限';}
  if(!reason&&spawnSync('bwrap',['--version'],{timeout:3000,windowsHide:true}).status!==0)reason='bubblewrap 不可用，禁止退回无隔离评测';
  const cases=(m?.cases||[]).filter(c=>c.status==='ready'&&c.split==='test');
  if(!reason&&!cases.length)reason='没有 ready test 样本';
  const annotated=cases.filter(c=>ann?.cases?.[c.id]?.status==='collector_verified'&&ann.cases[c.id].rawLogSha256===c.files?.rawLog?.sha256).length;
  const config={...agent.configuration(),maxModelCalls:8,timeoutSeconds:240,hardware:process.env.KERNEL_BENCHMARK_HARDWARE_ID||`${process.platform}/${process.arch}/${os.hostname()}`,decisionApi:process.env.KERNEL_DECISION_API||'decisions',decisionModel:process.env.KERNEL_DECISION_MODEL||'server-default',decisionEndpoint:process.env.KERNEL_DECISION_BASE_URL||null};
  const driver=path.join(__dirname,'../scripts/run-web-benchmark.py');
  const hashes=['benchmark-score.js','../scripts/run-web-benchmark.py','../scripts/run-localization-benchmark.py','../scripts/benchmark-worker.py','../tools/kernel-lab/dataset_contract.py'].map(f=>sha(fs.readFileSync(path.join(__dirname,f))));
  const cohort=sha(JSON.stringify({manifestSha,annotationsSha,config,engine:agent.identity(),hashes,scoring:scoring.VERSION}));
  if(!reason&&!process.env.KERNEL_DECISION_BASE_URL)reason='尚未配置 Decision 接口；请由管理员配置后再跑完整组合比较';
  return {available:!reason,reason,caseCount:cases.length,annotationCoverage:annotated,cohort,datasetSha256:manifestSha,annotationsSha256:annotationsSha,caseIds:cases.map(c=>c.id),dataset:m?.name||m?.schema||'未配置',evaluationType:'公开注入集练习评测，非盲测',rules,configuration:config,driver};
 }
 const visible=r=>{const {directory:privateDirectory,...safe}=r;return safe;};
 const mine=req=>state.agentBenchmarkRuns.filter(r=>r.ownerId===req.user.id).map(visible);
 function owned(req,res){const r=state.agentBenchmarkRuns.find(r=>r.id===req.params.id);if(!r){res.status(404).json({error:'评测记录不存在'});return null;}if(r.ownerId!==req.user.id&&req.user.role!=='admin'){res.status(403).json({error:'无权访问其他用户的评测明细'});return null;}return r;}
 async function drain(){
  if(draining)return;draining=true;
  try{for(;;){const r=state.agentBenchmarkRuns.find(r=>r.status==='queued');if(!r)break;
   try{await agent.withSlot(async()=>{
    if(r.status!=='queued')return;r.status='running';r.startedAt=new Date().toISOString();r.queueSeconds=(Date.now()-Date.parse(r.createdAt))/1000;save();
    const control={dataset:directory,output:r.directory,caseIds:r.caseIds,datasetSha256:r.datasetSha256,annotationsSha256:r.annotationsSha256,profile:r.profile,decisionBaseUrl:process.env.KERNEL_DECISION_BASE_URL,decisionApi:r.configuration.decisionApi,agent:{model:r.configuration.model,baseUrl:process.env.KERNEL_AGENT_BASE_URL||(r.configuration.transport==='ollama-native'?'http://127.0.0.1:11434':'http://127.0.0.1:11435/v1'),transport:r.configuration.transport,timeout:240,maxModelCalls:8}};
    fs.mkdirSync(r.directory,{recursive:true,mode:0o700});const file=path.join(r.directory,'control.json');fs.writeFileSync(file,JSON.stringify(control),{mode:0o600});
    await new Promise((resolve,reject)=>{
     const child=spawn(process.env.KERNEL_AGENT_PYTHON||'python3',[path.join(__dirname,'../scripts/run-web-benchmark.py'),file],{cwd:path.join(__dirname,'..'),env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},detached:process.platform==='linux',windowsHide:true,stdio:['ignore','pipe','pipe']});
     current={run:r,child};let buffer='',errors='';const log=fs.createWriteStream(path.join(r.directory,'evaluator.log'),{mode:0o600});
     const timer=setTimeout(()=>{try{process.kill(-child.pid,'SIGKILL');}catch{child.kill();}reject(Error('整套评测超时'));},r.caseIds.length*300000+120000);
     child.stdout.on('data',bytes=>{log.write(bytes);buffer+=bytes.toString();if(buffer.length>1024*1024){buffer='';child.kill();return;}let end;while((end=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,end);buffer=buffer.slice(end+1);try{const e=JSON.parse(line);if(e.type==='progress'){r.progress={completed:e.completed,total:e.total,message:e.message};save();}}catch{}}});
     child.stderr.on('data',bytes=>{log.write(bytes);errors=(errors+bytes.toString()).slice(-3000);});
     child.on('error',e=>{clearTimeout(timer);log.end();reject(e);});child.on('close',code=>{clearTimeout(timer);log.end();current=null;code===0?resolve():reject(Error('沙箱评测失败；'+errors.slice(-1200)));});
    });
    if(r.status==='cancelled')return;
    const result=JSON.parse(fs.readFileSync(path.join(r.directory,'results.json'),'utf8'));
    if(!result.complete||result.rows.length!==r.caseIds.length||result.rows.some((row,i)=>row.caseId!==r.caseIds[i])||result.datasetSha256!==r.datasetSha256||result.annotationsSha256!==r.annotationsSha256)throw Error('固定套件结果不完整或指纹不匹配');
    r.rows=result.rows;r.wallSeconds=result.wallSeconds;r.score=scoring.score(result.rows);r.status='completed';r.completedAt=new Date().toISOString();save();
   });}catch(e){if(r.status!=='cancelled'){r.status='failed';r.error=e.message;r.completedAt=new Date().toISOString();}save();}
  }}finally{draining=false;}
 }
 app.get('/api/benchmark/suite',(_,res)=>{const {driver,caseIds,...s}=suite();res.json(s);});
 app.get('/api/benchmark/leaderboard',(req,res)=>{const s=suite();res.json({cohort:s.cohort,rows:scoring.leaderboard(state.agentBenchmarkRuns.filter(r=>r.publish===true),s.cohort),rules:scoring.RULES,evaluationType:s.evaluationType});});
 app.get('/api/benchmark/runs',(req,res)=>res.json(mine(req)));
 app.get('/api/benchmark/runs/:id',(req,res)=>{const r=owned(req,res);if(r)res.json(visible(r));});
 app.get('/api/benchmark/runs/:id/export',(req,res)=>{const r=owned(req,res);if(r)res.set('Content-Disposition',`attachment; filename="benchmark-${r.id}.json"`).json(visible(r));});
 app.post('/api/benchmark/runs',(req,res)=>{
  const p=profiles.select(req);if(!p)return res.status(400).json({error:'请先选择个人空间保存的 Agent / Skill Prompt'});
  const s=suite();if(!s.available)return res.status(409).json({error:s.reason});
  const existing=state.agentBenchmarkRuns.find(r=>r.ownerId===req.user.id&&['queued','running'].includes(r.status));if(existing)return res.status(409).json({error:'已有排队或执行中的评测',runId:existing.id});
  if(state.agentBenchmarkRuns.filter(r=>['queued','running'].includes(r.status)).length>=10)return res.status(429).json({error:'评测队列已满，请稍后提交'});
  const stat=fs.statfsSync(data);if(Number(stat.bavail)*Number(stat.bsize)<512*1024*1024)return res.status(507).json({error:'磁盘空间不足'});
  const r={id:crypto.randomUUID(),ownerId:req.user.id,username:req.user.username,displayName:req.user.displayName,profile:p,status:'queued',createdAt:new Date().toISOString(),publish:req.body.publish===true,cohort:s.cohort,datasetSha256:s.datasetSha256,annotationsSha256:s.annotationsSha256,caseIds:s.caseIds,configuration:s.configuration,score:null,progress:{completed:0,total:s.caseCount,message:'等待独立沙箱和模型执行槽'}};
  r.directory=path.join(data,'agent-benchmarks',r.id);state.agentBenchmarkRuns.unshift(r);save();setImmediate(drain);res.status(202).json(visible(r));
 });
 app.post('/api/benchmark/runs/:id/cancel',(req,res)=>{const r=owned(req,res);if(!r)return;if(!['queued','running'].includes(r.status))return res.status(409).json({error:'该评测已结束'});r.status='cancelled';r.completedAt=new Date().toISOString();if(current?.run.id===r.id){try{process.kill(-current.child.pid,'SIGTERM');}catch{current.child.kill();}}save();res.json(visible(r));});
 return {mine};
};
