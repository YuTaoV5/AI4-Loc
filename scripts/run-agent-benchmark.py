"""Evaluate actual website model jobs; expected answers stay outside agent workspaces."""
import argparse, datetime, http.client, json, os, pathlib, time, urllib.request, urllib.error
parser=argparse.ArgumentParser()
parser.add_argument('--base',default='http://127.0.0.1:8787')
parser.add_argument('--limit',type=int,default=6)
parser.add_argument('--output',default='/opt/kernel-insight/data/agent-benchmark.json')
parser.add_argument('--resume',action='store_true')
args=parser.parse_args();token=None
def request(path,body=None):
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(args.base+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
        except (urllib.error.URLError,http.client.RemoteDisconnected,TimeoutError,ConnectionError):
            if body is not None or attempt==3:raise
            print('Read transport interrupted; retrying without resubmitting job',flush=True);time.sleep(3)
token=request('/api/auth/login',{'username':os.environ.get('BENCHMARK_USERNAME','admin'),'password':os.environ.get('BENCHMARK_PASSWORD','admin')})['token']
dataset=request('/api/benchmark')
result={'dataset':dataset['version'],'startedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'protocol':'Actual dsh/Qwen turns. Expected labels and community root causes are not supplied to the model. Category accuracy is not root-cause accuracy.','cases':[]}
out=pathlib.Path(args.output)
if args.resume and out.exists():result=json.loads(out.read_text(encoding='utf-8'))
def save():out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
save()
for case in dataset['cases'][:args.limit]:
    if any(x['caseId']==case['id'] and x['status'] not in ('queued','running') for x in result['cases']):continue
    existing=[j for j in request('/api/jobs') if j.get('benchmarkCaseId')==case['id'] and j['createdAt']>=result['startedAt']]
    start=time.monotonic();job=existing[0] if args.resume and existing else request('/api/benchmark/'+case['id']+'/analyze',{'autoSource':False,'forceRerun':True})
    print('START',case['id'],job['id'],flush=True)
    while True:
        progress=request('/api/jobs/'+job['id']+'/progress')
        if progress['status'] not in ('queued','running'):break
        print('PROGRESS',case['id'],progress.get('stage'),progress.get('agent',{}).get('message',''),flush=True);time.sleep(10)
    job=next(x for x in request('/api/jobs') if x['id']==job['id'])
    row={'caseId':case['id'],'split':case['split'],'jobId':job['id'],'status':job['status'],'expectedCategory':case['category'],'modelCategory':job.get('analysis',{}).get('category') if job.get('analysis',{}).get('agent') else None,'seconds':round((datetime.datetime.fromisoformat(job.get('analyzedAt') or job.get('agent',{}).get('updatedAt') or datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')).timestamp()-datetime.datetime.fromisoformat(job['createdAt']).timestamp()),3),'error':job.get('error'),'agent':job.get('analysis',{}).get('agent')}
    row['routing']=job.get('analysis',{}).get('routing');row['routingError']=job.get('analysis',{}).get('routingError')
    row['categoryCorrect']=row['modelCategory']==row['expectedCategory'];result['cases'].append(row);save();print('DONE',case['id'],row['status'],row['modelCategory'],row['seconds'],flush=True)
result['completedAt']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());result['completedModelCases']=sum(bool(x['agent']) for x in result['cases']);result['categoryAccuracy']=sum(x['categoryCorrect'] for x in result['cases'])/len(result['cases']);test=[x for x in result['cases'] if x['split']=='test'];result['testCategoryAccuracy']=sum(x['categoryCorrect'] for x in test)/len(test) if test else None
save();print('RESULT',result['categoryAccuracy'],flush=True)
