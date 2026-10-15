"""Qwen text-backbone LoRA decision training; no random 9B pretraining.

Inspired by Laya RLCD: zero-output categorical decisions, proper-score rewards,
Gaussian-logit policy-gradient regularization + cross entropy. Stock Laya's
bidirectional BERT head/masks are NOT used on Qwen's causal hybrid backbone.
LoRA is merged for the SAME SGLang runtime as the untrained baseline.
"""
import os,json,pathlib,random,hashlib,time,math,shutil
os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
import torch
import torch.nn.functional as F
from torch import nn
from transformers import AutoTokenizer,Qwen3_5ForConditionalGeneration
E=pathlib.Path(__file__).resolve().parent
BASE=pathlib.Path('/root/gpufree-data/systemone/models/Qwen3.5-9B')
OUT=pathlib.Path('/root/gpufree-data/systemone/models/AI4Loc-Jev-Qwen3.5-9B')
SEED=20261016
torch.manual_seed(SEED);random.seed(SEED);torch.set_num_threads(8)
class LoRA(nn.Module):
    def __init__(self,base,rank=8):
        super().__init__();self.base=base;self.scale=2.0
        self.a=nn.Parameter(torch.empty(rank,base.in_features,device=base.weight.device,dtype=torch.float32))
        self.b=nn.Parameter(torch.zeros(base.out_features,rank,device=base.weight.device,dtype=torch.float32))
        nn.init.kaiming_uniform_(self.a,a=math.sqrt(5))
    def forward(self,x):
        return self.base(x)+(F.linear(F.linear(x.float(),self.a),self.b)*self.scale).to(x.dtype)
    def merged(self):
        with torch.no_grad():self.base.weight.add_((self.b@self.a*self.scale).to(self.base.weight.dtype))
        return self.base
def render(text,question,options):
    return text+'\n\nQuestion: '+question+'\n'+'\n'.join(chr(65+i)+': '+n+' - '+n.replace('_',' ') for i,n in enumerate(options))+'\nAnswer with the letter of one option only.'
def rlcd(logits,target,sigma):
    """Laya-style Gaussian-logit policy gradient using log+spherical rewards."""
    eps=torch.randn((4,)+logits.shape,device=logits.device)*sigma
    eps=eps-eps.mean(-1,keepdim=True)
    z=logits.detach().unsqueeze(0)+eps
    q=z.softmax(-1)
    with torch.no_grad():
        reward=q[...,target].clamp_min(1e-12).log().clamp_min(-9.21)+.75*q[...,target]/q.norm(dim=-1).clamp_min(1e-9)
        adv=reward-reward.mean(0,keepdim=True);adv=adv/(adv.std()+1e-6)
    logdensity=-(z-logits.unsqueeze(0)).square().sum(-1)/(2*sigma*sigma)
    return -(adv*logdensity).mean()+F.cross_entropy(logits,torch.tensor([target],device=logits.device))
