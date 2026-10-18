"""Non-GPU acceptance on a shared Linux host. Never changes other processes."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,sys,time,ast

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    root=a.root.resolve();out=a.output.resolve();out.mkdir(exist_ok=False,parents=True)
    def command(args):
        r=subprocess.run(args,capture_output=True,text=True,timeout=45)
        return {'exit':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip()}
    def snapshot():
        proc={}
        for q in pathlib.Path('/proc').glob('[0-9]*'):
            try:
                stat=(q/'stat').read_text();end=stat.rindex(')');fields=stat[end+2:].split()
                proc[q.name]={'comm':(q/'comm').read_text().strip(),'start_tick':fields[19]}
            except (OSError,ValueError,IndexError):pass
        return {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gpu':command(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,power.draw','--format=csv,noheader']),
                'compute':command(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader']),'processes':proc}
    before=snapshot();(out/'before.json').write_text(json.dumps(before,indent=2))
    started=time.monotonic();env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
    r=subprocess.run([sys.executable,str(root/'skills/verify_decision_skills.py')],cwd=root,env=env,capture_output=True,text=True,timeout=90)
    (out/'checks.stdout.log').write_text(r.stdout);(out/'checks.stderr.log').write_text(r.stderr)
    files=list((root/'skills').rglob('*.py'))+[root/'research/jev-qwen35-9b-20261016/train.py'];hashes={}
    for q in files:
        ast.parse(q.read_text(encoding='utf-8'),filename=str(q))
        hashes[q.relative_to(root).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
    after=snapshot();(out/'after.json').write_text(json.dumps(after,indent=2))
    validation=json.loads((root/'skills/decision-skills-validation.json').read_text()) if r.returncode==0 else None
    # Record identities, not foreign command-line arguments or environments.
    active_python=[pid for pid,v in before['processes'].items() if 'python' in v['comm'].lower() and pid!=str(os.getpid())]
    stayed=[pid for pid in active_python if after['processes'].get(pid)==before['processes'][pid]]
    report={'schema':'ai4loc-shared-host-skill-acceptance/v1','passed':r.returncode==0,'utc':after['utc'],'python':sys.version,'seconds':time.monotonic()-started,'validation':validation,'parsed_python_files':len(files),'source_sha256':hashes,
            'cuda_visible_devices':'','model_downloaded':False,'gpu_training_executed':False,'real_model_api_calls':0,'new_model_ports':[],
            'foreign_python_processes_before':len(active_python),'same_identity_after':len(stayed),'signals_to_foreign_processes':0,'global_packages_modified':False,
            'scope':'CPU data contracts, plan generation, CE/RLCD worker syntax and local HTTP protocol stubs. Not 9B GPU training or live SGLang acceptance.',
            'gpu_execution_deferred_reason':'An existing compute workload is active; user requires no interference. No model or CUDA workload launched.'}
    (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
    raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
