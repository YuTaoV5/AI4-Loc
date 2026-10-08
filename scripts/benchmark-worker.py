"""Runs inside the evaluator-free namespace; fails closed if its canary is visible."""
import json,os,pathlib,sys
from localization_agent import run
request=json.loads(pathlib.Path(sys.argv[1]).read_text())
canary=pathlib.Path(os.environ['EVALUATOR_CANARY_PATH'])
checks={'evaluatorCanaryVisible':canary.exists(),'hostRootVisible':pathlib.Path('/root/gpufree-data').exists(),
        'businessDataVisible':pathlib.Path('/opt/kernel-insight/data/state.json').exists(),
        'procMounted':pathlib.Path('/proc/1/root').exists(),'workspaceAnonymous':request['workspace']=='/work'}
pathlib.Path('/work/isolation-audit.json').write_text(json.dumps(checks,indent=2))
assert not any(checks[k] for k in ['evaluatorCanaryVisible','hostRootVisible','businessDataVisible','procMounted']) and checks['workspaceAnonymous']
result=run(request,lambda x:print(json.dumps(x,ensure_ascii=False),flush=True))
print(json.dumps(result,ensure_ascii=False),flush=True)
