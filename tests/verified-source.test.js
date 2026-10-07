const {test}=require('node:test'),assert=require('assert/strict'),fs=require('fs'),path=require('path'),os=require('os'),crypto=require('crypto');
const {prepare}=require('../server/agent-source');
test('verified local source requires both exact log hash and matching file bytes',async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'kernel-source-registry-')),previous=process.env.KERNEL_VERIFIED_SOURCE_REGISTRY;
 try{
  const source=path.join(temp,'source'),work=path.join(temp,'work');fs.mkdirSync(source);fs.mkdirSync(work);fs.writeFileSync(path.join(source,'a.c'),'int evidence;');
  const log='BUG: test',hash=x=>crypto.createHash('sha256').update(x).digest('hex'),registry=path.join(temp,'registry.json');
  fs.writeFileSync(registry,JSON.stringify({sourceRoot:source,commit:'a'.repeat(40),logHashes:[hash(log)],files:[{path:'a.c',sha256:hash('int evidence;')}]}));process.env.KERNEL_VERIFIED_SOURCE_REGISTRY=registry;
  const result=await prepare(log,null,work);assert.equal(result.files[0].origin,'verified-local-build');assert.equal(fs.readFileSync(path.join(work,'source-context/a.c'),'utf8'),'int evidence;');
  fs.writeFileSync(path.join(source,'a.c'),'changed');assert.match((await prepare(log,null,work)).errors[0],/校验失败/);
 }finally{if(previous===undefined)delete process.env.KERNEL_VERIFIED_SOURCE_REGISTRY;else process.env.KERNEL_VERIFIED_SOURCE_REGISTRY=previous;assert.ok(path.basename(temp).startsWith('kernel-source-registry-'));fs.rmSync(temp,{recursive:true,force:true});}
});
test('unknown log cannot reuse a known patched vendor commit as official source',async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'kernel-source-registry-')),previous=process.env.KERNEL_VERIFIED_SOURCE_REGISTRY;
 try{const registry=path.join(temp,'registry.json');fs.writeFileSync(registry,JSON.stringify({commit:'a'.repeat(40),logHashes:[]}));process.env.KERNEL_VERIFIED_SOURCE_REGISTRY=registry;const result=await prepare('unseen log',{commit:'a'.repeat(40)},temp);assert.equal(result.files.length,0);assert.match(result.errors[0],/不能/);}
 finally{if(previous===undefined)delete process.env.KERNEL_VERIFIED_SOURCE_REGISTRY;else process.env.KERNEL_VERIFIED_SOURCE_REGISTRY=previous;fs.rmSync(temp,{recursive:true,force:true});}
});
