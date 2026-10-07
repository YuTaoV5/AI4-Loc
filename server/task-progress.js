const {EventEmitter}=require('events');
module.exports=({state,save})=>{
 const bus=new EventEmitter();bus.setMaxListeners(100);
 const names={queued:'等待执行',reading:'读取日志',extracting:'提取异常与调用链',matching:'匹配专家 Skill 与社区案例',source:'匹配对应内核源码',routing:'SGLang 多问题分诊',agent:'dsh 模型与工具分析',report:'生成定位报告',complete:'等待人工验证',failed:'执行失败'};
 const snapshot=j=>({id:j.id,status:j.status,progress:j.progress,stage:j.stage||'complete',stageName:names[j.stage]||'历史任务已完成',agent:j.agent||{name:'规则分析引擎',status:'completed',message:'历史任务未记录阶段事件'},timeline:j.timeline||[],kernelKey:j.kernelKey,sourceError:j.sourceError,reportReady:j.reportReady,error:j.error});
 const emit=j=>bus.emit(j.id,snapshot(j));
 const step=(j,stage,progress,message,status='running')=>{const now=new Date().toISOString();const previous=j.timeline?.at(-1);if(previous&&!previous.endedAt){previous.endedAt=now;previous.status=stage==='failed'?'failed':'completed';}j.timeline=j.timeline||[];j.timeline.push({stage,name:names[stage],startedAt:now,status,message});j.stage=stage;j.progress=progress;j.agent={name:j.agentName||'规则分析引擎',status:stage==='failed'?'failed':stage==='complete'?'completed':stage==='queued'?'queued':'running',message,updatedAt:now};save();emit(j);};
 const activity=(j,message,phase)=>{j.agent.message=String(message).slice(0,300);j.agent.updatedAt=new Date().toISOString();if(phase)j.agent.phase=String(phase).slice(0,40);j.agent.events=(j.agent.events||[]).concat({at:j.agent.updatedAt,message:j.agent.message}).slice(-30);save();emit(j);};
 const settle=j=>{save();emit(j);};
 const stream=(req,res,j)=>{res.setHeader('Content-Type','text/event-stream');res.setHeader('Cache-Control','no-cache');res.setHeader('Connection','keep-alive');res.flushHeaders();const send=s=>res.write(`event: progress\ndata: ${JSON.stringify(s)}\n\n`);send(snapshot(j));bus.on(j.id,send);const heartbeat=setInterval(()=>res.write(': heartbeat\n\n'),20000);req.on('close',()=>{clearInterval(heartbeat);bus.off(j.id,send);});};
 return {step,activity,settle,snapshot,stream};
};
