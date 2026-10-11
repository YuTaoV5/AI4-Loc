"""Independent offline trial accounting and placement verification."""
import json,pathlib,collections,math,statistics
from scipy.stats import binomtest
H=pathlib.Path(__file__).resolve().parent;read=lambda n:json.loads((H/'results'/n).read_text(encoding='utf-8'));rows=read('trials.json');protocol=read('protocol.json');runtime=read('pplx-runtime.json');s=read('statistics.json');audit=read('audit.json')
assert len(rows)==121 and collections.Counter(r['arm'] for r in rows)=={'pplx':78,'generic':43}
assert sum(r['split']=='test' for r in rows)==54 and sum(not r['scored'] for r in rows)==35
assert len({r['caseId'] for r in rows if r['scored']})==25 and len({r['caseId'] for r in rows})==60
assert runtime['parameterDevices']==['cuda:0'] and runtime['placement']=='full-gpu' and runtime['cpuMemoryLimit'] is None
assert read('completion.json')['restoration']['restored']
assert all(audit['experimentCodeHashesPassed'].values()) and all(audit['frozenCodeHashesPassed'].values())
for phase in ['pplxPhase','genericPhase']:assert not audit[phase]['production30000Responding'] and not audit[phase]['otherExperimentalArmResponding']
assert len({(r['caseId'],r['arm'],r['repeat']) for r in rows})==121
for r,p in zip(sorted(rows,key=lambda r:r['ordinal']),protocol['schedule']):
 assert all(r[k]==p[k] for k in ['caseId','arm','repeat','scored']) and r['isolationPassed']
 assert r['correct'] is None if not r['scored'] else isinstance(r['correct'],bool)
 assert r['gold']==protocol['taxonomy'].get(r['injectionFamily'])
 if r['scored']:assert r['correct']==(r['family']==r['gold'])
 assert r['status']=='completed' and r['outputTokens']==0 and math.isfinite(r['seconds']) and r['seconds']>0
 assert len(r['answers'])==3
 for answer in r['answers'].values():
  probabilities=answer['probabilities'];assert abs(sum(probabilities.values())-1)<1e-5 and all(math.isfinite(p) and 0<=p<=1 for p in probabilities.values());assert probabilities[answer['choice']]>=max(probabilities.values())-1e-6
for arm in ['generic','pplx']:
 test=[r for r in rows if r['arm']==arm and r['split']=='test'];assert sum(r['correct'] for r in test)==s['primary'][arm]['correct']
 assert math.isclose(statistics.mean(r['seconds'] for r in test),s['primary'][arm]['meanSeconds'])
 assert len(test)==27 and all(v==3 for v in collections.Counter(r['caseId'] for r in test).values())
 one=[r for r in rows if r['arm']==arm and r['scored'] and r['repeat']==0];assert sum(r['correct'] for r in one)==s['secondaryProxy'][arm]['correct']
b=s['accuracyMcNemar']['genericOnlyCorrect'];c=s['accuracyMcNemar']['pplxOnlyCorrect'];assert s['accuracyMcNemar']['exactTwoSidedP']==(binomtest(b,b+c).pvalue if b+c else 1.0)
print('PASS: 121 calls, all-GPU placement, exclusive phases, restoration, finite distributions and frozen schedule.')
