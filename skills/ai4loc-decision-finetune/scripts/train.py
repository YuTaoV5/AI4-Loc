"""Parameterize the frozen executed trainer; default is an offline plan, not training."""
import argparse,pathlib,json,hashlib,subprocess,sys,shutil
BASE_REV='c202236235762e1c871ad0ccb60c8ee5ba337b9a'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def worker_source(source,run,base,out,objective):
    s=source.read_text(encoding='utf-8')
    changes={"E=pathlib.Path(__file__).resolve().parent":f'E=pathlib.Path({str(run)!r})',"BASE=pathlib.Path('/root/gpufree-data/systemone/models/Qwen3.5-9B')":f'BASE=pathlib.Path({str(base)!r})',"OUT=pathlib.Path('/root/gpufree-data/systemone/models/AI4Loc-Jev-Qwen3.5-9B')":f'OUT=pathlib.Path({str(out)!r})'}
    for old,new in changes.items():
        if s.count(old)!=1:raise ValueError('Reference trainer layout changed; review before adapting')
        s=s.replace(old,new)
    # Honor custom class counts without asking random.choice for unavailable alternatives.
    s=s.replace('k=random.choice([5,8,12]);','k=random.choice(sorted(set(min(len(classes),n) for n in [5,8,12])));')
    if objective=='ce':
        old="loss=F.cross_entropy(logits,torch.tensor([target],device='cuda')) if epoch==0 else rlcd(logits,target,.4-(epoch-1)*.25)"
        if old not in s:raise ValueError('Reference objective changed')
        s=s.replace(old,"loss=F.cross_entropy(logits,torch.tensor([target],device='cuda'))")
        s=s.replace("'loss':'epoch0 CE, epochs1-2 CE + Laya-style RLCD PG(log+spherical proper reward); noise .4 to .15'","'loss':'CE-only all epochs; matched update budget'")
    compile(s,'training-worker.py','exec')
    return s

def main():
    p=argparse.ArgumentParser();p.add_argument('--project-root',type=pathlib.Path,required=True);p.add_argument('--run-dir',type=pathlib.Path,required=True);p.add_argument('--base',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--objective',choices=['ce','ce-rlcd'],default='ce-rlcd');p.add_argument('--execute',action='store_true');a=p.parse_args()
    root=a.project_root.resolve();run=a.run_dir.resolve();base=a.base.resolve();out=a.output.resolve();ref=root/'research/jev-qwen35-9b-20261016'
    for f in ['dataset.private.json','dataset-frozen.json','validation.json']:
        if not (run/f).is_file():raise ValueError(f'Missing dataset input: {f}')
    v=json.loads((run/'validation.json').read_text(encoding='utf-8'));f=json.loads((run/'dataset-frozen.json').read_text(encoding='utf-8'))
    if v.get('passed') is not True or sha(run/'dataset.private.json')!=f['private_sha256']:raise ValueError('Dataset validation/hash mismatch')
    private=json.loads((run/'dataset.private.json').read_text(encoding='utf-8'))
    if any(not r.get('reviewed_by') or not r.get('evidence') for r in private):raise ValueError('Reviewed inputs and label evidence required')
    # Recheck the current file, not merely a previously successful validation flag.
    groups={};hashes=set()
    for r in private:
        if r['input_sha256']!=hashlib.sha256(r['input'].encode()).hexdigest():raise ValueError('Input content hash changed')
        if r['group'] in groups and groups[r['group']]!=r['split']:raise ValueError('Group leakage')
        groups[r['group']]=r['split']
        h=r['normalized_input_sha256']
        if h in hashes:raise ValueError('Duplicate normalized input')
        hashes.add(h)
    for glob in ['training-steps.jsonl','training-complete.json','adapter-epoch*.pt','training-worker.py']:
        if list(run.glob(glob)):raise ValueError('Run already used for training; prepare a NEW dataset/run directory')
    if out.exists():raise ValueError('Output checkpoint must not exist')
    source=ref/'train.py'
    if not source.is_file():raise ValueError('Project reference train.py not found')
    s=worker_source(source,run,base,out,a.objective)
    counts=f['counts'];synthetic=v.get('synthetic_examples',False)
    plan={'schema':'ai4loc-decision-training-plan/v1','base_revision':BASE_REV,'base':str(base),'run':str(run),'output':str(out),'reference_sha256':sha(source),'dataset_frozen_sha256':sha(run/'dataset-frozen.json'),'objective':a.objective,'counts':counts,'epochs':3,'permutations_per_case_per_epoch':4,'microsteps':counts['train']*12,'optimizer_updates':counts['train']*3,'rank':8,'alpha':16,'lr':1e-4,'gradient_accumulation':4,'max_tokens':2048,'max_input_characters':3000,'execute_requested':a.execute,'synthetic_examples':synthetic,'reference_hardware':'A100 80GB; BF16 backbone / FP32 LoRA; observed torch training peak18.74GiB for historical workload, not a minimum-VRAM promise','requires_reference_environment':'torch2.13.0+cu130 / transformers5.12.1; SGLang0.5.21 for recorded serving'}
    plan.update(worker_source_validated=True,worker_source_sha256=hashlib.sha256(s.encode()).hexdigest())
    (run/'training-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(plan,ensure_ascii=False))
    if not a.execute:return
    if synthetic or counts['train']<5:raise ValueError('Do not train format examples; require at least5 reviewed real training cases')
    if not (base/'config.json').is_file():raise ValueError('Download and verify pinned base checkpoint first')
    verified=base/'verified-checkpoint.json'
    if not verified.is_file() or json.loads(verified.read_text(encoding='utf-8')).get('revision')!=BASE_REV:raise ValueError('Pinned checkpoint verification manifest required; use documented fetch-checkpoint.py')
    if shutil.disk_usage(out.parent).free<22*1024**3:raise ValueError('Need at least22GiB free for new merged output, plus adapters/logs elsewhere')
    metadata=ref/'official-model-metadata.json';shutil.copy2(metadata,run/metadata.name)
    worker=run/'training-worker.py';worker.write_text(s,encoding='utf-8')
    # Record the exact generated source prior to the first GPU forward.
    (run/'training-worker-sha256.json').write_text(json.dumps({'sha256':sha(worker),'objective':a.objective},indent=2),encoding='utf-8')
    with (run/'training.log').open('x',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,'-u',str(worker)],stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise SystemExit(result.returncode)
if __name__=='__main__':main()
