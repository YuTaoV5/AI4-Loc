const fs=require('fs'),path=require('path');
const {present}=require('./trace-presentation');
const LIMIT=2*1024*1024;
// Never return raw model messages, request headers, prompts or reasoning.
function clean(value,workspace,depth=0){
 if(depth>8)return '[深度截断]';
 if(typeof value==='string')return value.replaceAll(workspace,'<workspace>').replace(/<think>[\s\S]*?(?:<\/think>|$)/gi,'[推理内容已隐藏]').replace(/Bearer\s+[^\s"']+/gi,'Bearer [已隐藏]').replace(/((?:password|api[_-]?key|access[_-]?token)\s*[=:]\s*)[^\s,;]+/gi,'$1[已隐藏]').replace(/\b(?:sk-[\w-]{16,}|gh[pousr]_[\w]{20,})\b/g,'[密钥已隐藏]').slice(0,6000);
 if(Array.isArray(value))return value.slice(0,depth===0?300:100).map(v=>clean(v,workspace,depth+1));
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).slice(0,100).filter(([k])=>!/(?:authorization|cookie|password|secret|api.?key|headers|reasoning|thinking)|^(?:token|accessToken|refreshToken|prompt|messages|rawResponse|state)$/i.test(k)).map(([k,v])=>[k,clean(v,workspace,depth+1)]));
 return value;
}
function readTrace(data,job){
 const workspace=path.join(data,'agent-runs',job.id),warnings=[],entries=[];
 function read(name,jsonl=false){
  const file=path.join(workspace,name);
  try{
   // Trace paths are a fixed allowlist; refuse links escaping the task directory.
   if(fs.realpathSync(workspace)!==path.resolve(workspace)||fs.lstatSync(file).isSymbolicLink())throw Error('unsafe');
   const stat=fs.statSync(file);if(!stat.isFile())throw Error('unsafe');
   if(stat.size>LIMIT){warnings.push(name+' 过大，未加载');return jsonl?[]:null;}
   const text=fs.readFileSync(file,'utf8');
   if(jsonl)return text.split('\n').filter(Boolean).flatMap(line=>{try{return [JSON.parse(line)];}catch{return [];}}).slice(-300);
   return JSON.parse(text);
  }catch(e){if(e.code!=='ENOENT')warnings.push(name+' 暂不可读，请刷新');return jsonl?[]:null;}
 }
 const decisions=read('decision-trace.json')?.calls||[];
 for(const [i,row] of decisions.entries()){
  const request=row.request||{},response=row.response||row.rawResponse||{};
  const questions=row.questions|| (Array.isArray(request.questions)?request.questions:Object.entries(request.questions||{}).map(([id,q])=>({id,type:q.type,question:q.instructions,options:Object.entries(q.criteria||{}).map(([name,description])=>({name,description}))})));
  entries.push({id:'decision-'+i,kind:'decision',name:'Decision '+(row.endpoint||''),startedAt:row.startedAt,status:row.status,seconds:row.seconds,error:row.error,usage:response.usage,
   questions:questions.map(q=>{const a=response.answers?.[q.id]||{};return {id:q.id,type:q.type,question:q.question,options:q.options,levels:q.levels,answer:{choice:a.choice,score:a.score,noul:a.noul,probabilities:a.probabilities,labelMass:a.label_mass??a.x_label_mass}};})});
 }
 let calls=read('api-calls.jsonl',true);
 if(!calls.length)calls=job.analysis?.agent?.metrics?.requests||[];
 const models=new Map();for(const row of calls)models.set(row.index,row);
 for(const row of models.values())entries.push({id:'api-'+row.index,kind:'api',name:row.model||'Chat API',startedAt:row.startedAt,status:row.status,seconds:row.seconds,usage:row.usage,error:row.error,selection:row.selection,reportAccepted:row.reportAccepted,reportSummary:row.reportSummary,reportLocations:row.reportLocations});
 let tools=read('tool-trace.jsonl',true);if(!tools.length)tools=job.analysis?.agent?.evidence?.commands||[];
 for(const row of tools)entries.push({id:'tool-'+row.id,kind:'tool',name:row.tool,startedAt:row.startedAt,status:row.result?.error?'error':'returned',error:row.result?.error,seconds:row.seconds,arguments:row.arguments,result:row.result,origin:row.origin,modelRequestIndex:row.modelRequestIndex});
 for(const [i,row] of read('dsh-trace.jsonl',true).entries())entries.push({id:'dsh-'+i,kind:'dsh',name:row.name||row.type,eventType:row.type,startedAt:row.startedAt,status:row.status||row.type,arguments:row.arguments,result:row.result,error:row.error});
 entries.sort((a,b)=>a.startedAt&&b.startedAt?a.startedAt.localeCompare(b.startedAt):0);
 const readable=entries.slice(-300).map(row=>{const view=present(row);delete view.arguments;delete view.result;delete view.reportLocations;delete view.reportSummary;for(const q of view.questions||[])delete q.answer.labelMass;return view;});
 return {schema:'agent-call-trace/v2',jobId:job.id,entries:clean(readable,workspace),warnings,probabilitiesCalibrated:false,chronologyComplete:entries.every(x=>!!x.startedAt),
  note:'记录实际接口选择与工具发现，不包含模型内部推理。Decision 概率表示选项相对偏好，不是根因正确率。旧任务缺失的调用和选择无法回填。',running:['queued','running'].includes(job.status)};
}
module.exports={readTrace};
