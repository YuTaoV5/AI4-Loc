// Measured replay only: zero-order hold of observations; no token interpolation.
window.KVReplay = (() => {
  const data=JSON.parse(document.getElementById('kv-replay-data').textContent);
  const blue='#0071E3', ink='#1D1D1F', gray='#777780', light='#E5E5EA';
  const latest=(xs,t)=>{let last=null;for(const x of xs){if(x.t<=t)last=x;else break;}return last;};
  const font=(c,n,b=false)=>c.font=`${b?600:400} ${n}px "Microsoft YaHei","PingFang SC",sans-serif`;
  function text(c,x,y,value,size=20,color=ink,bold=false){font(c,size,bold);c.fillStyle=color;c.fillText(value,x,y);}
  function draw(canvas,scene,t){
    const c=canvas.getContext('2d');c.clearRect(0,0,1600,550);c.fillStyle='white';c.fillRect(0,0,1600,550);
    const end=scene.end, kvMax=Math.max(200,Math.ceil(Math.max(...scene.arms.map(a=>a.peak_kv))/200)*200);
    const tokenMax=Math.max(...scene.arms.flatMap(a=>[a.new_tokens,a.cached_tokens]));
    scene.arms.forEach((a,index)=>{
      const left=index*815, color=index===0?blue:gray, x=left+64, w=690;
      const sample=latest(a.samples,t),g=latest(a.gpu,t);
      const ready=a.calls.filter(r=>r.ready<=t).reduce((s,r)=>s+r.questions,0);
      const output=a.calls.filter(r=>r.ready<=t).reduce((s,r)=>s+r.output_tokens,0);
      const computed=a.prefills.filter(r=>r.t<=t);
      const uncached=computed.reduce((s,r)=>s+r.new,0), cached=computed.reduce((s,r)=>s+r.cached,0);
      text(c,left+16,30,a.label,27,color,true);
      text(c,left+16,62,`5次均值 ${a.mean_duration.toFixed(3)}s  ·  本次 #${a.trial} / repeat ${a.repeat}`,18,gray);
      text(c,left+16,96,`结果 ${ready} / ${a.questions}  ·  已返回文本 ${output} token`,25,ink,true);
      text(c,left+16,128,`活跃 attention KV  ${sample?sample.kv.toFixed(1):'—'} MiB`,21);
      const top=147,h=100;
      c.strokeStyle=light;c.lineWidth=1;
      for(let i=0;i<=2;i++){
        const y=top+i*h/2;c.beginPath();c.moveTo(x,y);c.lineTo(x+w,y);c.stroke();text(c,left+12,y+6,(kvMax-i*kvMax/2).toFixed(0),16,gray);
      }
      c.save();c.strokeStyle=color;c.lineWidth=3;c.beginPath();let previous=null;
      for(const s of a.samples){
        if(s.t>t)break;
        const xx=x+s.t/end*w, yy=top+h-s.kv/kvMax*h;
        if(previous){c.lineTo(xx,previous.y);c.lineTo(xx,yy);}else c.moveTo(xx,yy);
        previous={x:xx,y:yy};
      }
      if(previous)c.lineTo(x+Math.min(t,end)/end*w,previous.y);
      c.stroke();c.restore();
      const cursor=x+Math.min(t,end)/end*w;c.strokeStyle='#B9B9C0';c.lineWidth=1;c.setLineDash([4,5]);
      c.beginPath();c.moveTo(cursor,top);c.lineTo(cursor,top+h);c.stroke();c.setLineDash([]);
      text(c,left+16,276,`活跃线性状态 ${sample?sample.states:'—'} / 32 槽   ·   本次峰值 ${a.peak_states} 槽`,21);
      const rate=t>0?(uncached/Math.min(t,a.duration)).toFixed(0):'—';
      text(c,left+16,308,`prefill完成 ${computed.length} 题 · 累计结算速率 ${rate} 未命中token/s`,18,gray);
      [['未命中',uncached,331,color],['复用',cached,360,index===0?'#79B5EE':'#B8B8C0']].forEach(([label,n,y,col])=>{
        text(c,left+16,y+5,label,18,gray);c.fillStyle='#F0F0F3';c.fillRect(x,y-14,w-190,18);
        c.fillStyle=col;c.fillRect(x,y-14,(w-190)*n/tokenMax,18);text(c,x+w-176,y+3,n.toLocaleString(),20,ink,true);
      });
      text(c,left+16,393,'HTTP在途 / 结果点；浅灰为完整请求范围',18,gray);
      for(let task=0;task<a.tasks;task++){
        const y=417+task*20;text(c,left+16,y+6,'T'+(task+1),16,gray);
        for(const r of a.calls.filter(r=>r.task===task)){
          c.fillStyle='#E8E8ED';c.fillRect(x+r.start/end*w,y-7,(r.end-r.start)/end*w,12);
          if(t>r.start){c.fillStyle=color;c.fillRect(x+r.start/end*w,y-7,Math.max(0,Math.min(t,r.end)-r.start)/end*w,12);}
          c.beginPath();c.arc(x+r.ready/end*w,y-1,3,0,Math.PI*2);c.fillStyle=r.ready<=t?ink:'#C6C6CE';c.fill();
        }
      }
      const yAxis=492;c.strokeStyle=light;c.beginPath();c.moveTo(x,yAxis);c.lineTo(x+w,yAxis);c.stroke();
      for(let k=0;k<=4;k++)text(c,x+k*w/4-(k===4?44:10),yAxis+20,(end*k/4).toFixed(2)+'s',16,gray);
      text(c,left+16,541,`本次完成 ${a.duration.toFixed(3)}s · NVML ${g?(g.mib/1024).toFixed(2):'—'}GiB · KV池固定5.532GiB`,17,gray);
    });
  }
  function activate(root){
    let scene=data.scenes[root.dataset.scene],t=0,raf=null,previous=0,speed=Number(root.querySelector('.kv-rate').value||1);
    const canvas=root.querySelector('canvas'),play=root.querySelector('[data-kv=play]'),slider=root.querySelector('input');
    function apply(){
      root.dataset.time=t.toFixed(6);root.dataset.scene=scene.id;slider.max=scene.end;slider.value=t;
      root.querySelector('.kv-clock').textContent=`t = ${t.toFixed(3)} / ${scene.end.toFixed(3)}s`;
      root.querySelector('.kv-caption').textContent=`真实repeat ${scene.repeat} · 两个独立trial起点对齐 · token仅在prefill完成时结算`;
      draw(canvas,scene,t);
    }
    function stop(){if(raf)cancelAnimationFrame(raf);raf=null;root.dataset.playing='false';play.textContent='播放回放';}
    function frame(now){
      if(previous)t=Math.min(scene.end,t+(now-previous)/1000*speed);previous=now;apply();
      if(t>=scene.end)stop();else raf=requestAnimationFrame(frame);
    }
    function toggle(){if(raf){stop();return;}if(t>=scene.end)t=0;previous=0;root.dataset.playing='true';play.textContent='暂停回放';raf=requestAnimationFrame(frame);}
    function setTime(value){stop();t=Math.max(0,Math.min(scene.end,value));apply();}
    function next(){setTime(scene.points.find(x=>x>t+.00001)??scene.end);}
    function prev(){setTime([...scene.points].reverse().find(x=>x<t-.00001)??0);}
    root.querySelectorAll('[data-kv]').forEach(button=>button.onclick=e=>{
      e.stopPropagation();const a=button.dataset.kv;
      if(a==='play')toggle();if(a==='reset')setTime(0);if(a==='next')next();if(a==='prev')prev();if(a==='end')setTime(scene.end);
    });
    slider.oninput=()=>setTime(Number(slider.value));
    const select=root.querySelector('select.kv-scenes');
    if(select){select.value=scene.id;select.onchange=()=>{stop();scene=data.scenes[select.value];t=0;apply();};}
    const rate=root.querySelector('.kv-rate');rate.onchange=()=>{speed=Number(rate.value);};
    const api={next,prev,stop,toggle,setTime,get scene(){return scene;},canvas};root._kv=api;
    stop();apply();return api;
  }
  return {activate,data,draw};
})();
