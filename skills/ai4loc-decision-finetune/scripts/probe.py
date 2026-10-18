"""Explicit synthetic API probe, not a benchmark; standard library HTTP client."""
import argparse,json,time,urllib.request,pathlib,math
def main():
    p=argparse.ArgumentParser();p.add_argument('--base-url',required=True);p.add_argument('--model',required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Probe output must be new')
    result={'scope':'Synthetic deployment validation, excluded from benchmark','requests':[]}
    def post(route,body):
        t=time.monotonic();req=urllib.request.Request(a.base_url.rstrip('/')+route,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        return t,urllib.request.urlopen(req,timeout=120)
    state='Synthetic validation: BUG: KASAN: use-after-free. This is an API smoke example.'
    body={'model':a.model,'input':state,'questions':[{'id':'family','type':'choice','question':'Which family best matches the diagnostic?','options':[{'name':n,'description':n.replace('_',' ')} for n in ['memory_lifetime','locking','rcu_progress']]}],'temperature':1,'prompt_format_version':1}
    t,r=post('/v1/decisions',body)
    with r:d=json.load(r)
    seconds=time.monotonic()-t;answer=d['answers']['family'];probs=answer['probabilities'];values=list(probs.values()) if isinstance(probs,dict) else probs
    assert len(values)==3 and all(math.isfinite(x) and 0<=x<=1 for x in values) and abs(sum(values)-1)<1e-4
    assert answer['choice']=='memory_lifetime',answer
    result['requests'].append({'api':'decision','seconds':seconds,'answer':answer})
    body={'model':a.model,'messages':[{'role':'user','content':state+'\nA: memory_lifetime\nB: locking\nC: rcu_progress\nReply with one letter only.'}],'chat_template_kwargs':{'enable_thinking':False},'temperature':0,'max_tokens':1,'stream':True}
    t,r=post('/v1/chat/completions',body);first=None;content=''
    with r:
        for line in r:
            if not line.startswith(b'data: '):continue
            raw=line[6:].strip()
            if raw==b'[DONE]':break
            v=json.loads(raw);delta=v['choices'][0].get('delta',{}).get('content')
            if isinstance(delta,str) and delta:
                if first is None:first=time.monotonic()-t
                content+=delta
    assert first is not None,'No nonempty Chat content'
    assert content.strip()=='A','Synthetic Chat classification did not return A'
    result['requests'].append({'api':'chat','first_nonempty_content_seconds':first,'total_seconds':time.monotonic()-t,'content':content})
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
