// Pure, versioned scoring. Only the trusted evaluator may supply rows.
const VERSION='agent-location-v1';
const REFERENCES={boundarySeconds:5,rootLocationSeconds:60,reportOutputSeconds:20,totalTokens:12000,modelRequests:4};
const RULES={version:VERSION,accuracyWeights:{stage:10,panicType:20,rootLocation:50},efficiencyWeights:{boundarySeconds:4,rootLocationSeconds:6,reportOutputSeconds:2,totalTokens:4,modelRequests:4},references:REFERENCES,formula:'每例 A=10×阶段命中+20×故障类型命中+50×根因代码命中；E=Σ w×r/(r+x)，仅三项全部命中且遥测完整才计 E；总分=mean(A+E)。排名先比较准确分，再比较总分，最后按完成时间。',rootDefinition:'文件路径、符号精确相等且预测行区间与真值重叠；最多 2 个候选位置、每个最多 40 行。健康负例要求明确无故障、无候选根因。代码命中不等于根因机制或引入提交已验证。',timing:'定界耗时=语义分类就绪；根因定位耗时=最终有效位置报告就绪（从 worker 开始，包含报告输出）；报告输出耗时=产生最终报告的模型请求起至校验完成，是定位耗时的子集。排队/准备耗时单列。',ranking:'同一数据/标注/模型/硬件/代码/预算 cohort 内，每位用户最佳有效成绩；失败及超时计 0，缺标签或缺成本遥测不得入榜。公开注入集练习榜，不代表盲测泛化能力。'};
const valid=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
function score(rows){
 if(!Array.isArray(rows)||!rows.length)return {total:null,accuracyPoints:null,eligible:false,reasons:['没有测试样本'],caseCount:0};
 const reasons=new Set();let accuracy=0,efficiency=0,stage=0,panic=0,root=0,completed=0;
 const totals=Object.fromEntries(Object.keys(REFERENCES).map(k=>[k,0]));let allTelemetry=true;
 for(const row of rows){
  const ok=row.status==='completed',s=row.scores||{},m=row.metrics||{};
  if(!row.isolationVerified)reasons.add('沙箱隔离审计未通过');
  if(!row.goldComplete)reasons.add('阶段/故障类型/根因代码真值不完整');
  const hits=[ok&&s.stageHit===true,ok&&s.panicTypeHit===true,ok&&s.codeLocationHit===true];
  completed+=+ok;stage+=+hits[0];panic+=+hits[1];root+=+hits[2];accuracy+=10*hits[0]+20*hits[1]+50*hits[2];
  const telemetry=m.tokensComplete===true&&Object.keys(REFERENCES).every(k=>valid(m[k]));
  if(!telemetry){reasons.add('存在缺失成本遥测');allTelemetry=false;}
  for(const k of Object.keys(totals))if(valid(m[k]))totals[k]+=m[k];
  if(hits.every(Boolean)&&telemetry)for(const [k,w] of Object.entries(RULES.efficiencyWeights))efficiency+=w*REFERENCES[k]/(REFERENCES[k]+m[k]);
 }
 const n=rows.length;return {version:VERSION,caseCount:n,completed,stageAccuracy:stage/n,panicTypeAccuracy:panic/n,codeLocationAccuracy:root/n,accuracyPoints:accuracy/n,efficiencyPoints:efficiency/n,total:(accuracy+efficiency)/n,eligible:!reasons.size,reasons:[...reasons],totals,telemetryComplete:allTelemetry,rootCauseMechanismAccuracy:null,introducingCommitAccuracy:null};
}
function leaderboard(runs,cohort){
 const sorted=runs.filter(r=>r.status==='completed'&&r.cohort===cohort&&r.score?.eligible).sort((a,b)=>b.score.accuracyPoints-a.score.accuracyPoints||b.score.total-a.score.total||a.completedAt.localeCompare(b.completedAt));
 const seen=new Set();return sorted.filter(r=>{if(seen.has(r.ownerId))return false;seen.add(r.ownerId);return true;}).slice(0,10).map((r,i)=>({rank:i+1,displayName:r.displayName,username:r.username,profileName:r.profile.name,runId:r.id,completedAt:r.completedAt,score:r.score}));
}
module.exports={VERSION,RULES,score,leaderboard};
