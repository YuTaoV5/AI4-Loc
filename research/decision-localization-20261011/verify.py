"""Independent checks of the published experiment and exact paired inference."""
import csv,json,pathlib,hashlib,collections,math
import numpy as np
from scipy.stats import permutation_test
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
read=lambda n:json.loads((HERE/'results'/n).read_text(encoding='utf-8'))
p=read('protocol.json');s=read('statistics.json')
with (HERE/'results/boundary-trials.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
assert len(rows)==135 and len({(r['caseId'],r['repeat'],r['variant']) for r in rows})==135
assert collections.Counter(r['variant'] for r in rows)=={v['id']:27 for v in p['variants']}
for r,x in zip(sorted(rows,key=lambda r:int(r['ordinal'])),p['schedule']):
 assert r['caseId']==x['caseId'] and int(r['repeat'])==x['repeat'] and r['variant']==x['variant']
 assert r['correct']=='True' and r['isolationPassed']=='True' and r['status']=='completed'
means={v['id']:np.array([np.mean([float(r['seconds']) for r in rows if r['variant']==v['id'] and r['caseId']==c]) for c in p['cases']]) for v in p['variants']}
for name,a,b in [('C3-first minus D3-first','C3-first','D3-first'),('D3-first minus D1-first','D3-first','D1-first'),('C3-tail minus D3-tail','C3-tail','D3-tail')]:
 result=permutation_test((means[a],means[b]),lambda x,y:np.mean(x-y),permutation_type='samples',n_resamples=np.inf,alternative='two-sided')
 assert math.isclose(float(result.pvalue),s['contrasts'][name]['caseSignFlipP'],abs_tol=1e-12)
 assert math.isclose(float(result.statistic),s['contrasts'][name]['meanDifferenceSeconds'],abs_tol=1e-12)
for n,h in p['frozenCode'].items():
 f=HERE/n if n=='boundary-worker.py' else HERE/'frozen'/n
 assert hashlib.sha256(f.read_bytes()).hexdigest()==h,(n,'frozen source mismatch')
assert hashlib.sha256((HERE/'run-boundary-ablation.py').read_bytes()).hexdigest()==p['evaluatorSha256']
e=read('measured-decision-example.json')
for answer in e['answers'].values():assert math.isclose(sum(answer['probabilities'].values()),1,abs_tol=1e-8)
assert e['answers']['family']['choice']=='memory_lifetime'
print(json.dumps({'trials':135,'uniqueCases':9,'mechanismGroups':5,'scheduleVerified':True,'scipyExactTestsVerified':3,'frozenSourcesVerified':True,'measuredExampleVerified':True},indent=2))
