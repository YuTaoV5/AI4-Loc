  let anim=null;
  function startAnim(sl){
    if(anim)anim.stop();anim=null;
    if(!sl.classList.contains('walk'))return;
    const frames=JSON.parse(sl.querySelector('.walk-data').textContent),play=sl.querySelector('[data-act=play]');
    let k=0,timer=null;
    function apply(){sl.dataset.step=k;sl.querySelectorAll('[data-a]').forEach(el=>el.classList.toggle('on',Number(el.dataset.a)<=k));sl.querySelector('.walk-caption').textContent=`${k+1}/${frames.length} · ${frames[k]}`;}
    function stop(){clearInterval(timer);timer=null;sl.dataset.playing='false';play.textContent='播放讲解';}
    function next(){stop();k=Math.min(frames.length-1,k+1);apply();}
    function prev(){stop();k=Math.max(0,k-1);apply();}
    function toggle(){if(timer){stop();return;}if(k===frames.length-1)k=0;apply();sl.dataset.playing='true';play.textContent='暂停讲解';timer=setInterval(()=>{if(k<frames.length-1){k++;apply();}else stop();},2600);}
    sl.querySelectorAll('[data-act]').forEach(b=>b.onclick=e=>{e.stopPropagation();({prev,next,play:toggle,reset:()=>{stop();k=0;apply();}}[b.dataset.act])();});
    stop();apply();anim={next,prev,stop,toggle};
  }
