const crypto=require('crypto');
const RECIPES=[
 {id:'decision-chat',name:'快速定界 + 深入定位',description:'Decision 输出阶段与故障类型，Chat 调用只读工具追查根因代码。',instruction:'Use finite Decision boundary hints critically, then inspect evidence and owning source with tools before reporting causal candidates.'},
 {id:'chat-investigator',name:'Chat 证据调查',description:'由 Chat 完成定界、源码调查与结构化报告。',instruction:'Classify the first diagnostic and lifecycle stage from evidence. Inspect owning source with tools, distinguish detector from faulty owner.'}
];
const hash=value=>crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
module.exports=function(app,{state,save}){
 state.agentProfiles ||= [];
 function compose(body,ownerId,previous){
  if(typeof body.name!=='string'||!body.name.trim()||body.name.length>80)throw Error('组合名称须为 1–80 字');
  const recipe=RECIPES.find(x=>x.id===body.agentId);if(!recipe)throw Error('请选择支持的 Agent');
  if(!Array.isArray(body.skillIds)||body.skillIds.length>12||body.skillIds.some(x=>typeof x!=='string'))throw Error('最多选择 12 个 Skill');
  const skills=[...new Set(body.skillIds)].map(id=>{const s=state.skills.find(s=>s.id===id&&s.status==='active');if(!s)throw Error('Skill 不存在或未启用');return {id:s.id,name:s.name,version:s.version,category:s.category,patterns:[...(s.patterns||[])],guidance:String(s.guidance||'').slice(0,2000),contributor:s.contributor};});
  if(body.extraPrompt!=null&&typeof body.extraPrompt!=='string')throw Error('补充 Prompt 必须为文本');
  const extraPrompt=(body.extraPrompt||'').trim();if(extraPrompt.length>4000)throw Error('补充 Prompt 最多 4000 字');
  const prompt=[recipe.instruction,...skills.map(s=>`Skill ${s.name} v${s.version}: ${s.guidance}`),extraPrompt].filter(Boolean).join('\n\n');
  const snapshot={agentId:recipe.id,skills,extraPrompt,prompt};
  return {...snapshot,id:previous?.id||crypto.randomUUID(),ownerId,name:body.name.trim(),revision:(previous?.revision||0)+1,hash:hash(snapshot),isDefault:body.isDefault===true,createdAt:previous?.createdAt||new Date().toISOString(),updatedAt:new Date().toISOString()};
 }
 function select(req){
  const id=req.body.agentProfileId;if(!id)return null;
  const p=state.agentProfiles.find(p=>p.id===id&&p.ownerId===req.user.id);if(!p)throw Error('个人 Prompt 不存在或无权使用');
  return structuredClone(p);
 }
 app.get('/api/agent-presets',(_,res)=>res.json({agents:RECIPES.map(({instruction,...r})=>r),maxSkills:12,maxExtraPrompt:4000}));
 app.get('/api/me/agent-profiles',(req,res)=>res.json(state.agentProfiles.filter(p=>p.ownerId===req.user.id)));
 app.post('/api/agent-profiles/preview',(req,res)=>{const p=compose(req.body,req.user.id);res.json({prompt:p.prompt,hash:p.hash});});
 app.post('/api/me/agent-profiles',(req,res)=>{
  if(state.agentProfiles.filter(p=>p.ownerId===req.user.id).length>=30)return res.status(409).json({error:'最多保存 30 个组合'});
  const p=compose(req.body,req.user.id);if(p.isDefault)for(const x of state.agentProfiles.filter(x=>x.ownerId===req.user.id))x.isDefault=false;
  state.agentProfiles.push(p);save();res.status(201).json(p);
 });
 app.put('/api/me/agent-profiles/:id',(req,res)=>{const i=state.agentProfiles.findIndex(p=>p.id===req.params.id&&p.ownerId===req.user.id);if(i<0)return res.status(404).json({error:'组合不存在'});const p=compose(req.body,req.user.id,state.agentProfiles[i]);if(p.isDefault)for(const x of state.agentProfiles.filter(x=>x.ownerId===req.user.id))x.isDefault=false;state.agentProfiles[i]=p;save();res.json(p);});
 app.delete('/api/me/agent-profiles/:id',(req,res)=>{const i=state.agentProfiles.findIndex(p=>p.id===req.params.id&&p.ownerId===req.user.id);if(i<0)return res.status(404).json({error:'组合不存在'});state.agentProfiles.splice(i,1);save();res.json({ok:true});});
 return {select};
};
module.exports.RECIPES=RECIPES;
