"""Real endpoint smoke verification, no website/business writes or benchmark scoring."""
import argparse,json,math,pathlib,time,urllib.request,urllib.error,sys
p=argparse.ArgumentParser();p.add_argument('--base',default='http://127.0.0.1:30002');p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--agent-scripts',type=pathlib.Path);a=p.parse_args();model='perplexity-ai/pplx-decider-v1-27b';revision='b01a5cbaca5391f73bd55103d4f27e8982cd5e60'
def request(path,payload=None):
 data=json.dumps(payload).encode() if payload is not None else None
 req=urllib.request.Request(a.base+path,data=data,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=180) as response:return json.load(response)
health=request('/health');assert health['ready'] and health['revision']==revision and health['model']==model
payload={'model':model,'state':'BUG: KASAN: use-after-free in synthetic_probe. Evidence is a synthetic startup check.','questions':{
 'family':{'type':'choice','instructions':'Classify the explicit diagnostic.','criteria':{'use_after_free':'Explicit KASAN use-after-free','out_of_memory':'Out-of-memory killer','unknown':'No explicit diagnostic'}},
 'present':{'type':'noul','instructions':'Does the supplied text explicitly report KASAN use-after-free?'},
 'severity':{'type':'score','instructions':'Rate how explicitly a memory safety error is reported.','criteria':['No diagnostic','Ambiguous warning','Explicit invalid memory access']}}}
start=time.monotonic();reply=request('/v1/systemone',payload);seconds=time.monotonic()-start
assert reply['model']==model and reply['usage']['output_tokens']==0 and reply['usage']['input_tokens']>0
assert reply['answers']['family']['choice']=='use_after_free'
assert 0<=reply['answers']['present']['noul']<=1 and reply['answers']['present']['noul']>.5
assert 0<=reply['answers']['severity']['score']<=2
for name in ['family','severity']:
 values=reply['answers'][name]['probabilities'];assert all(math.isfinite(v) and 0<=v<=1 for v in values.values()) and abs(sum(values.values())-1)<1e-5
negative=[]
for body in [{'questions':payload['questions']},{**payload,'model':'wrong-checkpoint'},{**payload,'questions':{'bad':{'type':'choice','criteria':{}}}}]:
 try:request('/v1/systemone',body);raise AssertionError('Invalid request accepted')
 except urllib.error.HTTPError as error:assert error.code==422;negative.append(error.code)
try:request('/v1/chat/completions',{});raise AssertionError('Unexpected Chat route')
except urllib.error.HTTPError as error:assert error.code==404
client=None
if a.agent_scripts:
 sys.path.insert(0,str(a.agent_scripts));from decision_plugin import DecisionClient
 from boundary_router import QUESTIONS,boundary_state
 audit_dir=a.output.parent/'client-smoke';audit_dir.mkdir(exist_ok=True)
 incident={'firstDiagnosticLine':1,'lines':[{'line':1,'text':'BUG: KASAN: use-after-free in synthetic_probe+0x1/0x20'}],'available':{'log':True,'source':False,'artifacts':False}}
 start=time.monotonic();client=DecisionClient(a.base,audit_dir,180,api='systemone').decide(boundary_state(incident),QUESTIONS)
 assert client['answers']['family']['choice']=='memory_lifetime' and client['usage']['completion_tokens']==0
 client={'seconds':time.monotonic()-start,'family':client['answers']['family']['choice'],'stage':client['answers']['stage']['choice'],'reporter':client['answers']['reporter']['choice'],'usage':client['usage']}
result={'checkedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'passed':True,'health':health,'syntheticOnly':True,'request':payload,'response':reply,'seconds':seconds,'invalidRequestStatus':negative,'chatStatus':404,'agentClient':client}
a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'passed':True,'seconds':seconds,'agentClient':client,'output':str(a.output)}))
