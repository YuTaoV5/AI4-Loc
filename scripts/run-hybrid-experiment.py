"""Sequential isolated full-test evaluations, retain evidence-only control and hybrid."""
import argparse,json,os,pathlib,subprocess,sys,time
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--dataset',type=pathlib.Path,required=True);a=p.parse_args()
    while True:
        progress=a.root/'boundary-v2-results/results.json'
        if progress.exists() and len(json.loads(progress.read_text())['rows'])==54:break
        time.sleep(2)
    m=json.loads((a.dataset/'manifest.json').read_text());cases=[c['id'] for c in m['cases'] if c['status']=='ready' and c['split']=='test']
    for name,mode in [('isolated-control','evidence-only'),('isolated-hybrid','decision')]:
        dest=a.root/(name+'-results')
        if dest.exists():raise ValueError('Refuse to overwrite '+str(dest))
        env={**os.environ,'KERNEL_BOUNDARY_ROUTER':mode,'KERNEL_DECISION_BASE_URL':'http://127.0.0.1:30000'}
        cmd=[sys.executable,str(a.root/'candidate/scripts/run-localization-benchmark.py'),'--dataset',str(a.dataset),'--output',str(dest),'--cases',','.join(cases),'--profiles','log+source','--base','http://127.0.0.1:11434','--transport','ollama-native','--eager-boundary','--source-triage','--max-calls','8','--timeout','240']
        with (a.root/(name+'.log')).open('w') as log:result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
        print(name,'exit',result.returncode,flush=True)
        if result.returncode:raise RuntimeError('Evaluation failed; log retained')
        print(json.loads((dest/'results.json').read_text())['aggregate'],flush=True)
if __name__=='__main__':main()
