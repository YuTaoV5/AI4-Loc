const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {execFile}=require('child_process'),{promisify}=require('util');
const run=promisify(execFile),pending=new Map();
async function ingest(data,ownerId,file){
 const sha256=crypto.createHash('sha256').update(fs.readFileSync(file.path)).digest('hex');
 const owner=crypto.createHash('sha256').update(ownerId).digest('hex');
 const directory=path.join(data,'problem-pool',owner,sha256),manifest=path.join(directory,'manifest.json');
 const create=async()=>{
  if(fs.existsSync(manifest))return {...JSON.parse(fs.readFileSync(manifest)),directory,reused:true};
  fs.mkdirSync(directory,{recursive:true});
  const original=path.join(directory,'original');
  fs.copyFileSync(file.path,original);
  const content=path.join(directory,'content');
  // Incomplete extraction after a crash is never reused.
  fs.rmSync(content,{recursive:true,force:true});
  const {stdout}=await run(process.env.KERNEL_AGENT_PYTHON||(process.platform==='win32'?'python':'python3'),[path.join(__dirname,'../scripts/problem-extract.py'),original,content],{timeout:120000,maxBuffer:1024*1024,windowsHide:true});
  const record={id:sha256,sha256,originalName:file.originalname,size:fs.statSync(original).size,createdAt:new Date().toISOString(),extraction:JSON.parse(stdout)};
  fs.writeFileSync(manifest+'.tmp',JSON.stringify(record,null,2));fs.renameSync(manifest+'.tmp',manifest);
  return {...record,directory,reused:false};
 };
 if(pending.has(directory)){await pending.get(directory);return {...JSON.parse(fs.readFileSync(manifest)),directory,reused:true};}
 const work=create();pending.set(directory,work);try{return await work;}finally{pending.delete(directory);}
}
module.exports={ingest};
