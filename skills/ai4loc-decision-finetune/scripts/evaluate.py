"""Frozen-test choice evaluation; native Decision and identical rendered one-token Chat."""
import argparse,pathlib,json,hashlib,random,time,urllib.request,collections,math
def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=pathlib.Path,required=True);p.add_argument('--tokenizer',required=True);p.add_argument('--base-url',required=True);p.add_argument('--model',required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Use NEW evaluation output directory')
    private=a.run_dir/'dataset.private.json';f=json.loads((a.run_dir/'dataset-frozen.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(private.read_bytes()).hexdigest()==f['private_sha256']
    rows=[r for r in json.loads(private.read_text(encoding='utf-8')) if r['split']=='test'];assert rows
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(a.tokenizer,local_files_only=True);classes=f['classes'];question=f['question'];a.output.mkdir(parents=True)
    calls=[]
    def request(route,payload):
        req=urllib.request.Request(a.base_url.rstrip('/')+route,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'});return urllib.request.urlopen(req,timeout=180)
    for r in rows:
        for repeat in range(3):
            options=classes.copy();random.Random(20261016+repeat).shuffle(options);text=r['input'][:3000]
            def render():return text+'\n\nQuestion: '+question+'\n'+'\n'.join(chr(65+i)+': '+n+' - '+n.replace('_',' ') for i,n in enumerate(options))+'\nAnswer with the letter of one option only.'
            while True:
                prompt=tok.apply_chat_template([{'role':'user','content':render()}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
                ids=tok.encode(prompt,add_special_tokens=False)
                if len(ids)<=2048:break
                text=text[:-300]
                if len(text)<=100:raise ValueError('Question/options exceed context budget')
            payload={'model':a.model,'input':text,'questions':[{'id':'family','type':'choice','question':question,'options':[{'name':n,'description':n.replace('_',' ')} for n in options]}],'temperature':1,'prompt_format_version':1,'return_prompt_token_ids':True}
            for api in ['decision','chat']:
                start=time.monotonic();record={'case':r['case'],'group':r['group'],'label':r['label'],'repeat':repeat,'api':api,'status':'failed','prediction':None,'correct':False}
                try:
                    if api=='decision':
                        with request('/v1/decisions',payload) as response:v=json.load(response)
                        ans=v['answers']['family'];prob=ans['probabilities'];assert set(prob)==set(options) and all(math.isfinite(x) and 0<=x<=1 for x in prob.values()) and abs(sum(prob.values())-1)<1e-4
                        assert ans['prompt_token_ids']==ids,'Native Decision prompt does not match local Chat template'
                        record.update(prediction=ans['choice'],probabilities=prob,usage=v.get('usage',{}),prompt_token_sha256=hashlib.sha256(json.dumps(ids).encode()).hexdigest())
                    else:
                        body={'model':a.model,'messages':[{'role':'user','content':render()}],'temperature':0,'max_tokens':1,'stream':True,'stream_options':{'include_usage':True},'chat_template_kwargs':{'enable_thinking':False}}
                        content='';first=None;usage={}
                        with request('/v1/chat/completions',body) as response:
                            for line in response:
                                if not line.startswith(b'data: '):continue
                                raw=line[6:].strip()
                                if raw==b'[DONE]':break
                                v=json.loads(raw)
                                if v.get('usage'):usage=v['usage']
                                if not v.get('choices'):continue
                                s=v['choices'][0].get('delta',{}).get('content')
                                if isinstance(s,str) and s:
                                    if first is None:first=time.monotonic()-start
                                    content+=s
                        letter=content.strip();assert len(letter)==1 and 'A'<=letter<=chr(64+len(options)),'Invalid one-token answer'
                        record.update(prediction=options[ord(letter)-65],first_nonempty_content_seconds=first,usage=usage,prompt_token_sha256=hashlib.sha256(json.dumps(ids).encode()).hexdigest())
                    record.update(status='ok',correct=record['prediction']==r['label'])
                except Exception as e:record['error_type']=type(e).__name__
                record['seconds']=time.monotonic()-start;calls.append(record)
                with (a.output/'calls.jsonl').open('a',encoding='utf-8') as log:log.write(json.dumps(record,ensure_ascii=False)+'\n')
    summary=[]
    for api in ['decision','chat']:
        hits=0
        for r in rows:
            votes=[c['prediction'] for c in calls if c['case']==r['case'] and c['api']==api and c['status']=='ok'];counts=collections.Counter(votes)
            hits+=bool(counts and counts.most_common(1)[0][1]>=2 and counts.most_common(1)[0][0]==r['label'])
        cs=[c for c in calls if c['api']==api];summary.append({'api':api,'cases':len(rows),'majority_correct':hits,'accuracy':hits/len(rows),'calls':len(cs),'failed_calls':sum(c['status']!='ok' for c in cs),'mean_seconds':sum(c['seconds'] for c in cs)/len(cs)})
    result={'scope':'Reviewed first-diagnostic test, 3 option permutations per case; failures retained; not root-cause/commit accuracy or a randomized concurrency performance trial','dataset_sha256':hashlib.sha256((a.run_dir/'dataset-frozen.json').read_bytes()).hexdigest(),'mechanism_groups':len(set(r['group'] for r in rows)),'summary':summary}
    (a.output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
