"""Audit direct oracle channels and record synthetic-benchmark shortcut limitations."""
import argparse,hashlib,json,pathlib,re,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools/kernel-lab'))
from dataset_contract import resolve,validate,agent_log
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from localization_agent import Inspector

def audit(dataset,history=None):
    m=json.loads((dataset/'manifest.json').read_text());rows=[]
    pattern=re.compile(r'KI_(?:SCENARIO|TRIGGER|BASELINE|RUNTIME|UNKNOWN|MODULE)|ki\.(?:scn|act)=(?!<withheld>)\S+|lkdtm: Performing direct entry|ki_bench: trigger action=|rootLocation|diagnosticEvidence')
    for case in m['cases']:
        if case['status']!='ready':continue
        text=resolve(dataset,case['files']['agentLog']).read_text(encoding='utf-8',errors='replace')
        raw=resolve(dataset,case['files']['rawLog']).read_bytes()
        rows.append({'caseId':case['id'],'matches':[{'line':i+1,'text':x[:160]} for i,x in enumerate(text.splitlines()) if pattern.search(x)],'derivedMatchesContract':agent_log(raw)==resolve(dataset,case['files']['agentLog']).read_bytes()})
    source=dataset/'shared/source-tree'
    forbidden=[str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() and (p.name in ['ground-truth.json','manifest.json','expected.json','labels.json'] or p.name.endswith('.jsonl'))]
    old={'traceCount':0,'collectorReads':[]}
    if history:
        for p in history.rglob('localization-trace.json'):
            old['traceCount']+=1
            trace=json.loads(p.read_text())
            for row in trace.get('evidence',{}).get('commands',[]):
                if row['tool']=='source_read' and pathlib.PurePosixPath(row['arguments'].get('path','')).suffix not in {'.c','.h','.S','.s','.rs','.cpp','.cc','.hpp'}:
                    old['collectorReads'].append({'trace':str(p.relative_to(history)),'path':row['arguments'].get('path')})
    # Negative probes run through the actual tool, not only through source-code inspection.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root=pathlib.Path(tmp);(root/'source').mkdir();(root/'source/guest_init.sh').write_text('SCN=hidden_label');(root/'source/answer.c').write_text('int ok(void){return 0;}')
        inspector=Inspector(root);probes={x:inspector.execute('source_read',{'path':x,'start':1,'count':3}) for x in ['guest_init.sh','../ground-truth.json','manifest.json','answer.c']}
    return {'schema':'benchmark-leakage-audit/v1','manifestSha256':hashlib.sha256((dataset/'manifest.json').read_bytes()).hexdigest(),
            'integrity':validate(dataset),'readyLogs':len(rows),'directMetadataClean':all(not r['matches'] and r['derivedMatchesContract'] for r in rows),
            'logChecks':rows,'sourceForbiddenMetadataFiles':forbidden,'sourceCollectorScriptExists':(source/'guest_init.sh').exists(),
            'negativeProbes':probes,'historicalTraceAudit':old,
            'limitations':['This is a synthetic injection benchmark: descriptive function names and intentional fault code are valid supplied inputs but enable shortcuts.',
                           'Existing test split has been inspected during prior development; it is not an untouched blind holdout.',
                           'Historical in-process evaluation lacked OS isolation. No blanket zero-leakage guarantee is made for historical runs.',
                           'No audit can establish absence of model pretraining contamination without model training provenance.']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=pathlib.Path,required=True);p.add_argument('--history',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    result=audit(a.dataset,a.history);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:result[k] for k in ['readyLogs','directMetadataClean','sourceForbiddenMetadataFiles','historicalTraceAudit']},ensure_ascii=False))
