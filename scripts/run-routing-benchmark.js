// Model receives log only; evaluation labels stay in this separate driver.
const fs=require('fs'),path=require('path');
const router=require('../server/jev-router');
async function main(){
 if(!router.enabled())throw Error('KERNEL_ROUTER_BASE_URL is required');
 const dataset=require('../data/benchmark/manifest.json'),cases=[];
 for(const c of dataset.cases){
  try{const result=await router.route(fs.readFileSync(path.join(__dirname,'../data/benchmark',c.logPath),'utf8'));cases.push({caseId:c.id,split:c.split,expectedCategory:c.category,result,categoryCorrect:result.category===c.category});console.log(c.id,result.category,result.elapsedSeconds);}
  catch(error){cases.push({caseId:c.id,split:c.split,error:error.message,categoryCorrect:false});console.log(c.id,'failed',error.message);}
 }
 const result={dataset:dataset.version,protocol:'SGLang constrained multi-question routing; no benchmark labels supplied to model. Scores are category accuracy, not root-cause accuracy or calibrated probabilities.',completedAt:new Date().toISOString(),cases,categoryAccuracy:cases.filter(c=>c.categoryCorrect).length/cases.length};
 fs.writeFileSync(process.argv[2]||'data/tool-evidence/routing.json',JSON.stringify(result,null,2));
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
