"""Build collector-evidence boundary annotations, not independent expert annotations.
Only the fixed development test suite supported below is accepted. Labels stay evaluator-side.
"""
import argparse,hashlib,json,pathlib,re

def build(dataset):
    m=json.loads((dataset/'manifest.json').read_text());annotations={}
    for c in m['cases']:
        if c['status']!='ready' or c['split']!='test':continue
        raw=(dataset/c['files']['rawLog']['path']).read_bytes();text=raw.decode('utf-8','replace');lines=text.splitlines()
        label=json.loads((dataset/c['files']['groundTruth']['path']).read_text());run=json.loads((dataset/c['files']['run']['path']).read_text())
        if run.get('timedOut') or run.get('returnCode') is None:raise ValueError('Invalid collector record')
        if c['family']=='healthy':
            if 'KI_BASELINE_DONE' not in text or re.search(r'BUG: KASAN|Kernel panic|WARNING: possible circular|INFO: task .*blocked for more',text):raise ValueError('Healthy control has diagnostic')
            stage='unknown';panic='none';evidence=[{'line':lines.index('KI_BASELINE_DONE')+1,'text':'KI_BASELINE_DONE'}]
        else:
            signatures={'memory_uaf':('use_after_free',r'BUG: KASAN: use-after-free'),'hung_task':('hung_task',r'INFO: task .*blocked for more'),'usercopy':('usercopy',r'usercopy: Kernel memory (?:exposure|overwrite) attempt detected'),'lock_order':('lock_dependency',r'WARNING: possible circular locking dependency detected')}
            if c['family'] not in signatures:raise ValueError('No reviewed collector mapping for '+c['family'])
            panic,pattern=signatures[c['family']];hits=[i for i,line in enumerate(lines) if re.search(pattern,line)]
            start=next(i for i,line in enumerate(lines) if 'KI_SCENARIO_BEGIN' in line)
            if not hits or hits[0]<=start:raise ValueError('Diagnostic is not in triggered workload')
            stage='runtime';evidence=[{'line':hits[0]+1,'text':lines[hits[0]]}]
        annotations[c['id']]={'status':'collector_verified','stage':stage,'panicType':panic,'rawLogSha256':hashlib.sha256(raw).hexdigest(),'evidence':evidence,'method':'Collector init starts user-space debugfs workload after kernel boot; raw first detector and injector label cross-checked. Healthy stage unknown because no incident. Not independently adjudicated production ground truth.'}
    return {'schema':'benchmark-boundary-annotations/v1','datasetManifestSha256':hashlib.sha256((dataset/'manifest.json').read_bytes()).hexdigest(),'evaluationType':'public-development-practice','independentExpertAdjudication':False,'cases':annotations}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('dataset',type=pathlib.Path);a=p.parse_args();out=a.dataset/'benchmark-annotations.json';out.write_text(json.dumps(build(a.dataset),ensure_ascii=False,indent=2),encoding='utf-8');print(out)
