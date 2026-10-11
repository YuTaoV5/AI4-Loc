"""Isolated typed-decision client; evaluator labels never enter this worker."""
import sys,pathlib,json,time
sys.path.insert(0,'/agent')
from decision_plugin import DecisionClient
from boundary_router import boundary_state,QUESTIONS
w=pathlib.Path('/work');req=json.loads((w/'input.json').read_text());audit={'anonymous':str(w)=='/work','evaluatorVisible':pathlib.Path('/opt/kernel-insight/data/evaluation-datasets').exists(),'businessVisible':pathlib.Path('/opt/kernel-insight/data/state.json').exists(),'procVisible':pathlib.Path('/proc/self/root').exists()};assert audit['anonymous'] and not any(audit[k] for k in ['evaluatorVisible','businessVisible','procVisible'])
t=time.monotonic();out={'status':'failed','audit':audit}
try:
 reply=DecisionClient(req['base'],w,180,api='systemone').decide(boundary_state(req['incident']),QUESTIONS)
 out.update(status='completed',answers={k:{n:v for n,v in a.items() if n not in ['prompt_token_ids','label_token_ids']} for k,a in reply['answers'].items()},usage=reply['usage'])
except Exception as e:out['error']=str(e)[:500]
out['seconds']=time.monotonic()-t;(w/'response.json').write_text(json.dumps(out),encoding='utf-8')
