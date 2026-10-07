"""Evaluator owns labels; agent sees only selected inputs. Scores location, not category."""
import argparse,hashlib,json,os,pathlib,sys,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools/kernel-lab'))
from dataset_contract import PROFILES,validate,resolve
from localization_agent import run

def evaluate(report,label,profile):
    truth=label['rootLocation'];locations=(report or {}).get('localization',{}).get('locations',[])
    hit=any(x.get('path')==truth['path'] and x.get('symbol')==truth['symbol'] and x.get('startLine',0)<=truth['endLine'] and x.get('endLine',0)>=truth['startLine'] for x in locations)
    symbols=(report or {}).get('localization',{}).get('candidateSymbols',[])
    return {'codeLocationHit':hit,'functionHit':truth['symbol'] in symbols or any(x.get('symbol')==truth['symbol'] for x in locations),'rootCauseMechanismCorrect':None,'introducingCommitCorrect':None,'requiresHumanMechanismReview':True,'identifiability':'log absent: multiple scenarios share identical source/artifacts' if 'log' not in PROFILES[profile] else 'incident log supplied'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--cases',default='corrupt_uaf_kmalloc,leak_kmalloc,lock_mutex_abba,lock_sleep_atomic,pressure_oom,baseline');p.add_argument('--profiles',default='log+artifacts+source,log');p.add_argument('--model',default='qwen3.8:27b-kernel-8k');p.add_argument('--base',default='http://127.0.0.1:11435/v1');p.add_argument('--transport',choices=['openai','ollama-native'],default='openai');p.add_argument('--max-calls',type=int,default=8);p.add_argument('--timeout',type=int,default=240);p.add_argument('--eager-boundary',action='store_true');p.add_argument('--source-triage',action='store_true');a=p.parse_args()
    validation=validate(a.dataset)
    if not validation['complete']:raise ValueError('Dataset incomplete: '+str(validation['errors']))
    manifest=json.loads((a.dataset/'manifest.json').read_text(encoding='utf-8'));a.output.mkdir(parents=True,exist_ok=True)
    result={'schema':'kernel-localization-benchmark/v1','datasetManifestSha256':hashlib.sha256((a.dataset/'manifest.json').read_bytes()).hexdigest(),'agentSha256':hashlib.sha256(pathlib.Path(__file__).with_name('localization_agent.py').read_bytes()).hexdigest(),'model':a.model,'configuration':{'transport':a.transport,'eagerBoundary':a.eager_boundary,'sourceTriage':a.source_triage,'maxModelCalls':a.max_calls,'timeoutSeconds':a.timeout},'protocol':'Source location match is not mechanism correctness. No introducing-commit labels exist in synthetic injection set. Failures count in denominator. No scores fabricated for missing labels.','runs':[]}
    for case_id in a.cases.split(','):
        case=next(c for c in manifest['cases'] if c['id']==case_id and c['status']=='ready');label=json.loads(resolve(a.dataset,case['files']['groundTruth']).read_text(encoding='utf-8'))
        for profile in a.profiles.split(','):
            selected=PROFILES[profile];work=a.output/'workspaces'/(case_id+'__'+profile);work.mkdir(parents=True,exist_ok=False)
            if 'log' in selected:(work/'input.log').write_bytes(resolve(a.dataset,case['files']['agentLog']).read_bytes())
            if 'source' in selected:(work/'source').symlink_to(a.dataset/'shared/source-tree',target_is_directory=True)
            if 'artifacts' in selected:
                files=[]
                for key in ['vmlinux','module','config','systemMap']:
                    item=manifest['shared'][key];source=resolve(a.dataset,item);name=source.name;os.link(source,work/name);files.append({'path':name,'kind':key,'sha256':item['sha256']})
                (work/'artifacts.json').write_text(json.dumps({'files':files,'runtimeBuildId':manifest['build']['buildId'],'runtimeIdentityBasis':'raw guest GNU notes matched frozen ELF by dataset validator'}))
            request={'workspace':str(work),'model':a.model,'baseUrl':a.base,'transport':a.transport,'eagerBoundary':a.eager_boundary,'sourceTriage':a.source_triage,'timeout':a.timeout,'maxModelCalls':a.max_calls}
            output=run(request,lambda e:print(case_id,profile,e['message'],flush=True));report=output.get('analysis')
            row={'caseId':case_id,'family':case['family'],'profile':profile,'split':case['split'],'status':'completed' if report else 'failed','metrics':output['metrics'],'scores':evaluate(report,label,profile),'analysis':report,'error':output.get('error')};result['runs'].append(row)
            ready=result['runs'];eligible=[r for r in ready if 'source' in PROFILES[r['profile']] and 'log' in PROFILES[r['profile']] and r['family']!='healthy']
            result['aggregate']={'completed':sum(r['status']=='completed' for r in ready),'total':len(ready),'codeLocationAccuracy':sum(r['scores']['codeLocationHit'] for r in eligible)/len(eligible) if eligible else None,'codeLocationDenominator':len(eligible),'modelRequests':sum(r['metrics']['modelRequests'] for r in ready),'localizationSeconds':sum(r['metrics']['localizationSeconds'] for r in ready),'rootCauseAccuracy':None}
            (a.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('DONE',case_id,profile,row['status'],row['scores'],flush=True)
    print(json.dumps(result['aggregate']),flush=True)
if __name__=='__main__':main()
