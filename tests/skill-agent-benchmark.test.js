const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),os=require('os');
const agent=require('../server/agent'),benchmark=require('../server/skill-agent-benchmark');

test('full Skill benchmark executes baseline and candidate, retains reports, and rejects regression',async()=>{
 const data=fs.mkdtempSync(path.join(os.tmpdir(),'skill-agent-')),execute=agent.execute;
 const skill={id:'candidate',version:'1',patterns:[],category:'OOM',content:'Actual full investigation instructions'};
 const baseline=[{id:'base',version:'1',patterns:[],category:'内存越界',content:'baseline'}],proposed=[...baseline,skill];
 const snapshot={version:'fixture',fingerprint:'frozen',cases:[{id:'positive',category:'内存越界',log:'BUG: synthetic fault',rootCause:'EVALUATOR_ONLY_CAUSE'}]};
 const calls=[];
 agent.execute=async request=>{calls.push(request);assert.equal(request.job.agentProfile.agentId,'chat-investigator');assert.equal(request.job.agentBudget.maxModelCalls,8);return {category:request.log.startsWith('BUG:')?(request.skills.some(s=>s.id===skill.id)?'OOM':'内存越界'):'待专家分析',summary:'synthetic',metrics:{modelRequests:1}};};
 try{
  const result=await benchmark.run({skill,baseline,proposed,snapshot,data});
  assert.equal(calls.length,4);assert.equal(result.completed,4);assert.equal(result.mode,'agent');assert.equal(result.regressions,1);assert.equal(result.passed,false);assert.equal(result.rootCauseMechanismAccuracy,null);
  assert.ok(calls.every(c=>!('expected' in c.job)&&!JSON.stringify(c).includes('EVALUATOR_ONLY_CAUSE')));
  assert.equal(fs.readdirSync(path.join(data,'skill-pulls',skill.id,'agent-evaluations',result.runId)).length,5);
  assert.notEqual(benchmark.fingerprint(baseline),benchmark.fingerprint([{...baseline[0],content:'changed body'}]));
 }finally{agent.execute=execute;assert.ok(data.startsWith(path.resolve(os.tmpdir())+path.sep));fs.rmSync(data,{recursive:true,force:true});}
});
