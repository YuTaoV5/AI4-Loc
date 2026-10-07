#!/usr/bin/env python3
"""Import existing public lab traces for UI replay; never invoke a model or tests."""
import datetime,json,pathlib,subprocess,tarfile

ROOT=pathlib.Path(__file__).resolve().parents[2]
DATA=ROOT/'data/windows-local'
DATA.mkdir(parents=True,exist_ok=True)
replay=DATA/'archived-replays';replay.mkdir(exist_ok=True)
source=ROOT/'data/dataset-audit/benchmark-traces-v10.tgz'
index=[]
with tarfile.open(source) as tf:
    for m in tf.getmembers():
        if m.isfile() and m.name.startswith('iteration-source-v10/workspaces/') and m.name.endswith('localization-trace.json'):
            case=m.name.split('/')[2].split('__')[0]
            trace=json.load(tf.extractfile(m))
            (replay/(case+'.json')).write_text(json.dumps(trace,ensure_ascii=False,indent=2),encoding='utf-8')
            index.append(case)
script=r'''
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const root=process.cwd(),data=path.join(root,'data/windows-local');
const {analyze,builtins}=require('./server/analyzer');
const db=JSON.parse(fs.readFileSync(path.join(data,'accounts.json'))),owner=db.users.find(u=>u.username==='admin').id;
const file=path.join(data,'state.json'),state=fs.existsSync(file)?JSON.parse(fs.readFileSync(file)):{jobs:[],skills:builtins};
const names={corrupt_uaf_kmalloc:'释放后使用',leak_kmalloc:'内存泄漏',lock_mutex_abba:'锁顺序',lock_sleep_atomic:'原子态睡眠',pressure_oom:'内存耗尽',baseline:'健康基线'};
for(const [caseId,label] of Object.entries(names)){
 const id='replay-'+caseId;if(state.jobs.some(j=>j.id===id))continue;
 const trace=JSON.parse(fs.readFileSync(path.join(data,'archived-replays',caseId+'.json')));
 const log=fs.readFileSync(path.join(root,'data/datasets/stability-v1/cases',caseId,'agent.log'),'utf8');
 const analysis=analyze(log,builtins,[]);analysis.engine='既有实验报告回放（非本机新推理）';
 analysis.agent={...trace.analysis,metrics:trace.metrics,evidence:trace.evidence,toolCalls:trace.toolCalls,elapsedSeconds:trace.elapsedSeconds,model:'qwen3.8:27b-kernel-8k',harness:trace.harness};
 analysis.limitations='本条为已有真实实验结果的本地回放。没有重新调用模型；代码候选尚未经过独立机制复核。';
 const now=new Date().toISOString();
 const j={id,name:'实验回放 · '+label,ownerId:owner,createdAt:now,analyzedAt:now,status:'needs_review',stage:'complete',progress:100,reportReady:true,isBenchmark:true,machine:'OpenHarmony 5.10.210+ / QEMU',inputHash:crypto.createHash('sha256').update(log).digest('hex'),analysis,analysisSeconds:trace.elapsedSeconds,skillSelection:{preset:'recommended',ids:analysis.skills.map(s=>s.id)},agent:{name:'离线实验报告回放',status:'completed',message:'载入已有实验轨迹；此页面未进行本机模型推理'},timeline:[],replaySource:'data/dataset-audit/benchmark-traces-v10.tgz'};
 state.jobs.push(j);fs.mkdirSync(path.join(data,'reports'),{recursive:true});fs.writeFileSync(path.join(data,'reports',id+'.log'),log);
}
fs.writeFileSync(file,JSON.stringify(state,null,2));console.log(JSON.stringify({replayedCases:state.jobs.filter(j=>j.id.startsWith('replay-')).length,data}));
'''
subprocess.run(['node','-e',script],cwd=ROOT,check=True)
(DATA/'deployment.json').write_text(json.dumps({'purpose':'Windows local website and slide screenshots','site':'http://127.0.0.1:8787','benchmark':'openharmony-lkdtm-lab-v2','modelMode':'local deterministic triage; historical lab reports imported for replay','replayedCases':index,'newModelCalls':0,'functionalAcceptanceExecuted':False,'importedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()},ensure_ascii=False,indent=2),encoding='utf-8')
