"""Official PPLX reference computation with bounded GPU placement for a shared A100.

CPU offload changes placement, not BF16 weights, question rendering or saved temperature.
This is a weight/accuracy test runtime, not a native-SGLang speed benchmark.
"""
import argparse,pathlib,sys,json,os,time,threading
p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=pathlib.Path,required=True);p.add_argument('--port',type=int,default=30002);p.add_argument('--gpu-weight-limit',default='10GiB');p.add_argument('--cpu-memory-limit',default='64GiB');p.add_argument('--record',type=pathlib.Path,required=True);a=p.parse_args()
verified=json.loads((a.checkpoint/'verified-checkpoint.json').read_text());assert verified['complete'] and verified['revision']=='b01a5cbaca5391f73bd55103d4f27e8982cd5e60'
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';sys.path.insert(0,str(a.checkpoint/'source/src'))
import torch
from safetensors.torch import load_file
from transformers import AutoProcessor
from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5Model
from autojev.model import DecisionModel,answer,MAX_OPTIONS
from fastapi import FastAPI,HTTPException
from fastapi.concurrency import run_in_threadpool
from contextlib import asynccontextmanager
torch.set_num_threads(8);torch.backends.cuda.enable_cudnn_sdp(False)
lock=threading.Lock();model=None
@asynccontextmanager
async def lifespan(app):
 global model
 start=time.monotonic();saved=json.loads((a.checkpoint/'decision_config.json').read_text());assert saved['format_version']==1
 # Bypass only the reference constructor's unconditional .to(cuda), retaining
 # its official prepare/forward implementations and the exact checkpoint readout.
 model=DecisionModel.__new__(DecisionModel);torch.nn.Module.__init__(model)
 model.device_name='cuda';model.base_model=saved['base_model'];model.revision=saved['revision'];model.codes=saved['codes'];model.token_ids=saved['token_ids'];model.temperature=saved['temperature']
 model.processor=AutoProcessor.from_pretrained(str(a.checkpoint),local_files_only=True);model.processor.tokenizer.padding_side='left';model.processor.image_processor.size={'shortest_edge':65536,'longest_edge':262144}
 assert len(model.codes)==len(model.token_ids)==255
 assert [model.processor.tokenizer.encode(c,add_special_tokens=False)[0] for c in model.codes]==model.token_ids
 assert all(len(model.processor.tokenizer.encode(c,add_special_tokens=False))==1 for c in model.codes)
 model.backbone=Qwen3_5Model.from_pretrained(str(a.checkpoint),local_files_only=True,dtype=torch.bfloat16,attn_implementation='sdpa',device_map='auto',max_memory={0:a.gpu_weight_limit,'cpu':a.cpu_memory_limit},low_cpu_mem_usage=True)
 model.readout=torch.nn.Linear(model.backbone.config.text_config.hidden_size,MAX_OPTIONS,bias=False,dtype=torch.bfloat16,device='cuda');model.readout.load_state_dict(load_file(str(a.checkpoint/'readout.safetensors')));model.requires_grad_(False);model.eval()
 a.record.write_text(json.dumps({'model':verified['model'],'revision':verified['revision'],'runtime':'official-reference/transformers-accelerate-cpu-offload','dtype':'bfloat16','temperature':model.temperature,'gpuWeightLimit':a.gpu_weight_limit,'cpuMemoryLimit':a.cpu_memory_limit,'deviceMap':model.backbone.hf_device_map,'loadSeconds':time.monotonic()-start,'nativeSglangSpeedComparable':False,'torch':torch.__version__},indent=2));print('MODEL_READY',flush=True)
 yield
 model=None
app=FastAPI(lifespan=lifespan)
@app.get('/health')
def health():return {'ready':model is not None,'model':verified['model'],'revision':verified['revision'],'cpuOffload':True}
def infer(body):
 questions=body['questions'];rows=[{'state':body['state'],'question':q} for q in questions.values()]
 with torch.inference_mode():
  batch=model.prepare(rows);distributions=(model(batch)/model.temperature).softmax(-1).cpu().tolist();answers={k:answer(q,v[:count]) for (k,q),v,count in zip(questions.items(),distributions,batch.counts)}
 return {'model':verified['model'],'answers':answers,'usage':{'input_tokens':batch.input_tokens,'output_tokens':0}}
@app.post('/v1/systemone')
async def systemone(body:dict):
 if set(body)-{'state','questions','model'} or 'state' not in body:raise HTTPException(422,'Expected state, questions and optional model')
 if body.get('model',verified['model']) not in [verified['model'],'jev-latest']:raise HTTPException(422,'This service has one fixed PPLX checkpoint')
 if not isinstance(body.get('questions'),dict) or not 1<=len(body['questions'])<=3:raise HTTPException(422,'One to three fixed typed questions required')
 for key,q in body['questions'].items():
  if not key or not isinstance(q,dict) or set(q)-{'type','instructions','criteria'}:raise HTTPException(422,'Invalid question fields')
  kind=q.get('type');criteria=q.get('criteria')
  if kind=='choice' and (not isinstance(criteria,dict) or not 1<=len(criteria)<=255):raise HTTPException(422,'Choice requires 1..255 criteria')
  if kind=='score' and (not isinstance(criteria,list) or not 2<=len(criteria)<=10):raise HTTPException(422,'Score requires 2..10 ordered criteria')
  if kind=='noul' and criteria is not None and (not isinstance(criteria,dict) or set(criteria)-{'true','false'}):raise HTTPException(422,'Noul criteria are true/false')
  if kind not in ['choice','score','noul']:raise HTTPException(422,'Unsupported question type')
 if not lock.acquire(blocking=False):raise HTTPException(529,'Model busy')
 try:return await run_in_threadpool(infer,body)
 except ValueError as e:raise HTTPException(422,str(e)) from e
 finally:lock.release()
if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,host='127.0.0.1',port=a.port,log_level='info')
