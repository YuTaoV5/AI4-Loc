"""Preserve all variants; sequential execution avoids benchmark GPU contention."""
import argparse,json,os,pathlib,subprocess,sys,time

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--dataset',required=True);a=p.parse_args()
    cases='corrupt_uaf_kmalloc,leak_kmalloc,lock_mutex_abba,lock_sleep_atomic,pressure_oom,baseline,lkdtm_ACCESS_NULL,corrupt_oob_kmalloc,lock_rcu_stall'
    for variant,source,policy in [('adaptive','candidate','adaptive'),('rule-ablation','candidate','adaptive-rule'),('baseline-warm','baseline',None)]:
        dest=a.root/(variant+'-results')
        if dest.exists():raise ValueError('Refuse to overwrite experiment: '+str(dest))
        cmd=[sys.executable,str(a.root/source/'scripts/run-localization-benchmark.py'),'--dataset',a.dataset,'--output',str(dest),'--cases',cases,'--profiles','log+source','--base','http://127.0.0.1:11434','--transport','ollama-native','--eager-boundary','--source-triage','--max-calls','8','--timeout','240']
        env=dict(os.environ);env.pop('KERNEL_DECISION_BASE_URL',None);env.pop('KERNEL_DECISION_POLICY',None)
        if policy:env.update(KERNEL_DECISION_BASE_URL='http://127.0.0.1:30000',KERNEL_DECISION_POLICY=policy)
        started=time.time()
        with (a.root/(variant+'.log')).open('w') as log:result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
        (a.root/(variant+'-execution.json')).write_text(json.dumps({'command':cmd,'policy':policy,'exitCode':result.returncode,'wallSeconds':time.time()-started},indent=2))
        if result.returncode:raise RuntimeError('Experiment failed, log preserved: '+variant)
        print(variant,json.loads((dest/'results.json').read_text())['aggregate'],flush=True)
if __name__=='__main__':main()
