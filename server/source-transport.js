const {spawn}=require('child_process');
async function resource(url,timeout){
 if(process.env.KERNEL_SOURCE_TRANSPORT!=='curl')return fetch(url,{signal:AbortSignal.timeout(timeout)});
 const child=spawn(process.platform==='win32'?'curl.exe':'curl',['--disable','--proto','=https','--fail','--silent','--show-error','--location','--max-time',String(Math.ceil(timeout/1000)),'--max-filesize','1073741824',url],{windowsHide:true,stdio:['ignore','pipe','pipe']});
 let stderr='',spawnError;child.stderr.on('data',b=>stderr=(stderr+b.toString()).slice(-1500));
 child.on('error',e=>{spawnError=e;child.stdout.destroy(e);});
 const done=new Promise(resolve=>child.once('close',code=>resolve(code)));
 const complete=async()=>{const code=await done;if(spawnError||code!==0)throw spawnError||Error('源码下载失败：'+stderr);};
 return {ok:true,status:200,headers:new Map(),body:child.stdout,complete,text:async()=>{let text='';for await(const b of child.stdout){text+=b.toString();if(text.length>4*1024*1024){child.kill();throw Error('校验清单过大');}}await complete();return text;}};
}
module.exports={resource};
