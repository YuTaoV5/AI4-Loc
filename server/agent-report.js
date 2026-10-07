const categories=['内存越界','释放后使用','任务挂起','锁依赖','RCU / 锁死','OOM','待专家分析'];
function normalize(a,lineCount,evidence){
 if(!a||!categories.includes(a.category)||typeof a.summary!=='string'||!a.summary.trim()||!Array.isArray(a.hypotheses)||!Array.isArray(a.nextSteps)||(a.limitations!==undefined&&!Array.isArray(a.limitations)))throw Error('模型返回的结构化报告不符合协议');
 const hypotheses=a.hypotheses.slice(0,8).map(h=>{
  if(!h||typeof h!=='object'||!Array.isArray(h.evidenceLines))throw Error('模型假设缺少有效证据行号数组');
  const evidenceLines=[...new Set(h.evidenceLines.filter(n=>Number.isInteger(n)&&n>0&&n<=lineCount))].slice(0,20);
  return {cause:String(h.cause||'').slice(0,4000),evidenceLines,confidence:evidenceLines.length&&['high','medium','low'].includes(h.confidence)?h.confidence:'low',verification:String(h.verification||'待人工核对').slice(0,2000)};
 });
 const result={category:a.category,summary:a.summary.slice(0,12000),hypotheses,nextSteps:a.nextSteps.slice(0,12).map(x=>String(x).slice(0,2000)),limitations:(a.limitations||[]).slice(0,10).map(x=>String(x).slice(0,2000))};
 if(evidence&&Array.isArray(evidence.families)&&evidence.families.length===0){result.category='待专家分析';result.hypotheses=[];result.summary='工具证据未命中支持的异常特征，当前材料不足以生成故障假设。';result.limitations.unshift('未提取到异常不等于证明系统健康；需要完整故障日志与人工核对。');}
 return result;
}
module.exports={normalize};
