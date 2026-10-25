const fs=require('fs'),path=require('path'),crypto=require('crypto');
const agent=require('./agent');
const fingerprint=skills=>crypto.createHash('sha256').update(JSON.stringify(skills.map(({id,version,category,patterns,guidance,content})=>({id,version,category,patterns,guidance,content})))).digest('hex');
const engineIdentity=()=>crypto.createHash('sha256').update(agent.identity()).update(fs.readFileSync(__filename)).digest('hex');

async function run({skill,baseline,proposed,snapshot,data,onProgress}){
 const runId=crypto.randomUUID(),agentFingerprint=engineIdentity(),directory=path.join(data,'skill-pulls',skill.id,'agent-evaluations',runId);
 fs.mkdirSync(directory,{recursive:true,mode:0o700});
 const cases=[...snapshot.cases,{id:'NEGATIVE-001',category:'待专家分析',log:'Linux version 6.6\nBoot complete. All tests completed successfully.\n'}];
 const results=[];let completed=0;
 for(const item of cases){
  const caseId=crypto.randomUUID(),row={id:item.id,expected:item.category};
  for(const [variant,skills] of [['baseline',baseline],['candidate',proposed]]){
   onProgress?.({completed,total:cases.length*2,message:`完整 Agent：${completed+1}/${cases.length*2} · ${variant==='baseline'?'原 Skill 集合':'候选 Skill 集合'}`});
   const scene=require('./analyzer').inspect(item.log);
   const job={id:crypto.randomUUID(),agentSourceSpec:{version:scene.version,commit:scene.commit,repository:scene.version?.includes('-next-')?'next':'mainline'},agentProfile:{agentId:'chat-investigator',prompt:'Investigate the supplied incident using the complete selected Skill snapshots. Follow the standard diagnostic JSON schema; do not read benchmark labels or expected answers.'},agentBudget:{timeout:240,maxModelCalls:8}};
   let output=null,error=null;
   try{output=await agent.execute({job,log:item.log,skills,data,onEvent:event=>onProgress?.({completed,total:cases.length*2,message:event.message})});}
   catch(e){error=e.message;}
   const record={status:output?'completed':'failed',analysis:output,error,jobId:job.id};
   fs.writeFileSync(path.join(directory,caseId+'-'+variant+'.json'),JSON.stringify(record,null,2),{mode:0o600});
   row[variant+'Status']=record.status;row[variant+'Error']=error;
   row[variant+'ReportUrl']=`/api/skills/${skill.id}/agent-evaluations/${runId}/${caseId}/${variant}`;
   row[variant+'Metrics']=output?.metrics||null;
   row[variant+'Seconds']=output?.elapsedSeconds??null;
   row[variant==='baseline'?'before':'after']=output?.category||'执行失败';completed++;
  }
  row.correct=row.candidateStatus==='completed'&&row.after===row.expected;
  row.regression=row.baselineStatus==='completed'&&row.before===row.expected&&!row.correct;
  results.push(row);
 }
 const baselineScore=results.filter(r=>r.baselineStatus==='completed'&&r.before===r.expected).length/cases.length;
 const proposedScore=results.filter(r=>r.correct).length/cases.length;
 const regressions=results.filter(r=>r.regression).length;
 const passed=results.every(r=>r.candidateStatus==='completed')&&regressions===0&&proposedScore>=baselineScore;
 const evaluation={mode:'agent',engine:'closed-loop',agentFingerprint,model:agent.configuration().model,runId,dataset:snapshot.version,datasetFingerprint:snapshot.fingerprint,baselineFingerprint:fingerprint(baseline),at:new Date().toISOString(),kind:'真实 closed-loop Agent 基线/候选逐例调查；计分类别正确率与退化，不自动判定根因机制正确性',baselineScore,proposedScore,candidateScore:proposedScore,precision:null,recall:null,regressions,passed,results,completed,total:cases.length*2,rootCauseMechanismAccuracy:null};
 fs.writeFileSync(path.join(directory,'evaluation.json'),JSON.stringify(evaluation,null,2),{mode:0o600});
 onProgress?.({completed,total:completed,message:'完整 Agent 对照测试已完成'});
 return evaluation;
}
module.exports={run,fingerprint,engineIdentity};
