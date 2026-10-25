const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('fs'),path=require('path'),os=require('os'),vm=require('vm');

test('one-click Chat benchmark is available without a Decision endpoint',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'chat-suite-'));
 try{
  fs.writeFileSync(path.join(directory,'manifest.json'),JSON.stringify({cases:[{id:'case',status:'ready',split:'test',files:{rawLog:{sha256:'log'}}}]}));
  fs.writeFileSync(path.join(directory,'benchmark-annotations.json'),JSON.stringify({cases:{case:{status:'collector_verified',rawLogSha256:'log'}}}));
  const routes=new Map(),app={get:(name,fn)=>routes.set(name,fn),post:()=>{}};
  const context={module:{exports:{}},__dirname:path.join(__dirname,'../server'),process:{platform:'linux',arch:'x64',env:{KERNEL_BENCHMARK_DATASET:directory}},setImmediate};
  context.require=name=>name==='./agent'?{enabled:()=>true,configuration:()=>({engine:'closed-loop',model:'chat'}),identity:()=> 'engine'}:name==='child_process'?{spawnSync:()=>({status:0})}:name.startsWith('./')?require(path.join(__dirname,'../server',name)):require(name);
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../server/benchmark-service.js'),'utf8'),context);
  context.module.exports(app,{state:{},save:()=>{},data:directory,profiles:{}});
  let suite;routes.get('/api/benchmark/suite')({}, {json:value=>suite=value});
  assert.equal(suite.available,true);assert.equal(suite.reason,null);assert.equal(suite.caseCount,1);
  assert.equal(suite.configuration.decisionEndpoint,undefined);
 }finally{assert.ok(directory.startsWith(path.resolve(os.tmpdir())+path.sep));fs.rmSync(directory,{recursive:true,force:true});}
});
