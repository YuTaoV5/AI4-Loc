const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const {execFile} = require('child_process');
const {promisify} = require('util');
const run=promisify(execFile);
const {resource}=require('./source-transport');
const dir=path.join(process.env.KERNEL_INSIGHT_DATA_DIR||path.join(__dirname,'../data'),'kernels');
fs.mkdirSync(dir,{recursive:true});
const db=path.join(dir,'index.json');
let entries=fs.existsSync(db)?JSON.parse(fs.readFileSync(db)):[];
for(const e of entries) if(['queued','downloading','extracting'].includes(e.status)) {e.status='failed';e.error='服务重启，点击重试';}
const save=()=>{fs.writeFileSync(db+'.tmp',JSON.stringify(entries,null,2));fs.renameSync(db+'.tmp',db);};
let active=0;
async function extractArchive(archive,dest){
 const {stdout}=await run('tar',['-tf',archive],{maxBuffer:32*1024*1024,timeout:60000});const paths=stdout.trim().split(/\r?\n/);
 if(paths.some(p=>p.startsWith('/')||p.includes('\\')||p.split('/').includes('..')||/^[A-Za-z]:/.test(p)))throw Error('压缩包包含非法路径');
 const tops=new Set(paths.map(p=>p.split('/')[0]));if(tops.size!==1)throw Error('源码压缩包目录结构不符合预期');
 const top=[...tops][0],sourcePath=path.join(dest,top),links=[];
 const args=['-xf',archive,'-C',dest];
 if(process.platform==='win32'){
   const listing=await run('tar',['-tvf',archive],{maxBuffer:64*1024*1024,timeout:60000});
   for(const line of listing.stdout.split(/\r?\n/)){if(!line.startsWith('l'))continue;const start=line.indexOf(top+'/'),separator=line.indexOf(' -> ',start);if(start<0||separator<0)throw Error('无法解析源码符号链接');const name=line.slice(start,separator),target=line.slice(separator+4);links.push({name,target});args.push('--exclude',name);}
 }
 await run('tar',args,{timeout:600000,maxBuffer:1024*1024});
 if(links.length){
   const pending=[...links];let changed=true;
   const inside=p=>p===sourcePath||p.startsWith(sourcePath+path.sep);
   while(pending.length&&changed){changed=false;for(let i=pending.length-1;i>=0;i--){const l=pending[i],output=path.resolve(dest,l.name),target=path.resolve(path.dirname(output),l.target);if(!inside(output)||!inside(target))throw Error('符号链接超出源码目录');if(!fs.existsSync(target))continue;fs.mkdirSync(path.dirname(output),{recursive:true});if(!fs.existsSync(output)){if(fs.statSync(target).isDirectory())fs.symlinkSync(target,output,'junction');else fs.copyFileSync(target,output);}pending.splice(i,1);changed=true;}}
   if(pending.length)throw Error(`源码有 ${pending.length} 个无法解析的符号链接`);
   fs.writeFileSync(path.join(dest,'symlinks.json'),JSON.stringify(links,null,2));
 }
 if(!fs.existsSync(path.join(sourcePath,'Makefile')))throw Error('源码缺少 Makefile');
 return {sourcePath,linkMode:process.platform==='win32'?'file-copy / directory-junction':'native-symlinks',linkCount:links.length};
}
function resolve(spec) {
  const repository=spec.repository||'mainline';
  if(!['mainline','stable','next'].includes(repository)) throw Error('请选择 mainline / stable / next 仓库');
  const commit=spec.commit||spec.kernelCommit;
  const version=spec.version||spec.kernelVersion;
  if(commit) {
    if(!/^[a-f0-9]{12,40}$/.test(commit)) throw Error('Commit 必须为 12–40 位十六进制');
    const url=repository==='mainline'?`https://codeload.github.com/torvalds/linux/tar.gz/${commit}`:repository==='stable'?`https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/snapshot/linux-${commit}.tar.gz`:`https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/snapshot/linux-next-${commit}.tar.gz`;
    return {key:`${repository}-${commit}`,version:version||commit,commit,repository,url,format:'gz',exact:true};
  }
  if(!/^\d+\.\d+(?:\.\d+)?(?:-rc\d+)?$/.test(version||'')) throw Error('定制/发行版内核不能用基础版本替代，请提供准确的 commit 与仓库');
  const major=Number(version.split('.')[0]);
  if(major<3) throw Error('当前支持 Linux 3.x 及以上版本');
  const base=`https://cdn.kernel.org/pub/linux/kernel/v${major}.x/${version.includes('-rc')?'testing/':''}`;
  return {key:`release-${version}`,version,repository:'release',url:`${base}linux-${version}.tar.xz`,checksumUrl:`${base}sha256sums.asc`,format:'xz',exact:true};
}
async function download(e) {
  const dest=path.join(dir,e.key); fs.mkdirSync(dest,{recursive:true});
  const archive=path.join(dest,`source.tar.${e.format}`),temp=archive+'.part';
  try {
    e.error=null;
    const cached=fs.existsSync(archive)&&e.sha256&&crypto.createHash('sha256').update(fs.readFileSync(archive)).digest('hex')===e.sha256;
    if(!cached){e.status='downloading';e.bytes=0;save();
    const r=await resource(e.url,600000); if(!r.ok) throw Error(`下载 HTTP ${r.status}`);
    if(/text\/html/.test(r.headers.get('content-type')||'')) throw Error('源码站返回 HTML，可能需要网络重试');
    e.totalBytes=Number(r.headers.get('content-length'))||null;
    const fd=fs.openSync(temp,'w');const hash=crypto.createHash('sha256');let saved=Date.now();
    try {for await(const chunk of r.body) {e.bytes+=chunk.length;if(e.bytes>1024*1024*1024) throw Error('源码压缩包超过 1GB');fs.writeSync(fd,chunk);hash.update(chunk);if(Date.now()-saved>1000){save();saved=Date.now();}}}finally{fs.closeSync(fd);}
    if(r.complete)await r.complete();
    e.sha256=hash.digest('hex');
    if(e.checksumUrl) {
      const response=await resource(e.checksumUrl,45000);if(!response.ok) throw Error('无法读取官方 SHA256 校验清单');
      const text=await response.text();const line=text.split('\n').find(l=>l.trim().endsWith(`linux-${e.version}.tar.xz`));
      if(!line || line.trim().split(/\s+/)[0]!==e.sha256) throw Error('官方 SHA256 校验失败');e.verification='official-sha256';
    } else e.verification='https-snapshot / local-sha256';
    fs.renameSync(temp,archive);}
    e.status='extracting';save();Object.assign(e,await extractArchive(archive,dest));
    e.status='ready';e.completedAt=new Date().toISOString();
  }catch(err){e.status='failed';e.error=err.message.slice(0,1500);if(fs.existsSync(temp))fs.unlinkSync(temp);}finally{save();active--;pump();}
}
function pump(){for(const e of entries){if(active>=2)break;if(e.status==='queued'){active++;download(e);}}}
function ensure(spec){const resolved=resolve(spec);let e=entries.find(x=>x.key===resolved.key);if(e&&e.status==='ready'&&!fs.existsSync(path.join(e.sourcePath,'Makefile')))e.status='failed';if(!e){e={...resolved,status:'queued',createdAt:new Date().toISOString()};entries.unshift(e);}else if(e.status==='failed'){e.status='queued';e.error=null;}save();pump();return e;}
module.exports={resolve,ensure,extractArchive,list:()=>entries};
