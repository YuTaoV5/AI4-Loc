import sys,pathlib,json,time,urllib.request,hashlib
sys.path.insert(0,'/agent')
from decision_plugin import DecisionClient
from boundary_router import chat_boundary
p=pathlib.Path('/work');request=json.loads((p/'input.json').read_text());incident=request['incident'];started=time.monotonic()
audit={'evaluatorVisible':pathlib.Path('/opt/kernel-insight/data/evaluation-datasets').exists(),'businessDataVisible':pathlib.Path('/opt/kernel-insight/data/state.json').exists(),'procVisible':pathlib.Path('/proc/self/root').exists(),'anonymousWorkspace':str(p)=='/work'}
assert not any(audit[k] for k in ['evaluatorVisible','businessDataVisible','procVisible'])
result={'audit':audit,'status':'failed'}
try:
 if request['mode']=='decision':
  from boundary_router import boundary_state
  client=DecisionClient(request['base'],p,60,api='decisions');reply=client.decide(boundary_state(incident),request['questions']);result.update(family=reply['answers']['family']['choice'],usage=reply.get('usage'),answers=reply['answers'])
 else:
  reply=chat_boundary(request['base'],request['model'],incident,timeout=60);result.update(family=reply['family'],usage=reply.get('usage'));(p/'chat-trace.json').write_text(json.dumps(reply,ensure_ascii=False))
 result['status']='completed'
except Exception as e:result['error']=str(e)[:600]
result['seconds']=round(time.monotonic()-started,6)
(p/'response.json').write_text(json.dumps(result,ensure_ascii=False))
