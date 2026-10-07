"""Reproducible annotation-only repair. Never modifies raw logs or build artifacts."""
import argparse,json,pathlib,re,shutil
from dataset_contract import record,validate
p=argparse.ArgumentParser();p.add_argument('root',type=pathlib.Path);a=p.parse_args();root=a.root.resolve();m=json.loads((root/'manifest.json').read_text())
if m.get('annotationRevision')=='v2':
    print(json.dumps(validate(root),indent=2));raise SystemExit(0)
history=root/'annotation-history/v1';history.mkdir(parents=True,exist_ok=False);shutil.copy2(root/'manifest.json',history/'manifest.json')
for case in m['cases']:
    path=root/case['files']['groundTruth']['path'];label=json.loads(path.read_text());shutil.copy2(path,history/(case['id']+'.json'))
    label['diagnosticEvidence']=[e for e in label['diagnosticEvidence'] if not re.search(r'\bdebug:',e['text'],re.I)]
    source=(root/case['files']['causalSource']['path']).read_text().splitlines();loc=label['rootLocation']
    label['causalCode']=[{'line':n,'text':source[n-1]} for n in range(loc['startLine'],min(loc['endLine'],loc['startLine']+79)+1)]
    label['annotationRevision']='v2: bounded BUG signature; exact causal code retained'
    if case['status']=='ready' and case['family']!='healthy' and not label['diagnosticEvidence']:
        case['status']='excluded';case['exclusionReasons'].append('diagnostic consisted only of normal debug output');label['status']='excluded'
    path.write_text(json.dumps(label,ensure_ascii=False,indent=2));case['files']['groundTruth']=record(root,path);(path.parent/'case.json').write_text(json.dumps(case,indent=2))
m['annotationRevision']='v2';(root/'manifest.json').write_text(json.dumps(m,indent=2));report=validate(root);(root/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(0 if report['complete'] else 2)
