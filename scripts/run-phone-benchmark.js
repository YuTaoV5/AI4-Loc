const fs=require('fs'),path=require('path'),crypto=require('crypto'),{execFileSync}=require('child_process');
const instructions=`Analyze a phone incident across the available boot stages. These test bundles are explicitly synthetic illustrative examples; vendor stage names vary. Do not infer a cause from absent stages, watchdog alone, encrypted payload or metadata. Identify the earliest causal fault, not downstream symptoms. Read all supplied logs. Treat binary payload as evidence; never execute it. Return only a JSON object in report.md and in the final response, no Markdown prose, with keys stage, component, mechanism, evidence (array of {file: path relative to input/content, quote: exact verbatim supporting log substring}), nextAction. Allowed stages: xloader, bl2, bl31, uefi, kernel, android, none, unknown. Components: ddr, secure_monitor, verified_boot, ufs, zygote, none, unknown. Mechanisms: ddr_training_failure, handoff_failure, image_verification_failure, storage_io_timeout, zygote_restart_loop, none, insufficient_evidence. Next actions: check_ddr, check_handoff, verify_image, check_storage, inspect_crash, confirm_normal, request_decoding, request_early_logs. Use unknown/insufficient_evidence when evidence cannot establish the fault. Evidence for a healthy capture should support completed boot; for unknown captures cite the actual evidence limitation. Do not invent files or quotes.`;
async function run(control){
 const root=path.resolve(control.dataset),output=path.resolve(control.output),workData=path.join(output,'worker-data');fs.mkdirSync(workData,{recursive:true});
 process.env.KERNEL_INSIGHT_DATA_DIR=workData;
 if(process.platform!=='linux'||!process.env.KERNEL_AGENT_SANDBOX)throw Error('Phone benchmark requires the Linux Harness sandbox');
 const goldPath=path.join(root,'private/gold.json'),goldHash=crypto.createHash('sha256').update(fs.readFileSync(goldPath)).digest('hex');
 for(const skill of control.skills||[]){if(skill.package?.published){if(!control.sourceData)throw Error('Published packages require sourceData');const packages=require('../server/skill-packages');packages.verify(control.sourceData,skill);fs.cpSync(packages.privateRoot(control.sourceData,skill.id),packages.privateRoot(workData,skill.id),{recursive:true});}}
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'))),rows=[];
 if(manifest.schema!=='phone-benchmark/v1')throw Error('Invalid phone dataset');
 const python=process.env.KERNEL_AGENT_PYTHON||'python3';
 for(const c of manifest.cases){
  const source=path.resolve(root,c.archive);if(!source.startsWith(root+path.sep))throw Error('Invalid archive path');
  if(crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex')!==c.sha256)throw Error('Input hash mismatch');
  const id=crypto.randomUUID(),start=Date.now();let row={caseId:c.id,status:'failed',points:0};
  try{
   const problem=await require('../server/problem-pool').ingest(workData,'isolated-phone-benchmark',{path:source,originalname:'incident.zip'});
   const selected=control.skills||[];
   const job={id,engine:'skill-harness',problemDirectory:problem.directory,userPrompt:instructions+'\n\n'+(control.prompt||'')};
   const analysis=await require('../server/agent').execute({job,log:'',skills:selected,data:workData});
   fs.writeFileSync(path.join(output,id+'.report.json'),JSON.stringify(analysis,null,2));
   const prediction=path.join(output,id+'.prediction.txt');fs.writeFileSync(prediction,analysis.reportMarkdown);
   // Worker has exited: trusted controller reads answers only now, outside its sandbox.
   const goldBytes=fs.readFileSync(goldPath);if(crypto.createHash('sha256').update(goldBytes).digest('hex')!==goldHash)throw Error('Gold labels changed during run');const gold=JSON.parse(goldBytes)[c.id];const goldFile=path.join(output,id+'.gold.json');fs.writeFileSync(goldFile,JSON.stringify(gold),{mode:0o600});
   const result=JSON.parse(execFileSync(python,[path.join(__dirname,'phone-scoring.py'),prediction,goldFile,source],{encoding:'utf8'}));
   row={...row,status:'completed',...result,report:id+'.report.json'};
  }catch(e){row.error=e.message.slice(0,1500);}
  row.elapsedSeconds=(Date.now()-start)/1000;rows.push(row);
  fs.writeFileSync(path.join(output,'results.json.tmp'),JSON.stringify({schema:'phone-benchmark-result/v1',dataset:manifest.version,origin:'synthetic',model:process.env.KERNEL_HARNESS_MODEL||process.env.KERNEL_AGENT_MODEL,goldSha256:goldHash,isolation:'Linux Harness sandbox; labels outside mounted worker workspace',scope:'Known constructed scenarios; not real phone root-cause accuracy',complete:rows.length===manifest.cases.length,caseCount:manifest.cases.length,completed:rows.filter(r=>r.status==='completed').length,score:rows.reduce((s,r)=>s+r.points,0)/manifest.cases.length,rows},null,2));fs.renameSync(path.join(output,'results.json.tmp'),path.join(output,'results.json'));
  console.log(JSON.stringify({completed:rows.length,total:manifest.cases.length,caseId:c.id,status:row.status,points:row.points}));
 }
}
if(require.main===module)run(JSON.parse(fs.readFileSync(process.argv[2]))).catch(e=>{console.error(e);process.exitCode=1;});
module.exports={run,instructions};
