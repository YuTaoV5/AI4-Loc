import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {appendFile,realpath} from 'node:fs/promises';
import path from 'node:path';
export const name='kernel-decision';
export const inject=['tools'];
export function apply(ctx,config={}) {
  if(!config.python||!config.bridge||!config.workspace||!config.baseUrl)throw Error('kernel-decision requires trusted python/bridge/workspace/baseUrl');
  const mode=config.mode||'rank';if(!['rank','boundary'].includes(mode))throw Error('Unsupported decision tool mode');
  ctx.tools.register({name:mode==='boundary'?'kernel_boundary':'kernel_decide',description:'Inspect kernel evidence and use typed SGLang decisions to rank observed source candidates. Read-only; probabilities are not proof.',
    parameters:{type:'object',properties:{},additionalProperties:false},
    output:{schema:{type:'object',additionalProperties:true},render:(_args,value)=>[{type:'text',text:JSON.stringify(value)}]},
    async execute(args,exec){
      if(!args||Object.keys(args).length)throw Error('No arguments allowed; input comes from the trusted task workspace');
      const workspace=await realpath(config.workspace);
      const {stdout}=await promisify(execFile)(config.python,[config.bridge,'--workspace',workspace,'--base',config.baseUrl,'--mode',mode],{cwd:workspace,timeout:60000,maxBuffer:512*1024,signal:exec?.signal});
      const value=JSON.parse(stdout);
      await appendFile(path.join(workspace,'dsh-decision-events.jsonl'),JSON.stringify({type:'decision/tool-result',tool:mode==='boundary'?'kernel_boundary':'kernel_decide',pluginVersion:1,at:new Date().toISOString(),selected:value.selected})+'\n');
      return value;
    }});
}
