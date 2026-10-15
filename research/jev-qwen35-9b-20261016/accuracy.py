"""Frozen first-diagnostic test; raw payloads private, labels only local scorer.

Each test has three deterministic option permutations. Count cases/groups,
never permutations, as independent evaluation units.
"""
import asyncio,hashlib,json,pathlib,random,time,os
import aiohttp
from transformers import AutoTokenizer
from train import render
ROOT=pathlib.Path(__file__).resolve().parent
E=pathlib.Path(os.environ['AI4LOC_RUN_DIR'])
async def main():
    rows=json.loads((ROOT/'dataset.private.json').read_text())
    frozen=json.loads((ROOT/'dataset-frozen.json').read_text());classes=frozen['classes'];question=frozen['question']
    assert hashlib.sha256((ROOT/'dataset.private.json').read_bytes()).hexdigest()==frozen['private_sha256']
    tok=AutoTokenizer.from_pretrained('/root/gpufree-data/systemone/models/Qwen3.5-9B',local_files_only=True)
    (E/'accuracy-raw').mkdir(exist_ok=False)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=180)) as session:
        for r in rows:
            if r['split']!='test':continue
            for repeat in range(3):
                options=classes.copy();random.Random(20261016+repeat).shuffle(options)
                text=r['input'][:3000]
                while len(tok.encode(tok.apply_chat_template([{'role':'user','content':render(text,question,options)}],tokenize=False,add_generation_prompt=True,enable_thinking=False),add_special_tokens=False))>2048:
                    text=text[:-300];assert len(text)>100
                q={'id':'family','type':'choice','question':question,'options':[{'name':n,'description':n.replace('_',' ')} for n in options]}
                for arm in ['decision','chat']:
                    request_id='acc-'+hashlib.sha256((r['source']+r['case']).encode()).hexdigest()[:12]+f'-{repeat}-{arm}'
                    if arm=='decision':
                        payload={'model':'AI4Loc-Qwen9B','input':text,'questions':[q],'temperature':1,'prompt_format_version':1,'return_prompt_token_ids':True};path='/v1/decisions'
                    else:
                        payload={'model':'AI4Loc-Qwen9B','messages':[{'role':'user','content':render(text,question,options)}],
                                 'temperature':0,'max_tokens':1,'stream':True,'stream_options':{'include_usage':True},'chat_template_kwargs':{'enable_thinking':False}};path='/v1/chat/completions'
                    start_wall=time.time_ns();start=time.monotonic_ns();events=[];first=None;response=None;usage={}
                    async with session.post('http://127.0.0.1:30003'+path,json=payload,headers={'X-Request-ID':request_id}) as resp:
                        assert resp.status==200,(resp.status,await resp.text())
                        if arm=='decision':
                            response=await resp.json();answer=response['answers']['family'];probs=answer['probabilities'];assert abs(sum(probs.values())-1)<1e-5
                            prediction=answer['choice'];usage=response.get('usage',{})
                        else:
                            content=''
                            async for line in resp.content:
                                line=line.decode().strip()
                                if not line.startswith('data: ') or line=='data: [DONE]':continue
                                obj=json.loads(line[6:]);now=time.monotonic_ns();events.append({'mono_ns':now,'data':obj})
                                if obj.get('usage'):usage=obj['usage']
                                for c in obj.get('choices',[]):
                                    v=c.get('delta',{}).get('content') or ''
                                    if v and first is None:first=now
                                    content+=v
                            letter=content.strip();prediction=options[ord(letter)-65] if len(letter)==1 and 'A'<=letter<=chr(64+len(options)) else None
                            response={'text':content};probs=None
                    end=time.monotonic_ns()
                    (E/'accuracy-raw'/f'{request_id}.json').write_text(json.dumps({'request':payload,'response':response,'events':events}))
                    record={'rid':request_id,'case':r['case'],'source':r['source'],'group':r['group'],'repeat':repeat,'api':arm,
                            'label':r['label'],'prediction':prediction,'correct':prediction==r['label'],'probabilities':probs,
                            'seconds':(end-start)/1e9,'chat_first_nonempty_seconds':(first-start)/1e9 if first else None,'usage':usage,
                            'start_wall_ns':start_wall,'end_wall_ns':time.time_ns(),'start_mono_ns':start,'end_mono_ns':end,
                            'input_sha256':hashlib.sha256(text.encode()).hexdigest(),'option_order':options}
                    with (E/'accuracy.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
            print('ACCURACY',r['source'],r['case'],flush=True)
if __name__=='__main__':asyncio.run(main())