def main():
    assert not (E/'training-complete.json').exists()
    records=json.loads((E/'dataset.private.json').read_text());frozen=json.loads((E/'dataset-frozen.json').read_text())
    assert hashlib.sha256((E/'dataset.private.json').read_bytes()).hexdigest()==frozen['private_sha256']
    tokenizer=AutoTokenizer.from_pretrained(BASE,local_files_only=True)
    classes=frozen['classes'];question=frozen['question'];labels=[tokenizer.encode(chr(65+i),add_special_tokens=False) for i in range(len(classes))]
    assert all(len(x)==1 for x in labels);ids=torch.tensor([x[0] for x in labels],device='cuda')
    protocol={'seed':SEED,'base_revision':json.loads((E/'official-model-metadata.json').read_text())['sha'],
      'adaptation':'new zero-initialized rank8 LoRA; pretrained alphabet readout retained; merged into base weights for identical SGLang serving',
      'targets':'all text layers down_proj, full-attention q_proj and v_proj','rank':8,'alpha':16,
      'max_tokens':2048,'max_state_characters':3000,'epochs':3,'permutations_per_case_per_epoch':4,
      'gradient_accumulation':4,'optimizer':'AdamW','learning_rate':0.0001,'weight_decay':0.01,'clip_norm':1,
      'loss':'epoch0 CE, epochs1-2 CE + Laya-style RLCD PG(log+spherical proper reward); noise .4 to .15',
      'checkpoint_selection':'lowest dev NLL at epoch boundary; test never selects epoch/temperature',
      'calibration':'temperature fitted on dev NLL, fixed grid .5..3.0; held-out test evaluated after selection',
      'dataset_sha256':hashlib.sha256((E/'dataset-frozen.json').read_bytes()).hexdigest(),
      'train_case_count':sum(r['split']=='train' for r in records)}
    (E/'training-protocol.json').write_text(json.dumps(protocol,indent=2))
    model=Qwen3_5ForConditionalGeneration.from_pretrained(BASE,dtype=torch.bfloat16,attn_implementation='sdpa',local_files_only=True).to('cuda')
    model.requires_grad_(False);pairs=[]
    for name,layer in list(model.model.language_model.named_modules()):
        if isinstance(layer,nn.Linear) and name.split('.')[-1] in ['down_proj','q_proj','v_proj']:
            parent,key=name.rsplit('.',1);holder=model.model.language_model.get_submodule(parent)
            wrapped=LoRA(layer);setattr(holder,key,wrapped);pairs.append((holder,key,wrapped,name))
    assert len(pairs)==48,len(pairs)
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
    params=[p for p in model.parameters() if p.requires_grad]
    optim=torch.optim.AdamW(params,lr=1e-4,weight_decay=.01)
    info={'trainable_parameters':sum(p.numel() for p in params),'total_parameters':sum(p.numel() for p in model.parameters()),
          'torch':torch.__version__,'device':torch.cuda.get_device_name(),'dtype':'bfloat16 backbone / float32 adapter and optimizer',
          'targets':[n for *_,n in pairs]}
    (E/'training-environment.json').write_text(json.dumps(info,indent=2));print('TRAIN_READY',info['trainable_parameters'],flush=True)
    def encode(r,options):
        text=r['input'][:3000]
        while True:
            prompt=tokenizer.apply_chat_template([{'role':'user','content':render(text,question,options)}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
            toks=tokenizer.encode(prompt,add_special_tokens=False)
            if len(toks)<=2048:break
            text=text[:max(100,len(text)-300)]
            assert len(text)>100,'Question exceeds context'
        return torch.tensor([toks],device='cuda')
    def forward(r,options):
        x=encode(r,options)
        h=model.model.language_model(input_ids=x,attention_mask=torch.ones_like(x),use_cache=False).last_hidden_state[:,-1,:]
        return F.linear(h.float(),model.lm_head.weight[ids[:len(options)]].float()),len(x[0])
    def evaluate(split,tag):
        model.eval();out=[]
        with torch.no_grad():
            for r in records:
                if r['split']!=split:continue
                # Canonical fixed options; no labels used to construct the input.
                logits,n=forward(r,classes);logits=logits[0].float().cpu().tolist()
                out.append({'case':r['case'],'source':r['source'],'group':r['group'],'split':split,'label':r['label'],'logits':logits,'input_tokens':n})
        (E/f'{tag}-{split}.json').write_text(json.dumps(out,indent=2))
        nll=sum(float(F.cross_entropy(torch.tensor([r['logits']]),torch.tensor([classes.index(r['label'])]))) for r in out)/len(out)
        return nll
    # Baseline is recorded before any update. It is never used to tune training.
    evaluate('dev','untrained');evaluate('test','untrained')
    best=float('inf');best_epoch=None;step=0;started=time.monotonic();optim.zero_grad(set_to_none=True)
    train=[r for r in records if r['split']=='train'];assert len(train)>=5
    for epoch in range(3):
        model.train();schedule=[r for r in train for _ in range(4)];random.shuffle(schedule)
        for i,r in enumerate(schedule):
            options=classes.copy();random.shuffle(options)
            # Variable option sets always contain the gold in training only.
            k=random.choice([5,8,12]);options=[r['label']]+[x for x in options if x!=r['label']][:k-1];random.shuffle(options)
            t=time.monotonic();logits,n=forward(r,options);target=options.index(r['label'])
            loss=F.cross_entropy(logits,torch.tensor([target],device='cuda')) if epoch==0 else rlcd(logits,target,.4-(epoch-1)*.25)
            assert torch.isfinite(loss),'Nonfinite training loss'
            # Last partial accumulation is normalized by its actual group size.
            size=min(4,len(schedule)-(i//4)*4);(loss/size).backward()
            if (i+1)%4==0 or i+1==len(schedule):
                torch.nn.utils.clip_grad_norm_(params,1);optim.step();optim.zero_grad(set_to_none=True)
            torch.cuda.synchronize();step+=1
            row={'step':step,'epoch':epoch,'case':r['case'],'source':r['source'],'loss':loss.item(),'tokens':n,
                 'options':len(options),'seconds':time.monotonic()-t,'elapsed':time.monotonic()-started,
                 'allocated_bytes':torch.cuda.memory_allocated(),'reserved_bytes':torch.cuda.memory_reserved()}
            with (E/'training-steps.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            if step%4==0:print(json.dumps(row),flush=True)
        nll=evaluate('dev',f'epoch{epoch}')
        print('DEV',epoch,nll,flush=True)
        state={n:{'a':w.a.detach().cpu().clone(),'b':w.b.detach().cpu().clone()} for _,_,w,n in pairs}
        torch.save(state,E/f'adapter-epoch{epoch}.pt')
        if nll<best:best=nll;best_epoch=epoch
    selected=torch.load(E/f'adapter-epoch{best_epoch}.pt',weights_only=True)
    for _,_,w,n in pairs:
        w.a.data.copy_(selected[n]['a']);w.b.data.copy_(selected[n]['b'])
    evaluate('dev','selected');evaluate('test','selected')
    dev=json.loads((E/'selected-dev.json').read_text())
    def score(temp):return sum(float(F.cross_entropy(torch.tensor([r['logits']])/temp,torch.tensor([classes.index(r['label'])]))) for r in dev)/len(dev)
    temperature=min([.5+i*.05 for i in range(51)],key=score)
    # Adapter export does NOT fold temperature into all alphabet rows. Serving
    # passes this scalar to native Decision, preserving comparable Chat logits.
    before=json.loads((E/'selected-dev.json').read_text())
    for holder,key,w,n in pairs:setattr(holder,key,w.merged())
    evaluate('dev','merged')
    after=json.loads((E/'merged-dev.json').read_text())
    drift=[{'case':a['case'],'source':a['source'],
            'max_absolute_logit_difference':max(abs(x-y) for x,y in zip(a['logits'],b['logits'])),
            'top1_equal':max(range(len(classes)),key=lambda i:a['logits'][i])==max(range(len(classes)),key=lambda i:b['logits'][i])}
           for a,b in zip(before,after)]
    (E/'merge-validation.json').write_text(json.dumps(drift,indent=2))
    assert shutil.disk_usage(OUT.parent).free>21*1024**3,'Insufficient export space'
    OUT.mkdir(exist_ok=False)
    model.save_pretrained(OUT,max_shard_size='5GB');tokenizer.save_pretrained(OUT)
    for name in ['chat_template.jinja','preprocessor_config.json','video_preprocessor_config.json','LICENSE']:
        if (BASE/name).exists():shutil.copy2(BASE/name,OUT/name)
    hashes={}
    for p in sorted(OUT.iterdir()):
        if not p.is_file():continue
        h=hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(16*1024*1024),b''):h.update(block)
        hashes[p.name]={'bytes':p.stat().st_size,'sha256':h.hexdigest()}
    (E/'trained-checkpoint-manifest.json').write_text(json.dumps({'files':hashes,'base_revision':protocol['base_revision'],'adapter_epoch':best_epoch},indent=2))
    result={'status':'completed','steps':step,'best_epoch':best_epoch,'dev_nll':best,'temperature':temperature,
            'seconds':time.monotonic()-started,'model_path':str(OUT),'trainable_parameters':info['trainable_parameters'],
            'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'production_service_restored_by_controller':False}
    (E/'training-complete.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':main()
