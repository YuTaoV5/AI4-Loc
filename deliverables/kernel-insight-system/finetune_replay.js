/* Offline teaching steps and measured observations. No model calls or external assets. */
window.FTReplay=(()=>{
const D=JSON.parse(document.getElementById('ft-data').textContent),blue='#0071E3',ink='#1D1D1F',muted='#6E6E73',gray='#AAB2BD';
const last=(a,t)=>a.filter(x=>x.t<=t).at(-1),fmt=(v,n=2)=>v==null?'未观测':Number(v).toFixed(n);
function activate(root){
 const canvas=root.querySelector('canvas'),g=canvas.getContext('2d'),kind=root.dataset.kind;
 let scene='trained-4x8-warm',t=0,raf=0,playing=false,stamp=0;
 const slider=root.querySelector('input'),play=root.querySelector('[data-ft=play]');
 const isReal=['runtime','memory','training'].includes(kind);
 const getScene=()=>D.scenes[scene];
 function arms(){if(kind==='memory')return [D.scenes['base-4x8-warm'].arms[0],D.scenes['trained-4x8-warm'].arms[0]];return getScene().arms;}
 function end(){return kind==='training'?D.complete.seconds:kind==='memory'?Math.max(...arms().map(a=>a.duration)):kind==='runtime'?getScene().end:5;}
 function text(s,x,y,size=26,color=ink,align='left'){g.font=`${size>=38?600:400} ${size}px "Microsoft YaHei",sans-serif`;g.fillStyle=color;g.textAlign=align;g.fillText(s,x,y);}
 function line(x,y,a,b,color=gray,w=2){g.beginPath();g.moveTo(x,y);g.lineTo(a,b);g.strokeStyle=color;g.lineWidth=w;g.stroke();}
 function box(x,y,w,h,label,active=false,sub=''){g.fillStyle=active?'#E8F3FF':'#F5F5F7';g.beginPath();g.roundRect(x,y,w,h,18);g.fill();if(active){g.strokeStyle=blue;g.lineWidth=2;g.stroke();}text(label,x+24,y+48,30,active?blue:ink);if(sub)text(sub,x+24,y+91,23,muted);}
 function arrow(x,y,to){line(x,y,to-12,y,blue,3);g.beginPath();g.moveTo(to-23,y-8);g.lineTo(to-12,y);g.lineTo(to-23,y+8);g.stroke();}
 function note(s){text(s,36,560,23,muted);}
 function bars(rows,max,{x=390,y=95,w=980,gap=95,labelWidth=350,unit='',digits=3}={}){
   rows.forEach((r,i)=>{const yy=y+i*gap;const visible=t>=Math.min(4,i+1);text(r[0],x-25,yy+27,27,ink,'right');g.fillStyle='#F0F2F5';g.fillRect(x,yy,w,40);if(visible){g.fillStyle=i%2?blue:gray;g.fillRect(x,yy,w*r[1]/max,40);text(fmt(r[1],digits)+unit,x+w+18,yy+29,27);}else text('待揭示',x+w+18,yy+29,24,muted);});
 }
 function drawMechanism(){const k=Math.floor(t+1e-8);
  if(kind==='model'){
   box(40,60,370,130,'冻结 Qwen3.5-9B',k>=0,'BF16 · 原有因果骨干');box(510,60,470,130,'冻结 W · 原LM字母读出',k>=1,'保持原架构与选项token');arrow(410,125,510);
   box(510,270,470,140,'可训练 A → B · rank 8',k>=2,'48处投影 · FP32梯度与优化器');line(745,190,745,265,blue,3);box(1080,160,470,160,'W有效 = W + 2BA',k>=4,'5,308,416 参数 · 约0.056%');arrow(980,125,1080);arrow(980,340,1080);
   text(k>=3?'A随机初始化，B=0 → 初始增量为0':'仅更新低秩支路；骨干不回传参数更新',48,467,32,k>=3?blue:muted);note('机制示意：非随机预训练9B；没有新增随机决策头；未移植Laya的双向编码器。');
  }else if(kind==='data'){
   box(35,65,480,125,'真实日志 → 脱敏诊断窗口',true,'去注入命令 / 来源路径 / 标签元数据');box(610,65,420,125,'按注入机制跨内核分组',k>=1,'测试20个机制簇 · 不是87独立机制');arrow(515,128,610);
   ['训练 33','开发 4','测试 87'].forEach((s,i)=>{box(55+i*520,265,460,135,s,k>=i+2,['监督分类 + 选项排列','选择epoch与温度','冻结推理后再评分'][i]);});
   text('输入哈希无重叠；历史测试组不进训练',45,466,33,blue);note('历史测试已为开发者所见；弱首诊断标签；OOM与watchdog测试支持为0。');
  }else if(kind==='objective'){
   const labels=['提取字母logits','采4组高斯扰动','计算真类奖励','标准化优势','CE + 策略梯度'];
   labels.forEach((s,i)=>{box(30+i*315,74,290,130,s,k>=i,['现有LM读出','σ = 0.4 → 0.15','log + spherical','中心化 / 标准化','梯度累积4微步'][i]);if(i<4)arrow(320+i*315,140,345+i*315);});
   text('epoch 0：交叉熵 CE',55,320,37,k>=0?blue:muted);text('epoch 1–2：CE + Laya式RLCD',55,385,37,k>=3?blue:muted);text('R = max(log q正确, −9.21) + 0.75 · q正确 / ‖q‖₂',55,475,33);
   note('机制示意；未保存逐次梯度动画。无等预算CE-only消融，不能把全部增益归因于RLCD。');
  }else if(kind==='inference'){
   box(35,70,430,130,'选中epoch 1 → 合并BF16',k>=0,'开发仅4例 · 温度T=0.5');box(560,70,430,130,'SGLang同一因果骨干',k>=1,'取字母候选logits');arrow(465,135,560);
   box(1090,50,470,150,'Decision → 概率向量',k>=2,'0生成token · 完整概率可用');box(1090,300,470,150,'Chat → 首个内容字母',k>=3,'关闭thinking · 最多1 token');arrow(990,135,1090);line(1005,135,1005,375,blue,3);arrow(1005,375,1090);
   text('8个不同选项集合 = 8次独立渲染与评分',45,335,32,blue);text('不是一次prefill复用完整隐状态',45,400,29,muted);note('流程示意；适配器与合并权重开发top1相同，但最大logit漂移3.308，不保证逐位等价。');
  }else{
   ['分类：66/87 → 78/87','八步预热：接口约快7.7%','KV / 状态：没有节省','完整定位：仍为2/3','下一步：盲测 + CE消融 + 因果真值'].forEach((s,i)=>{text((k>=i?'●  ':'○  ')+s,90,85+i*87,36,k>=i?blue:muted);});
   note('完整报告、逐请求/训练数据、源hash与限制：research/jev-qwen35-9b-20261016。');
  }
 }
 function drawTraining(){
  const rows=D.training.filter(x=>x.elapsed<=t),cur=rows.at(-1),x0=105,y0=90,w=1370,h=260;
  const vals=D.training.map(x=>x.loss),lo=Math.min(0,...vals),hi=Math.max(...vals),xx=s=>x0+s/end()*w,yy=v=>y0+h-(v-lo)/(hi-lo||1)*h;
  const boundaries=[0,...[0,1,2].map(e=>D.training.filter(x=>x.epoch===e).at(-1).elapsed)];
  [0,1,2].forEach(e=>{g.fillStyle=e===1?'#EDF5FF':'#F5F5F7';g.fillRect(xx(boundaries[e]),y0,xx(boundaries[e+1])-xx(boundaries[e]),h);text(e===0?'epoch0 · CE':`epoch${e} · CE+RLCD`,xx(boundaries[e])+10,y0-22,24,e===1?blue:muted);});
  for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;line(x0,yy(v),x0+w,yy(v),'#DFE3E9',1);text(fmt(v,1),x0-15,yy(v)+8,21,muted,'right');}
  g.beginPath();rows.forEach((r,i)=>i?g.lineTo(xx(r.elapsed),yy(r.loss)):g.moveTo(xx(r.elapsed),yy(r.loss)));g.strokeStyle=blue;g.lineWidth=2;g.stroke();
  line(xx(t),y0,xx(t),y0+h,ink,2);[0,60,120,180,240,300,end()].forEach(v=>text(fmt(v,0)+'s',xx(v),390,21,muted,'center'));
  text(cur?`微步 ${cur.step}/396  ·  完成更新 ${Math.floor(cur.step/4)}/99  ·  loss ${fmt(cur.loss,4)}`:'等待首个微步记录（首步包含编译）',80,458,31,blue);
  text(cur?`当前torch allocated ${fmt(cur.allocated_bytes/2**30)} GiB  ·  输入 ${cur.tokens} tokens`:'训练日志首条 elapsed = 57.132s',80,509,27,muted);
  note(t>=D.training.at(-1).elapsed?'最后微步290.764s；到开发评估/导出/哈希结束343.689s。选中epoch1，不是最后一轮。':'真实离散loss点；epoch0与后续目标不同，不将跨阶段曲线当统一收敛指标。');
 }
 function drawAccuracy(){
  const n=Math.floor(t/5*87),cs=D.cases,base=cs.filter(c=>c.before).length,after=cs.filter(c=>c.after).length;
  ['基座','微调后'].forEach((s,a)=>{text(s,40,60+a*150,31);for(let i=0;i<87;i++){const c=cs[i],on=i<n,val=a?c.after:c.before;g.fillStyle=!on?'#E8EBEF':val?blue:'#515D6C';g.fillRect(200+(i%29)*45,25+a*150+Math.floor(i/29)*33,34,24);}text(`${cs.slice(0,n).filter(c=>a?c.after:c.before).length}/${n}`,1530,80+a*150,32,blue,'right');});
  text('蓝 = 命中；深灰 = 未命中；教学顺序揭示配对案例',200,336,25,muted);
  text(`最终 ${base}/87（75.86%）→ ${after}/87（89.66%）`,60,410,40,blue);
  text('警告 8/20→19/20   ·   RCU 1/7→2/7   ·   阻塞 2/2→1/2',60,478,30);
  note('排列多数票；Decision/Chat分类相同。机制簇bootstrap区间触及/跨越0；不是独立盲测或根因真值。');
 }
 function drawCalibration(){
   const rows=D.calibration;const sets=[['NLL ↓','case_nll',2.1],['Brier ↓','case_brier',.31],['ECE10 ↓','ece10',.14]];
   sets.forEach(([title,key,max],j)=>{const x=65+j*520;text(title,x,65,33);rows.forEach((r,i)=>{const y=128+i*105;const show=t>=i+1;text(['基座 T=1','微调 T=1','微调 T=0.5'][i],x,y-15,25,muted);g.fillStyle='#EEF0F3';g.fillRect(x,y,410,37);if(show){g.fillStyle=i?blue:gray;g.fillRect(x,y,410*r[key]/max,37);text(fmt(r[key],3),x+420,y+28,25);}});});
   text('准确率上升 ≠ 概率可靠；NLL暴露错误的过度自信',65,489,36,blue);note('三个排列概率均值的实际统计量；开发集只有4例，T=0.5选择不稳定。条形逐列揭示不是时间测量。');
 }
 function drawRuntime(){
   const aa=arms(),limit=end(),scale=600/limit;
   aa.forEach((a,i)=>{const x=40+i*795,color=i?gray:blue,label=kind==='memory'?(i?'微调后 Decision':'基座 Decision'):(i?'Chat · 首内容token':'Decision · 完整概率');
    text(label,x,40,31,color);text(`实测 ${fmt(a.duration,3)}s  ·  5次均值 ${fmt(a.mean,3)}s`,x,79,23,muted);
    const obs=last(a.samples,Math.min(t,a.duration)),gpu=last(a.gpu,Math.min(t,a.duration)),pref=a.prefills.filter(p=>p.t<=t);
    text(`KV ${fmt(obs?.kv,1)} MiB · 状态 ${obs?.states??'未知'} · 排队 ${obs?.queued??'未知'}`,x,125,26);
    text(`显存 ${fmt(gpu?.mib?gpu.mib/1024:null)} GiB · 功耗 ${fmt(gpu?.power,0)} W`,x,164,25,muted);
    // Zero-order scheduler staircase on a zero-baseline common 520 MiB scale.
    const left=x+65,top=205,height=125;line(left,top+height,left+600,top+height,'#CBD1D9');
    text('520',left-12,top+10,19,muted,'right');text('0',left-12,top+height,19,muted,'right');
    const ss=a.samples.filter(s=>s.t<=t);if(ss.length){g.beginPath();ss.forEach((s,j)=>{const px=left+s.t*scale,py=top+height-s.kv/520*height;if(!j)g.moveTo(px,py);else{g.lineTo(px,top+height-ss[j-1].kv/520*height);g.lineTo(px,py);}});const z=ss.at(-1);g.lineTo(left+Math.min(t,a.duration)*scale,top+height-z.kv/520*height);g.strokeStyle=color;g.lineWidth=3;g.stroke();}
    a.calls.forEach(c=>{if(c.start>t)return;const yy=365+c.task*27;g.fillStyle=color;g.fillRect(left+c.start*scale,yy,Math.max(1,(Math.min(c.end,t)-c.start)*scale),12);if(c.ready<=t){g.fillStyle=ink;g.beginPath();g.arc(left+c.ready*scale,yy+6,3,0,7);g.fill();}});
    line(left+Math.min(t,limit)*scale,top-10,left+Math.min(t,limit)*scale,472,ink,1);
    text(`${fmt(0,1)}s`,left,495,20,muted);text(`${fmt(limit,3)}s`,left+600,495,20,muted,'right');
    text(`prefill结算：新算 ${pref.reduce((s,p)=>s+p.new,0)} / 缓存 ${pref.reduce((s,p)=>s+p.cached,0)}`,x,532,23,color);
   });
   note(kind==='memory'?'相同9B架构与静态池；不同实验时段。KV token=32KiB，线性状态另计；NVML约100ms采样。':'独立trial对齐起点；黑点为用户结果可用。KV/状态为离散观测；token只在原生prefill完成时结算。');
 }
 function drawHeatmap(){
  const keys=['1×1冷','1×1热','1×8冷','1×8热','4×1冷','4×1热','4×8冷','4×8热'];
  text('Decision相对Chat整批耗时减少（%）；负值表示更慢',50,50,30);
  keys.forEach((s,i)=>text(s,320+i*155,110,24,muted,'center'));
  ['base','trained'].forEach((cp,j)=>{text(j?'微调后':'基座',45,205+j*155,31);let i=0;for(const c of [1,4])for(const d of [1,8])for(const cache of ['cold','warm']){const a=D.scenes[`${cp}-${c}x${d}-${cache}`].arms,v=100*(a[1].mean-a[0].mean)/a[1].mean,on=t>=(j?3:1);const x=250+i*155,y=150+j*155;g.fillStyle=on?(v>=0?`rgba(0,113,227,${.12+Math.min(.7,v/40)})`:'#D8DDE4'):'#F0F2F5';g.fillRect(x,y,140,100);text(on?`${v>=0?'+':''}${fmt(v,1)}%`:'待揭示',x+70,y+61,28,on?ink:muted,'center');i++;}});
  text('所有条件每接口5次重复 · 共两个检查点224组trial',55,505,31,blue);note('同一A100 80GB / SGLang0.5.21 / ctx8192 / 静态比例0.55 / 32状态槽；不是27B与9B横比。');
 }
 function drawAgent(){
  const a=D.agent,rows=a.map(r=>[(r.checkpoint==='base'?'基座':'微调后')+' · '+(r.variant==='chat-only'?'纯Chat':'Decision+Chat'),Number(r.total_localization_seconds)]);
  bars(rows,60,{x:475,y:65,w:680,gap:100,unit:'s'});
  a.forEach((r,i)=>{if(t>=Math.min(4,i+1))text(`${r.model_http_calls} HTTP · ${r.code_location_hits}/${r.cases}命中`,1400,92+i*100,24,muted,'center');});
  text('混合流程调用变少，但仍慢于纯Chat；代码位置命中均未提升',50,506,32,blue);note('ctx32768独立Agent实验；3例串行耗时之和。柱子揭示为教学动画，不是逐请求时序。');
 }
 function draw(){
  g.fillStyle='white';g.fillRect(0,0,1600,590);
  ({training:drawTraining,accuracy:drawAccuracy,calibration:drawCalibration,runtime:drawRuntime,memory:drawRuntime,heatmap:drawHeatmap,agent:drawAgent}[kind]||drawMechanism)();
  root.dataset.time=t;root.dataset.playing=playing;slider.value=t/end();root.querySelector('.ft-clock').textContent=isReal?`t ${fmt(t,3)} / ${fmt(end(),3)} s`:`教学步 ${Math.floor(t)+1} / 6`;
  root.querySelector('.ft-caption').textContent=kind==='runtime'?`${getScene().title} · 单次repeat ${getScene().repeat}（0起算） · 5次均值另列；非平均轨迹。`:kind==='memory'?'比较独立试验中的真实Decision轨迹；不能归因细小抖动为LoRA的计算架构变化。':kind==='training'?'日志时钟可拖动：真实训练记录；第一步含编译，最后微步之后为开发评估与导出。':'机制 / 统计展示按教学步播放；不声称测得逐算子、逐梯度时间。';
 }
 function stop(){playing=false;cancelAnimationFrame(raf);play.textContent='播放演示';root.dataset.playing='false';}
 function setTime(v){stop();t=Math.max(0,Math.min(end(),v));draw();}
 function points(){if(kind==='runtime')return getScene().points;if(kind==='memory')return [...new Set([0,end(),...arms().flatMap(a=>a.calls.map(c=>c.ready))])].sort((a,b)=>a-b);if(kind==='training')return [0,...D.training.map(x=>x.elapsed),end()];return [0,1,2,3,4,5];}
 function next(){setTime(points().find(v=>v>t+1e-6)??end());}
 function prev(){setTime(points().filter(v=>v<t-1e-6).at(-1)??0);}
 function toggle(){if(playing){stop();return;}if(t>=end())t=0;playing=true;stamp=performance.now();play.textContent='暂停演示';root.dataset.playing='true';function tick(now){const dt=(now-stamp)/1000;stamp=now;t=Math.min(end(),t+dt*(kind==='training'?end()/12:isReal?1:.6));draw();if(t>=end())stop();else raf=requestAnimationFrame(tick);}raf=requestAnimationFrame(tick);}
 root.querySelectorAll('[data-ft]').forEach(b=>b.onclick=e=>{e.stopPropagation();({prev,next,play:toggle,reset:()=>setTime(0),end:()=>setTime(end())}[b.dataset.ft])();});
 slider.oninput=()=>setTime(Number(slider.value)*end());const select=root.querySelector('select');if(select)select.onchange=()=>{scene=select.value;setTime(0);};
 root._ft={setTime,end,next,prev,toggle,stop};draw();return root._ft;
}
return {activate};
})();
