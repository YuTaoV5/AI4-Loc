const fs=require('fs'),path=require('path'),crypto=require('crypto'),multer=require('multer');
const digest=file=>new Promise((resolve,reject)=>{const h=crypto.createHash('sha256'),s=fs.createReadStream(file);s.on('data',b=>h.update(b));s.on('end',()=>resolve(h.digest('hex')));s.on('error',reject);});
module.exports=(app,{data})=>{
 const base=path.join(data,'materials');fs.mkdirSync(base,{recursive:true});
 const upload=multer({dest:base,limits:{fileSize:2*1024**3,files:6,fields:8,fieldSize:4096}}).fields([{name:'symbols',maxCount:4},{name:'vmcore',maxCount:1},{name:'kernelConfig',maxCount:1}]);
 const get=(id,user)=>{
  if(!/^[a-f0-9-]{36}$/.test(String(id)))throw Error('材料编号无效');
  const directory=path.join(base,id),manifest=JSON.parse(fs.readFileSync(path.join(directory,'manifest.json'),'utf8'));
  if(manifest.ownerId!==user.id&&user.role!=='admin')throw Error('不能访问其他用户的诊断材料');
  return {directory,manifest};
 };
 app.post('/api/materials',(req,res,next)=>{
  const stat=fs.statfsSync(data),available=Number(stat.bavail)*Number(stat.bsize),size=Number(req.headers['content-length']);
  if(!Number.isFinite(size)||size<=0)return res.status(411).json({error:'材料上传需要明确文件大小'});
  if(size>4*1024**3||available<size+512*1024**2)return res.status(507).json({error:'材料总量限 4GB，且需保留 512MB 空间'});
  upload(req,res,async err=>{
   const files=Object.values(req.files||{}).flat();let directory;
   try{
    if(err)throw err;if(!files.length)throw Error('请选择符号文件、vmcore 或内核配置');
    const expectedBuildId=String(req.body.expectedBuildId||'').toLowerCase().trim();
    if(expectedBuildId&&!/^[a-f0-9]{8,128}$/.test(expectedBuildId))throw Error('Build ID 需为 8–128 位十六进制');
    const id=crypto.randomUUID();directory=path.join(base,id);fs.mkdirSync(directory);
    const manifest={id,ownerId:req.user.id,createdAt:new Date().toISOString(),files:[]};
    for(const f of files){
     const fd=fs.openSync(f.path,'r'),head=Buffer.alloc(4096);let n;try{n=fs.readSync(fd,head,0,head.length,0);}finally{fs.closeSync(fd);}
     if(f.fieldname!=='kernelConfig'){if(n<64||!head.subarray(0,4).equals(Buffer.from([127,69,76,70]))||![1,2].includes(head[4])||![1,2].includes(head[5]))throw Error('符号与 vmcore 目前仅支持 ELF 文件');const type=head[5]===1?head.readUInt16LE(16):head.readUInt16BE(16);if(f.fieldname==='vmcore'?type!==4:![1,2,3].includes(type))throw Error('ELF 类型与材料用途不符');}
     if(f.fieldname==='kernelConfig'&&(f.size>2*1024**2||head.subarray(0,n).includes(0)||!/(?:^|\n)(?:CONFIG_[A-Z0-9_]+=|# CONFIG_)/.test(head.toString('utf8',0,n))))throw Error('请选择原始文本内核 .config（最多 2MB）');
     const sha256=await digest(f.path);
     const filename=manifest.files.length+'-'+f.fieldname,target=path.join(directory,filename);
     fs.renameSync(f.path,target);fs.chmodSync(target,0o400);
     manifest.files.push({path:filename,name:path.basename(f.originalname).slice(0,160),kind:f.fieldname,size:f.size,sha256,expectedBuildId});
    }
    fs.writeFileSync(path.join(directory,'manifest.json'),JSON.stringify(manifest),{mode:0o600});res.status(201).json(manifest);
   }catch(error){if(directory)fs.rmSync(directory,{recursive:true,force:true});next(error);}
   finally{for(const f of files)if(fs.existsSync(f.path))fs.unlinkSync(f.path);}
  });
 });
 app.get('/api/materials/:id',(req,res)=>{try{res.json(get(req.params.id,req.user).manifest);}catch(e){res.status(403).json({error:e.message});}});
 return {
  resolve:(id,user)=>id?get(id,user).manifest:null,
  stage:(manifest,workspace)=>{
   if(!manifest)return;const directory=path.join(workspace,'artifacts');fs.mkdirSync(directory,{recursive:true});
   const files=manifest.files.map(item=>{const source=path.join(base,manifest.id,item.path),target=path.join(directory,item.path);fs.copyFileSync(source,target,fs.constants.COPYFILE_FICLONE);fs.chmodSync(target,0o400);return {...item,path:'artifacts/'+item.path};});
   fs.writeFileSync(path.join(workspace,'artifacts.json'),JSON.stringify({files}));
  }
 };
};
