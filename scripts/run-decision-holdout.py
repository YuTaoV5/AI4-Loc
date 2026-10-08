"""Evaluate every ready test-split case; no selection by observed performance."""
import argparse,json,os,pathlib,subprocess,sys,time
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--dataset',type=pathlib.Path,required=True);p.add_argument('--wait-pid',type=int);a=p.parse_args()
    if a.wait_pid:
        while pathlib.Path('/proc',str(a.wait_pid)).exists():time.sleep(5)
    manifest=json.loads((a.dataset/'manifest.json').read_text());cases=[c['id'] for c in manifest['cases'] if c['split']=='test' and c['status']=='ready']
    for variant,source,enabled in [('test-baseline','baseline',False),('test-adaptive','candidate',True)]:
        dest=a.root/(variant+'-results')
        if dest.exists():raise ValueError('Refuse to overwrite existing results')
        cmd=[sys.executable,str(a.root/source/'scripts/run-localization-benchmark.py'),'--dataset',str(a.dataset),'--output',str(dest),'--cases',','.join(cases),'--profiles','log+source','--base','http://127.0.0.1:11434','--transport','ollama-native','--eager-boundary','--source-triage','--max-calls','8','--timeout','240']
        env=dict(os.environ);env.pop('KERNEL_DECISION_BASE_URL',None);env.pop('KERNEL_DECISION_POLICY',None)
        if enabled:env.update(KERNEL_DECISION_BASE_URL='http://127.0.0.1:30000',KERNEL_DECISION_POLICY='adaptive')
        with (a.root/(variant+'.log')).open('w') as log:result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError(variant+' failed; retained log')
        print(variant,json.loads((dest/'results.json').read_text())['aggregate'],flush=True)
if __name__=='__main__':main()
