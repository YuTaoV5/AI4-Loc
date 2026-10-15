"""Rebuild the learned checkpoint from a pinned base + privately retained adapter.

Not a training run. Requires sufficient GPU memory and a maintenance window.
The original merged checkpoint's manifest remains the authoritative fingerprint.
"""
import argparse,pathlib,shutil,json,hashlib
import torch
from transformers import Qwen3_5ForConditionalGeneration,AutoTokenizer
from train import LoRA
def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=pathlib.Path,required=True);p.add_argument('--adapter',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    assert not a.output.exists(),'Never overwrite a checkpoint'
    state=torch.load(a.adapter,map_location='cpu',weights_only=True)
    m=Qwen3_5ForConditionalGeneration.from_pretrained(a.base,dtype=torch.bfloat16,local_files_only=True,attn_implementation='sdpa').to('cuda')
    m.requires_grad_(False)
    for name,v in state.items():
        base=m.model.language_model.get_submodule(name);w=LoRA(base);w.a.data.copy_(v['a']);w.b.data.copy_(v['b']);w.merged()
    a.output.mkdir();m.save_pretrained(a.output,max_shard_size='5GB');AutoTokenizer.from_pretrained(a.base,local_files_only=True).save_pretrained(a.output)
    for name in ['chat_template.jinja','preprocessor_config.json','video_preprocessor_config.json','LICENSE']:
        if (a.base/name).exists():shutil.copy2(a.base/name,a.output/name)
    (a.output/'adapter-reconstruction.json').write_text(json.dumps({'base':str(a.base),'adapter_sha256':hashlib.sha256(a.adapter.read_bytes()).hexdigest(),'note':'Numerical/kernel/library variations can change merged bytes. Verify against original trained-checkpoint-manifest.json before claiming bitwise equivalence.'},indent=2))
if __name__=='__main__':main()
