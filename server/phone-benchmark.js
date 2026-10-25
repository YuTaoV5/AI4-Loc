const fs=require('fs'),path=require('path');
module.exports=(app,{data})=>{
 const root=path.join(data,'phone-benchmark'),read=file=>{try{return JSON.parse(fs.readFileSync(file));}catch{return null;}};
 app.get('/api/phone-benchmark',(_,res)=>{const suite=read(path.join(root,'synthetic/manifest.json')),real=read(path.join(root,'abrlog/provenance.json')),latest=read(path.join(root,'latest.json'));res.json({available:!!suite,version:suite?.version,cases:suite?.cases||[],realCases:read(path.join(root,'abrlog/samples.json'))?.cases||[],real:real?{source:real.source,fileCount:real.fileCount,expandedBytes:real.expandedBytes,rootCauseLabels:false}:null,result:latest?read(path.join(root,'runs',latest.id,'results.json')):null,notice:'合成集只衡量已知构造场景；真实手机语料没有人工根因标签，不计准确率。'});});
 app.get('/api/phone-benchmark/real/:id/archive',(req,res)=>{const list=read(path.join(root,'abrlog/samples.json')),c=list?.cases.find(c=>c.id===req.params.id);if(!c)return res.status(404).json({error:'真实手机采集包不存在'});res.download(path.join(root,'abrlog',c.archive),'phone-abrlog-'+c.id+'.zip');});
 app.get('/api/phone-benchmark/cases/:id/archive',(req,res)=>{const suite=read(path.join(root,'synthetic/manifest.json')),c=suite?.cases.find(c=>c.id===req.params.id);if(!c)return res.status(404).json({error:'手机样本不存在'});res.download(path.join(root,'synthetic',c.archive),'phone-synthetic-'+c.id+'.zip');});
};
