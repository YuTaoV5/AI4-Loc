"""Trusted evaluator for website runs. Never mount labels, manifest, or business state into workers."""
import argparse,hashlib,importlib.util,json,os,pathlib,signal,sys,time,uuid
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools/kernel-lab'))
from dataset_contract import validate,resolve
spec=importlib.util.spec_from_file_location('isolated_evaluator',pathlib.Path(__file__).with_name('run-localization-benchmark.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def evaluate(report,label,gold,healthy=False):
    scene=(report or {}).get('firstScene',{});loc=(report or {}).get('localization',{});locations=loc.get('locations',[])
    truth=label['rootLocation']
    hit=any(x.get('path')==truth['path'] and x.get('symbol')==truth['symbol'] and isinstance(x.get('startLine'),int) and isinstance(x.get('endLine'),int) and 0<=x['endLine']-x['startLine']<40 and x['startLine']<=truth['endLine'] and x['endLine']>=truth['startLine'] for x in locations[:2]) if len(locations)<=2 else False
    if healthy:hit=bool(report) and scene.get('panicType')=='none' and not locations and not loc.get('candidateSymbols') and not report.get('hypotheses')
    return {'stageHit':scene.get('stage')==gold.get('stage') if gold else None,'panicTypeHit':scene.get('panicType')==gold.get('panicType') if gold else None,'codeLocationHit':hit,'rootCauseMechanismCorrect':None,'introducingCommitCorrect':None}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('control',type=pathlib.Path);a=parser.parse_args();control=json.loads(a.control.read_text(encoding='utf-8-sig'))
    dataset=pathlib.Path(control['dataset']);out=pathlib.Path(control['output']);out.mkdir(parents=True,exist_ok=True)
    m=json.loads((dataset/'manifest.json').read_text());annotations=json.loads((dataset/'benchmark-annotations.json').read_text()) if (dataset/'benchmark-annotations.json').exists() else {'cases':{}}
    expected=control['datasetSha256'];actual=hashlib.sha256((dataset/'manifest.json').read_bytes()).hexdigest()
    if actual!=expected:raise ValueError('Dataset changed since submission')
    ann_sha=hashlib.sha256((dataset/'benchmark-annotations.json').read_bytes()).hexdigest() if (dataset/'benchmark-annotations.json').exists() else None
    if ann_sha!=control['annotationsSha256']:raise ValueError('Scoring annotations changed since submission')
    verified=validate(dataset)
    if not verified['complete']:raise ValueError('Dataset contract failed: '+str(verified['errors'])[:1500])
    cases=[c for c in m['cases'] if c['status']=='ready' and c['split']=='test']
    if [c['id'] for c in cases]!=control['caseIds']:raise ValueError('Fixed suite changed')
    rows=[];started=time.monotonic()
    for index,c in enumerate(cases):
        work=out/'workspaces'/str(uuid.uuid4());work.mkdir(parents=True,exist_ok=False)
        (work/'input.log').write_bytes(resolve(dataset,c['files']['agentLog']).read_bytes())
        (work/'source').symlink_to(dataset/'shared/source-tree',target_is_directory=True)
        files=[]
        for key in ['vmlinux','module','config','systemMap']:
            item=m['shared'][key];source=resolve(dataset,item);name=source.name
            # Read-only bind by sandbox: link avoids copying the 1 GB ELF for each test.
            (work/name).symlink_to(source);files.append({'path':name,'kind':key,'sha256':item['sha256']})
        (work/'artifacts.json').write_text(json.dumps({'files':files,'runtimeBuildId':m['build']['buildId'],'runtimeIdentityBasis':'Guest notes matched frozen ELF by dataset validator'}))
        request={**control['agent'],'workspace':str(work),'eagerBoundary':True,'sourceTriage':True,'fastFinal':False,'userPrompt':control['profile']['prompt']}
        # No recipe IDs, case names, expected labels, scores, or host paths enter the model context.
        if control['profile']['agentId']=='decision-chat':request['boundaryRouter']={'baseUrl':control['decisionBaseUrl'],'timeout':15,'api':control.get('decisionApi','decisions')}
        began=time.monotonic();error=None;output={};isolation=False
        print(json.dumps({'type':'progress','completed':index,'total':len(cases),'phase':'case','message':f'正在执行匿名样本 {index+1}/{len(cases)}'}),flush=True)
        try:
            output=module.isolated_run(request,work)
            audit=json.loads((work/'isolation-audit.json').read_text())
            isolation=audit.get('workspaceAnonymous') is True and all(audit.get(k) is False for k in ['evaluatorCanaryVisible','hostRootVisible','businessDataVisible','procMounted'])
            if not isolation:raise ValueError('Isolation audit failed')
        except Exception as exc:error=str(exc)[:800]
        # Read labels only after worker termination; this process is outside its namespace.
        label=json.loads(resolve(dataset,c['files']['groundTruth']).read_text());gold=annotations.get('cases',{}).get(c['id'],{})
        gold_complete=gold.get('status')=='collector_verified' and gold.get('rawLogSha256')==c['files']['rawLog']['sha256'] and bool(gold.get('stage')) and bool(gold.get('panicType')) and bool(label.get('rootLocation'))
        report=output.get('analysis');metrics=output.get('metrics',{});elapsed=round(time.monotonic()-began,4)
        row={'caseId':c['id'],'workspaceId':work.name,'status':'completed' if report and not error else 'failed','error':error or output.get('error'),'goldComplete':gold_complete,'isolationVerified':isolation,'scores':evaluate(report,label,gold if gold_complete else {},c['family']=='healthy'),'metrics':metrics,'wallSeconds':elapsed,'analysis':report}
        rows.append(row)
        result={'schema':'website-agent-benchmark/v1','datasetSha256':expected,'annotationsSha256':ann_sha,'rows':rows,'wallSeconds':round(time.monotonic()-started,4),'validation':verified,'complete':len(rows)==len(cases)}
        target=out/'results.json';temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(target)
        print(json.dumps({'type':'progress','completed':index+1,'total':len(cases),'phase':'case','message':f'已完成 {index+1}/{len(cases)}'}),flush=True)
    print(json.dumps({'type':'complete','count':len(rows)}),flush=True)
if __name__=='__main__':main()
