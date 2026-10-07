const fs=require('fs'),path=require('path'),crypto=require('crypto');
const runCurl=require('util').promisify(require('child_process').execFile);
async function getSource(url){const {stdout}=await runCurl(process.platform==='win32'?'curl.exe':'curl',['--disable','--proto','=https','--location','--fail','--silent','--show-error','--max-time','15','--max-filesize','2097152','--user-agent','Kernel-Insight','--header','Accept: application/vnd.github.raw+json',url],{encoding:'utf8',maxBuffer:2097152,timeout:18000,windowsHide:true});return stdout;}
async function prepare(log,spec,dir){
 const registryFile=process.env.KERNEL_VERIFIED_SOURCE_REGISTRY;
 if(registryFile){
  try{
   const registry=JSON.parse(fs.readFileSync(registryFile,'utf8')),inputHash=crypto.createHash('sha256').update(log).digest('hex');
   if(registry.logHashes.includes(inputHash)){
    const source=fs.realpathSync(registry.sourceRoot),files=[];
    for(const item of registry.files){
     if(!/^[a-zA-Z0-9_./-]+$/.test(item.path)||item.path.split('/').includes('..'))throw Error('本地源码清单路径非法');
     const from=fs.realpathSync(path.join(source,item.path));if(!from.startsWith(source+path.sep))throw Error('本地源码超出目录');
     const bytes=fs.readFileSync(from);if(bytes.length>2*1024*1024||crypto.createHash('sha256').update(bytes).digest('hex')!==item.sha256)throw Error('本地源码校验失败');
     const target=path.join(dir,'source-context',item.path);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,bytes);
     files.push({file:item.path,revision:registry.commit,sha256:item.sha256,bytes:bytes.length,origin:'verified-local-build',buildId:registry.buildId,sourceState:registry.sourceState});
    }
    fs.writeFileSync(path.join(dir,'source-context.json'),JSON.stringify({files,errors:[],inputHash,datasetManifestSha256:registry.datasetManifestSha256},null,2));return {files,errors:[]};
   }
   if(spec?.commit===registry.commit)return {files:[],errors:['该日志未匹配本地构建身份清单；不能将 OpenHarmony 补丁构建替换成官方同名 commit']};
  }catch(error){return {files:[],errors:['本地构建源码核验失败：'+error.message]};}
 }
 const revision=spec?.commit||(/^\d+\.\d+(?:\.\d+)?(?:-rc\d+)?$/.test(spec?.version||'')?'v'+spec.version:null);
 if(!revision||!/^([a-f0-9]{12,40}|v\d+\.\d+(?:\.\d+)?(?:-rc\d+)?)$/.test(revision))return {files:[],errors:['没有可确认的官方版本或 commit，未拉取源码上下文']};
 const names=[...new Set(Array.from(log.matchAll(/\b((?:arch|block|crypto|drivers|fs|include|ipc|kernel|lib|mm|net|security|sound|virt)\/[a-zA-Z0-9_./-]+\.[ch]):\d+/g),m=>m[1]))].filter(s=>!s.split('/').includes('..')).slice(0,6);
 const files=[],errors=[];fs.mkdirSync(path.join(dir,'source-context'),{recursive:true});
 await Promise.allSettled(names.map(async file=>{try{
  const repository=spec.repository==='stable'?'gregkh/linux':'torvalds/linux';const url=spec.repository==='next'?`https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/plain/${file}?id=${revision}`:`https://raw.githubusercontent.com/${repository}/${revision}/${file}`;
  let actualUrl=url,text;
  try{text=await getSource(url);}catch(error){
   if(spec.repository==='next')throw error;
   actualUrl='https://api.github.com/repos/'+repository+'/contents/'+file+'?ref='+revision;
   text=await getSource(actualUrl);
  }
  if(text.length>2*1024*1024||/<html|<!doctype html/i.test(text.slice(0,500)))throw Error('源码响应不是可接受的 C 文本');
  if(text.trimStart().startsWith('{')){
   try{const object=JSON.parse(text);if(object.type!=='file'||object.path!==file||object.encoding!=='base64')throw Error('API 未返回源码文件');text=Buffer.from(object.content,'base64').toString('utf8');}catch(error){throw Error('源码 API 返回不可接受的 JSON');}
  }
  const target=path.join(dir,'source-context',file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,text);
  files.push({file,revision,url:actualUrl,sha256:crypto.createHash('sha256').update(text).digest('hex'),bytes:Buffer.byteLength(text)});
 }catch(error){errors.push(file+': '+String(error.stderr||error.message).slice(-250));}}));
 fs.writeFileSync(path.join(dir,'source-context.json'),JSON.stringify({files,errors},null,2));return {files,errors};
}
module.exports={prepare};
