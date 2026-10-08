const fs=require('fs'),path=require('path'),crypto=require('crypto'),{spawn}=require('child_process');
const enabled=()=>process.env.KERNEL_AGENT_MODE==='dsh';
const configuration=()=>({enabled:enabled(),engine:enabled()?(process.env.KERNEL_AGENT_ENGINE==='closed-loop'?'closed-loop':'dsh-qwen'):'deterministic-triage-v1',model:process.env.KERNEL_AGENT_MODEL||'qwen3.8:27b-256k',provider:process.env.KERNEL_AGENT_PROVIDER||'ollama',transport:process.env.KERNEL_AGENT_TRANSPORT||'openai',timeoutSeconds:Number(process.env.KERNEL_AGENT_TIMEOUT_SECONDS||240)});
const identity=()=>crypto.createHash('sha256').update(JSON.stringify({...configuration(),endpoint:process.env.KERNEL_AGENT_BASE_URL,router:process.env.KERNEL_ROUTER_BASE_URL,verifiedSourceRegistry:process.env.KERNEL_VERIFIED_SOURCE_REGISTRY&&fs.existsSync(process.env.KERNEL_VERIFIED_SOURCE_REGISTRY)?crypto.createHash('sha256').update(fs.readFileSync(process.env.KERNEL_VERIFIED_SOURCE_REGISTRY)).digest('hex'):null})).update(fs.readFileSync(__filename)).update(fs.readFileSync(path.join(__dirname,'agent-source.js'))).update(fs.readFileSync(path.join(__dirname,'agent-report.js'))).update(fs.readFileSync(path.join(__dirname,'../tools/kernel-debug/diagnostic-methods.md'))).update(fs.readFileSync(path.join(__dirname,'jev-router.js'))).update(fs.readFileSync(path.join(__dirname,'../scripts/agent-runner.py'))).update(fs.readFileSync(path.join(__dirname,'../scripts/localization_agent.py'))).update(fs.readFileSync(path.join(__dirname,'../scripts/kernel_triage.py'))).update(fs.readFileSync(path.join(__dirname,'../scripts/kernel_artifacts.py'))).update(fs.readFileSync(path.join(__dirname,'../scripts/dump-query.py'))).update(fs.readFileSync(path.join(__dirname,'materials.js'))).digest('hex');
let active=0;const waiting=[];
async function acquire(){if(active>=Number(process.env.KERNEL_AGENT_CONCURRENCY||1))await new Promise(resolve=>waiting.push(resolve));else active++;}
function release(){const next=waiting.shift();if(next)next();else active--;}
async function execute({job,log,skills,data,onEvent,stageMaterials}){
 await acquire();
 try{
  const dir=path.join(data,'agent-runs',job.id);fs.mkdirSync(dir,{recursive:true});
  stageMaterials?.(dir);
  fs.writeFileSync(path.join(dir,'input.log'),log);fs.writeFileSync(path.join(dir,'skills.json'),JSON.stringify(skills.map(({id,name,version,category,guidance,patterns,contributor,content})=>({id,name,version,category,guidance,patterns,contributor,content})),null,2));
  let guidanceBudget=4000;
  fs.writeFileSync(path.join(dir,'skills-brief.json'),skills.slice(0,12).map(s=>{const guidance=String(s.guidance||'').slice(0,Math.max(0,Math.min(600,guidanceBudget)));guidanceBudget-=guidance.length;return JSON.stringify({id:s.id,name:s.name,contributor:s.contributor,category:s.category,guidance});}).join('\n'));
  onEvent?.({type:'progress',message:'正在按精确版本获取日志涉及的源码文件'});
  const sources=await require('./agent-source').prepare(log,job.agentSourceSpec,dir);
  fs.copyFileSync(path.join(__dirname,'../tools/kernel-debug/diagnostic-methods.md'),path.join(dir,'diagnostic-methods.md'));
  const request={workspace:dir,engine:configuration().engine,eagerBoundary:configuration().engine==='closed-loop',sourceTriage:configuration().engine==='closed-loop',transport:configuration().transport,model:configuration().model,baseUrl:process.env.KERNEL_AGENT_BASE_URL||(configuration().transport==='ollama-native'?'http://127.0.0.1:11434':'http://127.0.0.1:11434/v1'),timeout:configuration().timeoutSeconds,sourceRoot:job.agentSourceRoot||null};
  if(process.env.KERNEL_BOUNDARY_ROUTER==='decision'&&process.env.KERNEL_DECISION_BASE_URL)request.boundaryRouter={baseUrl:process.env.KERNEL_DECISION_BASE_URL,timeout:15,api:process.env.KERNEL_DECISION_API||'decisions'};
  else if(process.env.KERNEL_DECISION_BASE_URL)request.decisionPlugin={baseUrl:process.env.KERNEL_DECISION_BASE_URL,policy:'adaptive'};
  if(job.agentProfile){
   request.userPrompt=job.agentProfile.prompt;
   if(job.agentProfile.agentId==='chat-investigator'){delete request.boundaryRouter;delete request.decisionPlugin;request.fastFinal=false;}
  }else request.userPrompt=skills.map(s=>`Skill ${s.name}: ${s.guidance||''}`).join('\n\n').slice(0,30000);
  fs.writeFileSync(path.join(dir,'request.json'),JSON.stringify(request));
  const python=process.env.KERNEL_AGENT_PYTHON||'python3',runner=path.join(__dirname,'../scripts/agent-runner.py');
  let command=python,args=[runner,path.join(dir,'request.json')];
  if(process.env.KERNEL_AGENT_SANDBOX){command=process.env.KERNEL_AGENT_SANDBOX;args=[dir,python,runner,path.join(dir,'request.json')];}
  const result=await new Promise((resolve,reject)=>{
   const child=spawn(command,args,{cwd:dir,env:{...process.env,HOME:dir,DSH_HOME:path.join(dir,'dsh-home'),PYTHONDONTWRITEBYTECODE:'1'},windowsHide:true,stdio:['ignore','pipe','pipe']});let buffer='',stderr='',final=null,settled=false;
   const timeout=setTimeout(()=>{child.kill('SIGTERM');reject(Error('dsh 模型分析超过时间限制'));},(request.timeout+75)*1000);
   child.stdout.on('data',chunk=>{buffer+=chunk.toString();if(buffer.length>2*1024*1024){child.kill();return;}let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);try{const event=JSON.parse(line);if(event.type==='result')final=event;else if(event.type==='progress')onEvent?.(event);}catch{}}});
   child.stderr.on('data',chunk=>stderr=(stderr+chunk.toString()).slice(-6000));
   child.on('error',error=>{clearTimeout(timeout);reject(error);});child.on('close',code=>{clearTimeout(timeout);if(code!==0||!final?.analysis)return reject(Error(final?.error||'dsh 执行失败：'+stderr.slice(-1200)));resolve(final);});
  });
  const normalized=require('./agent-report').normalize(result.analysis,log.split(/\r?\n/).length,result.evidence);
  normalized.limitations=[...new Set([...(result.evidence?.gaps||[]),...normalized.limitations])].slice(0,16);
  return {...normalized,firstScene:result.analysis.firstScene,localization:result.analysis.localization,metrics:result.metrics,model:request.model,provider:configuration().provider,harness:result.harness,finishReason:result.finishReason,attempts:result.attempts,firstFinishReason:result.firstFinishReason,toolCalls:result.toolCalls||[],elapsedSeconds:result.elapsedSeconds,evidence:result.evidence,sourceFiles:sources.files,sourceErrors:sources.errors,benchmarkGroundTruthProvided:false};
 }finally{release();}
}
const decisionIdentity=()=>{
 const hash=crypto.createHash('sha256').update(identity()).update(process.env.KERNEL_DECISION_BASE_URL||'disabled').update(process.env.KERNEL_BOUNDARY_ROUTER||'adaptive').update(process.env.KERNEL_DECISION_API||'decisions').update(process.env.KERNEL_DECISION_MODEL||'default');
 for(const name of ['../scripts/boundary_router.py','../scripts/decision_plugin.py','../plugins/kernel-decision/manifest.json','../plugins/kernel-decision/index.mjs']){
  const file=path.join(__dirname,name);if(fs.existsSync(file))hash.update(fs.readFileSync(file));
 }
 return hash.digest('hex');
};
async function withSlot(work){await acquire();try{return await work();}finally{release();}}
module.exports={enabled,configuration,identity:decisionIdentity,execute,withSlot};
