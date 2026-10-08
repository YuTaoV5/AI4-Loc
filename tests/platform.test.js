const {test,before,after}=require('node:test');const assert=require('node:assert/strict');const fs=require('fs'),path=require('path'),os=require('os'),crypto=require('crypto');const {execFileSync}=require('child_process');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'kernel-insight-test-'));process.env.KERNEL_INSIGHT_DATA_DIR=temp;
process.env.KERNEL_BENCHMARK_DIR=path.join(__dirname,'fixtures/community-v1');
const app=require('../server/index');const {analyze,builtins}=require('../server/analyzer');const kernels=require('../server/kernels');
const manifest=require('./fixtures/community-v1/manifest.json');let server,base,adminToken,testerToken,otherToken;const nativeFetch=global.fetch;
before(async()=>{server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));base=`http://127.0.0.1:${server.address().port}`;const login=async(url,body)=>nativeFetch(base+url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(r=>r.json());adminToken=(await login('/api/auth/login',{username:'admin',password:'admin'})).token;testerToken=(await login('/api/auth/register',{username:'test_user',password:'test-pass'})).token;otherToken=(await login('/api/auth/register',{username:'other_user',password:'test-pass'})).token;global.fetch=(url,options={})=>nativeFetch(url,String(url).startsWith(base)?{...options,headers:{Authorization:'Bearer '+testerToken,...options.headers}}:options);});
after(()=>{global.fetch=nativeFetch;server.close();const resolved=path.resolve(temp);assert.ok(resolved.startsWith(path.resolve(os.tmpdir())+path.sep)&&path.basename(resolved).startsWith('kernel-insight-test-'));fs.rmSync(resolved,{recursive:true,force:true});});
const req=async(u,body,headers={})=>{const r=await fetch(base+u,body===undefined?{headers}:{method:'POST',headers:{'Content-Type':'application/json',...headers},body:JSON.stringify(body)});return {status:r.status,body:await r.json()};};
async function waitJob(id){for(let i=0;i<50;i++){const j=(await req('/api/jobs',undefined,{Authorization:'Bearer '+adminToken})).body.find(j=>j.id===id);if(!['queued','running'].includes(j.status))return j;await new Promise(r=>setTimeout(r,20));}throw Error('Job timeout');}
const log=c=>fs.readFileSync(path.join(__dirname,'fixtures/community-v1',c.logPath),'utf8');
test('low disk space refuses new analysis before creating a task and keeps reports readable',async()=>{
 const statfs=fs.statfsSync,headers={Authorization:'Bearer '+adminToken};const before=(await req('/api/jobs',undefined,headers)).body.length;
 fs.statfsSync=()=>({bavail:0,bsize:4096});
 try{const result=await req('/api/benchmark/'+manifest.cases[0].id+'/analyze',{},headers);assert.equal(result.status,507);assert.equal((await req('/api/jobs',undefined,headers)).body.length,before);}finally{fs.statfsSync=statfs;}
});
test('account management is administrator-only and cannot remove the final administrator',async()=>{
 assert.equal((await req('/api/admin/users')).status,403);const rows=(await req('/api/admin/users',undefined,{Authorization:'Bearer '+adminToken})).body;assert.ok(rows.every(u=>!u.passwordHash&&!u.salt));const target=rows.find(u=>u.username==='other_user'),admin=rows.find(u=>u.username==='admin');
 assert.equal((await req('/api/admin/users/'+target.id+'/role',{role:'leader'})).status,403);assert.equal((await req('/api/admin/users/'+target.id+'/role',{role:'invalid'},{Authorization:'Bearer '+adminToken})).status,400);assert.equal((await req('/api/admin/users/'+admin.id+'/role',{role:'tester'},{Authorization:'Bearer '+adminToken})).status,409);
 assert.equal((await req('/api/admin/users/'+target.id+'/role',{role:'leader'},{Authorization:'Bearer '+adminToken})).body.user.role,'leader');assert.equal((await req('/api/auth/me',undefined,{Authorization:'Bearer '+otherToken})).body.user.role,'leader');await req('/api/admin/users/'+target.id+'/role',{role:'tester'},{Authorization:'Bearer '+adminToken});
});
test('Markdown extensions render safely and preserve authored experience content',async()=>{
 const content='# 实际经验\n\n| 项目 | 结果 |\n| --- | --- |\n| 栈 | 已核对 |\n\n- [x] 验证\n\n```javascript\nconst evidence = true;\n```\n\n```mermaid\nflowchart LR\nA --> B\n```\n\n```plantuml\nAlice -> Bob: evidence\n```\n\n证据[^1]\n\n[^1]: 原始日志\n\n<script>alert(1)</script>\n\n[x](javascript:alert(1))';
 const preview=await req('/api/markdown/preview',{content});assert.equal(preview.status,200);const html=preview.body.html;assert.match(html,/<table>/);assert.match(html,/type="checkbox"/);assert.match(html,/hljs-keyword/);assert.match(html,/data-diagram="mermaid"/);assert.match(html,/data-diagram="plantuml"/);assert.match(html,/footnote/);assert.doesNotMatch(html,/<script|href="javascript:/);
 const created=await req('/api/skills',proposal({content}));assert.equal(created.status,201);const detail=await req('/api/experiences/'+created.body.id);assert.equal(detail.body.content,content);assert.equal(detail.body.html,html);assert.equal(detail.body.satisfaction,null);assert.equal((await req('/api/skills',proposal({content:'a'.repeat(100001)}))).status,400);
});
test('PlantUML renders local PNGs, caches results and refuses external references',async()=>{
 assert.equal((await req('/api/diagrams/plantuml',{source:'!include https://example.com/file'})).status,400);
 const rendered=await req('/api/diagrams/plantuml',{source:'@startuml\nAlice -> Bob: 本地分析\n@enduml'});assert.equal(rendered.status,200);const response=await fetch(base+rendered.body.url);assert.equal(response.status,200);const bytes=Buffer.from(await response.arrayBuffer());assert.equal(bytes.subarray(0,8).toString('hex'),'89504e470d0a1a0a');assert.ok(bytes.length>1000);assert.deepEqual((await req('/api/diagrams/plantuml',{source:'@startuml\nAlice -> Bob: 本地分析\n@enduml'})).body,rendered.body);assert.equal((await req('/api/diagrams/plantuml',{source:'@startuml\nclass Evidence\nclass Report\nEvidence --> Report\n@enduml'})).status,200);
});
test('experience satisfaction excludes trials and deduplicates rated problem signatures',()=>{
 const {metrics}=require('../server/experience');const job=(id,rating,at,isBenchmark=false)=>({id,isBenchmark,status:'resolved',analysis:{signature:'same',skills:[{id:'skill'}]},review:{rating,at}});
 const result=metrics({id:'skill'},[job('a',1,'2026-01-01'),job('b',5,'2026-01-02'),job('trial',1,'2026-01-03',true)]);assert.equal(result.used,2);assert.equal(result.confirmed,1);assert.equal(result.ratingCount,1);assert.equal(result.averageRating,5);assert.equal(result.satisfaction,100);assert.equal(metrics({id:'skill'},[]).satisfaction,null);
});
test('six sourced cases have integrity hashes, separate splits and real classified evidence',()=>{assert.equal(manifest.cases.length,6);for(const c of manifest.cases){const text=log(c);assert.equal(crypto.createHash('sha256').update(text).digest('hex'),c.sha256);const result=analyze(text,builtins,manifest.cases);assert.equal(result.category,c.category);assert.ok(result.evidence.length);assert.ok(result.candidates.some(x=>x.id===c.id));assert.equal(text.split(/\r?\n/)[result.evidence[0].line-1],result.evidence[0].text);}assert.equal(manifest.cases.filter(c=>c.split==='test').length,3);});
test('unknown log does not receive fabricated evidence or root cause',()=>{const r=analyze('system started normally',builtins,manifest.cases);assert.equal(r.category,'待专家分析');assert.equal(r.candidates.length,0);assert.equal(r.evidence.length,0);assert.equal(r.kernelVersion,null);});
test('versions and exact commits are extracted, signature keeps version separation',()=>{const text=log(manifest.cases[1]);const r=analyze(text,builtins,[]);assert.equal(r.kernelCommit,'fcc79e1714e8');assert.equal(r.kernelVersion,manifest.cases[1].kernelVersion);assert.notEqual(r.signature,analyze(text.replace('6.12.0-syzkaller','6.13.0-syzkaller'),builtins,[]).signature);assert.equal(r.signature,analyze(text.replaceAll('5894','12345'),builtins,[]).signature);});
test('exact source resolution and custom kernel rejection',()=>{assert.equal(kernels.resolve({version:'6.6.1'}).url,'https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.6.1.tar.xz');assert.ok(kernels.resolve({version:'6.13-rc2'}).url.includes('/testing/'));assert.equal(kernels.resolve({version:'6.6-custom',commit:'abcdef123456',repository:'stable'}).key,'stable-abcdef123456');assert.throws(()=>kernels.resolve({version:'6.6-custom'}),/定制/);assert.throws(()=>kernels.resolve({commit:'../../etc/passwd'}));assert.throws(()=>kernels.resolve({commit:'abcdef123456',repository:'unknown'}));});
test('empty uploads, missing APIs and invalid source inputs fail explicitly',async()=>{assert.equal((await req('/api/analyze',{})).status,400);assert.equal((await req('/api/missing')).status,404);assert.equal((await req('/api/kernels',{version:'6.6-custom'})).status,400);assert.equal((await req('/api/reports/bad%2Fid')).status,404);});
test('batch upload, report attribution, review, dedup and paired metrics',async()=>{
 const text=log(manifest.cases[1]);const fd=new FormData();fd.append('logs',new Blob([text]),'stress-one.log');fd.append('logs',new Blob([text.replaceAll('5894','9999')]),'stress-two.txt');fd.append('autoSource','false');fd.append('machine','test-lab');const r=await fetch(base+'/api/analyze',{method:'POST',body:fd});assert.equal(r.status,202);const jobs=await r.json();assert.equal(jobs.length,2);const first=await waitJob(jobs[0].id),second=await waitJob(jobs[1].id);assert.equal(first.status,'needs_review');assert.equal(second.status,'needs_review');assert.ok(first.duplicateOf||second.duplicateOf);assert.equal(first.analysis.skills[0].contributor,'项目内置规则');const report=await fetch(base+'/api/reports/'+first.id).then(r=>r.text());assert.match(report,/Skill 贡献者/);assert.match(report,/selinux/);
 assert.equal((await req(`/api/jobs/${first.id}/review`,{accepted:true,note:''})).status,400);assert.equal((await req(`/api/jobs/${first.id}/review`,{accepted:true,note:'verified',baselineMinutes:-1})).status,400);for(const rating of [0,6,2.5,'bad'])assert.equal((await req(`/api/jobs/${first.id}/review`,{accepted:true,note:'verified',rating})).status,400);
 await req(`/api/jobs/${first.id}/review`,{accepted:true,note:'API test verification',baselineMinutes:100,rating:5});await req(`/api/jobs/${second.id}/review`,{accepted:true,note:'same signature verified',baselineMinutes:100});const d=(await req('/api/dashboard')).body;assert.equal(d.total,1);assert.equal(d.resolved,1);assert.equal(d.duplicates,1);assert.equal(d.pairedCount,1);assert.ok(d.improvement>90);
 await req(`/api/jobs/${first.id}/review`,{accepted:false,note:'need more evidence'});await req(`/api/jobs/${second.id}/review`,{accepted:false,note:'need reproduction'});assert.equal((await req('/api/dashboard')).body.resolved,0);assert.ok((await req('/api/skills')).body.find(s=>s.id==='memory-oob').feedback>=2);
});
test('benchmark run excluded from leadership metrics',async()=>{const before=(await req('/api/dashboard')).body;const r=await req('/api/benchmark/LINUX-003/analyze',{autoSource:false});assert.equal(r.status,202);const j=await waitJob(r.body.id);assert.equal(j.analysis.category,'任务挂起');await req(`/api/jobs/${j.id}/review`,{accepted:true,note:'test run',baselineMinutes:90});const after=(await req('/api/dashboard')).body;assert.equal(after.total,before.total);assert.equal(after.resolved,before.resolved);});
const adminHeaders=()=>({Authorization:'Bearer '+adminToken});
const proposal=(extra={})=>({name:'Perf lifecycle',contributor:'Test Expert',category:'任务挂起',patterns:['blocked for more than'],guidance:'Check task work synchronization',...extra});
async function waitSkill(id){for(let i=0;i<100;i++){const s=(await req('/api/skills')).body.find(s=>s.id===id);if(s.pull.status!=='testing')return s;await new Promise(r=>setTimeout(r,10));}throw Error('test timeout');}
test('PR gates, fixed benchmark, ownership and merge permissions are enforced',async()=>{
 const r=await req('/api/skills',proposal());assert.equal(r.status,201);const id=r.body.id,owner={'X-Submission-Token':r.body.ownerToken};assert.equal(r.body.pull.caseCount,6);
 assert.equal((await req('/api/skills')).body.find(s=>s.id===id).ownerToken,undefined);
 assert.equal((await req('/api/skills/'+id+'/evaluate',{},owner)).status,409);
 assert.equal((await req('/api/skills/'+id+'/review',{decision:'approve',note:'good'})).status,403);
 assert.equal((await req('/api/skills/'+id+'/activate',{},adminHeaders())).status,409);
 assert.equal((await req('/api/skills/'+id+'/review',{decision:'approve',note:'Reviewed evidence'},adminHeaders())).status,200);
 assert.equal((await req('/api/skills/'+id+'/evaluate',{}, {Authorization:'Bearer '+otherToken})).status,403);
 assert.equal((await req('/api/skills/'+id+'/evaluate',{},owner)).status,202);
 const evaluated=await waitSkill(id);assert.equal(evaluated.evaluation.passed,true);assert.equal(evaluated.evaluation.regressions,0);assert.equal(evaluated.evaluation.results.length,7);
 assert.equal((await req('/api/skills/'+id+'/activate',{},owner)).status,403);
 assert.equal((await req('/api/skills/'+id+'/activate',{},adminHeaders())).status,200);
 const fd=new FormData();fd.append('logText',log(manifest.cases[2]));fd.append('autoSource','false');fd.append('skillPreset','custom');fd.append('skillIds',JSON.stringify([id]));
 const jobs=await fetch(base+'/api/analyze',{method:'POST',body:fd}).then(r=>r.json());const j=await waitJob(jobs[0].id);assert.equal(j.analysis.skills.length,1);assert.equal(j.analysis.skills[0].contributor,'Test Expert');assert.deepEqual(j.skillSelection.ids,[id]);
 const rank=(await req('/api/contributors')).body.rows[0];assert.equal(rank.name,'Test Expert');assert.equal(rank.used,1);assert.equal(rank.benchmark,100);
});
test('administrator skip still requires tests and broad matching cannot regress baseline',async()=>{
 const r=await req('/api/skills',proposal({name:'Bad broad rule',patterns:['BUG:','blocked for more than']}));const id=r.body.id;
 await req('/api/skills/'+id+'/review',{decision:'skip',note:'Admin fast path'},adminHeaders());assert.equal((await req('/api/skills/'+id+'/activate',{},adminHeaders())).status,409);
 await req('/api/skills/'+id+'/evaluate',{},adminHeaders());const s=await waitSkill(id);assert.equal(s.evaluation.passed,false);assert.ok(s.evaluation.regressions>0);assert.equal((await req('/api/skills/'+id+'/activate',{},adminHeaders())).status,409);
});
test('changed baseline invalidates otherwise passing merge and requires manual retest',async()=>{
 const a=(await req('/api/skills',proposal({name:'A'}))).body,b=(await req('/api/skills',proposal({name:'B'}))).body;
 for(const s of [a,b]){await req('/api/skills/'+s.id+'/review',{decision:'approve',note:'checked'},adminHeaders());await req('/api/skills/'+s.id+'/evaluate',{},adminHeaders());assert.equal((await waitSkill(s.id)).evaluation.passed,true);}
 await req('/api/skills/'+a.id+'/activate',{},adminHeaders());assert.equal((await req('/api/skills/'+b.id+'/activate',{},adminHeaders())).status,409);
 await req('/api/skills/'+b.id+'/evaluate',{},adminHeaders());await waitSkill(b.id);assert.equal((await req('/api/skills/'+b.id+'/activate',{},adminHeaders())).status,200);
});
test('custom selection validates active IDs and memory preset excludes blocking rules',async()=>{
 for(const ids of [[],['not-active']])assert.equal((await req('/api/analyze',{logText:'test',autoSource:'false',skillPreset:'custom',skillIds:JSON.stringify(ids)})).status,400);
 const r=await req('/api/analyze',{logText:log(manifest.cases[2]),autoSource:'false',skillPreset:'memory'});const j=await waitJob(r.body[0].id);assert.equal(j.analysis.category,'待专家分析');assert.equal(j.skillSelection.preset,'memory');
});
test('archive logs are read without extraction to arbitrary paths',async()=>{const dir=path.join(temp,'archive-input');fs.mkdirSync(dir);fs.writeFileSync(path.join(dir,'kernel.txt'),log(manifest.cases[0]));const archive=path.join(temp,'logs.tar');execFileSync('tar',['-cf',archive,'-C',dir,'kernel.txt']);const fd=new FormData();fd.append('logs',new Blob([fs.readFileSync(archive)]),'logs.tar');fd.append('autoSource','false');const jobs=await fetch(base+'/api/analyze',{method:'POST',body:fd}).then(r=>r.json());const j=await waitJob(jobs[0].id);assert.equal(j.analysis.category,'内存越界');assert.match(await fetch(base+'/api/jobs/'+j.id+'/log').then(r=>r.text()),/# FILE: kernel.txt/);});
test('state is persisted with review and contribution',async()=>{const saved=JSON.parse(fs.readFileSync(path.join(temp,'state.json')));assert.ok(saved.jobs.some(j=>j.review));assert.ok(saved.skills.some(s=>s.contributor==='Test Expert'));});
test('source downloads verify checksum, extract Makefile, reuse cache and expose checksum failure',async()=>{
 const input=path.join(temp,'source-fixture');const tree=path.join(input,'linux-6.6.999');fs.mkdirSync(tree,{recursive:true});fs.writeFileSync(path.join(tree,'Makefile'),'VERSION = 6\nPATCHLEVEL = 6\nSUBLEVEL = 999\n');const archive=path.join(temp,'fixture.tar.xz');execFileSync('tar',['-cJf',archive,'-C',input,'linux-6.6.999']);const bytes=fs.readFileSync(archive),hash=crypto.createHash('sha256').update(bytes).digest('hex');const originalFetch=global.fetch;
 global.fetch=async(url,options)=>String(url).startsWith('https://cdn.kernel.org/')?new Response(String(url).endsWith('sha256sums.asc')?`${hash}  linux-6.6.999.tar.xz\n${'0'.repeat(64)}  linux-6.6.998.tar.xz\n`:bytes,{headers:{'content-type':String(url).endsWith('.asc')?'text/plain':'application/x-xz'}}):originalFetch(url,options);
 const wait=async(k)=>{for(let i=0;i<200;i++){if(['ready','failed'].includes(k.status))return k;await new Promise(r=>setTimeout(r,20));}throw Error('Source worker timeout');};
 try{const entry=kernels.ensure({version:'6.6.999'});assert.equal(kernels.ensure({version:'6.6.999'}),entry);await wait(entry);assert.equal(entry.status,'ready',entry.error);assert.equal(entry.sha256,hash);assert.equal(entry.verification,'official-sha256');assert.ok(fs.existsSync(path.join(entry.sourcePath,'Makefile')));assert.equal(kernels.ensure({version:'6.6.999'}).status,'ready');const source=await req('/api/kernels/release-6.6.999/source?file=Makefile&line=1');assert.equal(source.status,200);assert.equal(source.body.lines[0].text,'VERSION = 6');assert.equal((await req('/api/kernels/release-6.6.999/source?file=../../state.json')).status,400);const corrupt=kernels.ensure({version:'6.6.998'});await wait(corrupt);assert.equal(corrupt.status,'failed');assert.match(corrupt.error,/SHA256/);}finally{global.fetch=originalFetch;}
});
test('Windows source extraction materializes safe links and rejects outside targets',async()=>{
 const tarEntries=entries=>Buffer.concat([...entries.flatMap(e=>{const h=Buffer.alloc(512);h.write(e.name,0,100);h.write('0000644\0',100,8);h.write('0000000\0',108,8);h.write('0000000\0',116,8);const body=Buffer.from(e.content||'');h.write(body.length.toString(8).padStart(11,'0')+'\0',124,12);h.write('00000000000\0',136,12);h.fill(32,148,156);h.write(e.target?'2':'0',156,1);if(e.target)h.write(e.target,157,100);h.write('ustar\0',257,6);h.write('00',263,2);h.write([...h].reduce((a,b)=>a+b,0).toString(8).padStart(6,'0')+'\0 ',148,8);return [h,body,Buffer.alloc((512-body.length%512)%512)];}),Buffer.alloc(1024)]);
 const archive=path.join(temp,'links.tar');fs.writeFileSync(archive,tarEntries([{name:'linux-fixture/Makefile',content:'VERSION = 6'},{name:'linux-fixture/include/core.h',content:'#define SOURCE 1\n'},{name:'linux-fixture/include/alias.h',target:'core.h'},{name:'linux-fixture/include-link',target:'include'}]));const dest=path.join(temp,'link-output');fs.mkdirSync(dest);const result=await kernels.extractArchive(archive,dest);assert.equal(fs.readFileSync(path.join(result.sourcePath,'include/alias.h'),'utf8'),'#define SOURCE 1\n');assert.equal(fs.readFileSync(path.join(result.sourcePath,'include-link/core.h'),'utf8'),'#define SOURCE 1\n');
 if(process.platform==='win32'){const bad=path.join(temp,'bad-links.tar');fs.writeFileSync(bad,tarEntries([{name:'linux-bad/Makefile',content:'VERSION = 6'},{name:'linux-bad/escape',target:'../../outside'}]));await assert.rejects(kernels.extractArchive(bad,dest),/超出源码/);}
});

test('benchmark score differentiates coverage and replacement preserves original coverage',async()=>{
 const replacement=(await req('/api/skills',proposal({name:'Partial OOB replacement',category:'内存越界',patterns:['ovl_inode_upper'],replaces:'memory-oob'}))).body;
 await req('/api/skills/'+replacement.id+'/review',{decision:'approve',note:'coverage test'},adminHeaders());await req('/api/skills/'+replacement.id+'/evaluate',{},adminHeaders());const result=await waitSkill(replacement.id);assert.equal(result.evaluation.candidateScore,.5);assert.equal(result.evaluation.passed,false);assert.ok(result.evaluation.regressions>=2);
 const snapshot=JSON.parse(fs.readFileSync(path.join(temp,'skill-pulls',replacement.id,'benchmark.json'),'utf8'));assert.equal(snapshot.cases.length,6);for(const c of snapshot.cases)assert.equal(crypto.createHash('sha256').update(c.log).digest('hex'),c.sha256);
});

test('personal workspace isolates submissions, trial jobs, scoring history and owned skills',async()=>{
 const client=(await req('/api/auth/register',{username:'personal_user',password:'pass1234'})).body.token,other=(await req('/api/auth/register',{username:'personal_other',password:'pass1234'})).body.token,headers={Authorization:'Bearer '+client};
 const getMine=key=>fetch(base+'/api/me',{headers:{Authorization:'Bearer '+key}}).then(r=>r.json());
 assert.equal((await req('/api/me',undefined,{Authorization:'Bearer invalid'})).status,401);
 const task=(await req('/api/analyze',{logText:log(manifest.cases[2]),autoSource:'false'},headers)).body[0];await waitJob(task.id);
 const trial=(await req('/api/benchmark/LINUX-003/analyze',{autoSource:false},headers)).body;await waitJob(trial.id);
 const proposalResult=(await req('/api/skills',proposal({name:'Personal contribution'}),headers)).body;
 await req('/api/skills/'+proposalResult.id+'/review',{decision:'approve',note:'Personal scope test'},adminHeaders());await req('/api/skills/'+proposalResult.id+'/evaluate',{}, {...headers,'X-Submission-Token':proposalResult.ownerToken});await waitSkill(proposalResult.id);
 const mine=await getMine(client),theirs=await getMine(other);assert.equal(mine.jobs.length,2);assert.equal(mine.jobs.find(j=>j.isBenchmark).benchmarkCaseId,'LINUX-003');assert.equal(mine.skills.length,1);assert.equal(mine.skills[0].ownerToken,undefined);assert.equal(mine.benchmarkRuns.length,1);assert.equal(mine.benchmarkRuns[0].skillId,proposalResult.id);assert.equal(theirs.jobs.length,0);assert.equal(theirs.skills.length,0);assert.equal(theirs.benchmarkRuns.length,0);
 assert.equal((await req('/api/me/claim-skill',{id:proposalResult.id,token:'bad'},{Authorization:'Bearer '+other})).status,403);assert.equal((await req('/api/me/claim-skill',{id:proposalResult.id,token:proposalResult.ownerToken},{'X-Client-Id':other})).status,409);
});

test('default admin login, registration roles, hashed credentials, logout and protected APIs',async()=>{
 const bad=await req('/api/auth/login',{username:'admin',password:'wrong'});assert.equal(bad.status,401);
 const logged=await req('/api/auth/login',{username:'admin',password:'admin'});assert.equal(logged.body.user.role,'admin');assert.equal(logged.body.user.passwordHash,undefined);
 assert.equal((await req('/api/auth/register',{username:'test_user',password:'test-pass'})).status,409);
 const registered=await req('/api/auth/register',{username:'no_escalation',password:'pass1234',role:'admin'});assert.equal(registered.body.user.role,'tester');
 const headers={Authorization:'Bearer '+registered.body.token};assert.equal((await req('/api/auth/claim-history',{},headers)).status,403);
 assert.equal((await req('/api/jobs',undefined,{Authorization:'Bearer invalid'})).status,401);
 await req('/api/auth/logout',{},headers);assert.equal((await req('/api/me',undefined,headers)).status,401);
 const saved=JSON.parse(fs.readFileSync(path.join(temp,'accounts.json')));const admin=saved.users.find(u=>u.username==='admin');assert.equal(admin.password,undefined);assert.equal(admin.passwordHash.length,128);assert.ok(admin.salt);
});
test('task progress records real stages, streams snapshots, and blocks another account',async()=>{
 const created=await req('/api/analyze',{logText:log(manifest.cases[2]),autoSource:'false'});const j=await waitJob(created.body[0].id);
 const progress=(await req('/api/jobs/'+j.id+'/progress')).body;assert.equal(progress.stage,'complete');assert.equal(progress.agent.status,'completed');assert.deepEqual(progress.timeline.map(t=>t.stage),['queued','reading','extracting','matching','source','report','complete']);assert.ok(progress.timeline.every(t=>t.startedAt));assert.ok(progress.timeline.slice(0,-1).every(t=>t.endedAt));
 for(const route of ['/progress','/events','/log'])assert.equal((await req('/api/jobs/'+j.id+route,undefined,{Authorization:'Bearer '+otherToken})).status,403);
 assert.equal((await req('/api/jobs/'+j.id+'/review',{accepted:true,note:'unauthorized'},{Authorization:'Bearer '+otherToken})).status,403);
 const abort=new AbortController(),stream=await fetch(base+'/api/jobs/'+j.id+'/events',{signal:abort.signal});assert.match(stream.headers.get('content-type'),/text\/event-stream/);const reader=stream.body.getReader(),chunk=await reader.read();assert.match(new TextDecoder().decode(chunk.value),/event: progress/);abort.abort();
 const failed=(await req('/api/analyze',{logText:'bad\u0000input',autoSource:'false'})).body[0];const broken=await waitJob(failed.id);assert.equal(broken.stage,'failed');assert.equal(broken.agent.status,'failed');
});

test('analysis requests coalesce, reuse results, isolate owners, and rerun changed conditions',async()=>{
 const registered=await req('/api/auth/register',{username:'dedup_test',password:'test-pass',role:'expert'});assert.equal(registered.body.user.role,'tester');const headers={Authorization:'Bearer '+registered.body.token};const body={logText:log(manifest.cases[0])+'\nDedup fixture',autoSource:'false'};
 const [a,b]=await Promise.all([req('/api/analyze',body,headers),req('/api/analyze',body,headers)]);assert.equal(a.body[0].id,b.body[0].id);assert.equal([a,b].filter(r=>r.body[0].reused).length,1);await waitJob(a.body[0].id);const repeated=await req('/api/analyze',body,headers);assert.equal(repeated.body[0].id,a.body[0].id);assert.equal(repeated.body[0].reused,true);assert.equal((await req('/api/me',undefined,headers)).body.jobs.length,1);
 const newline=await req('/api/analyze',{...body,logText:body.logText.replace(/\n/g,'\r\n')},headers);assert.equal(newline.body[0].id,a.body[0].id);
 const forced=await req('/api/analyze',{...body,forceRerun:true},headers);assert.notEqual(forced.body[0].id,a.body[0].id);await waitJob(forced.body[0].id);
 const changed=await req('/api/analyze',{...body,skillPreset:'custom',skillIds:['memory-oob']},headers);assert.notEqual(changed.body[0].id,forced.body[0].id);await waitJob(changed.body[0].id);const other=await req('/api/analyze',body,{Authorization:'Bearer '+otherToken});assert.notEqual(other.body[0].id,a.body[0].id);await waitJob(other.body[0].id);
 const trialA=(await req('/api/benchmark/LINUX-001/analyze',{autoSource:false},headers)).body;await waitJob(trialA.id);const trialB=(await req('/api/benchmark/LINUX-001/analyze',{autoSource:false},headers)).body;assert.equal(trialA.id,trialB.id);assert.equal(trialB.reused,true);
});

test('diagnostic materials validate file types, bind ownership and change task reuse conditions',async()=>{
 const send=async(name,bytes,kind='symbols',headers={})=>{const fd=new FormData();fd.append(kind,new Blob([bytes]),name);return fetch(base+'/api/materials',{method:'POST',body:fd,headers});};
 assert.equal((await send('fake.elf','not ELF')).status,400);
 const elf=Buffer.alloc(64);Buffer.from([127,69,76,70,2,1,1]).copy(elf);elf.writeUInt16LE(2,16);elf.writeUInt16LE(62,18);
 assert.equal((await send('wrong.vmcore',elf,'vmcore')).status,400);
 const response=await send('vmlinux',elf);assert.equal(response.status,201);const bundle=await response.json();assert.equal(bundle.files[0].sha256,crypto.createHash('sha256').update(elf).digest('hex'));
 assert.equal((await req('/api/materials/'+bundle.id,undefined,{Authorization:'Bearer '+otherToken})).status,403);
 assert.equal((await req('/api/analyze',{logText:'normal material fixture',autoSource:'false',materialsId:bundle.id},{Authorization:'Bearer '+otherToken})).status,400);
 const first=(await req('/api/analyze',{logText:'normal material fixture',autoSource:'false',materialsId:bundle.id})).body[0];
 assert.equal((await waitJob(first.id)).materials.id,bundle.id);
 const different=(await req('/api/analyze',{logText:'normal material fixture',autoSource:'false'})).body[0];assert.notEqual(first.id,different.id);
 const reused=(await req('/api/analyze',{logText:'normal material fixture',autoSource:'false',materialsId:bundle.id})).body[0];assert.equal(reused.id,first.id);assert.equal(reused.reused,true);
 assert.equal((await send('.config','CONFIG_DEBUG_INFO=y\n','kernelConfig')).status,201);
});

test('personal Agent/Skill profiles are owned, canonical, versioned, and used by analysis',async()=>{
 const body={name:'我的源码调查组合',agentId:'chat-investigator',skillIds:['memory-oob'],extraPrompt:'Inspect ownership, preserve evidence.',isDefault:true};
 const preview=await req('/api/agent-profiles/preview',{...body,prompt:'forged'});assert.equal(preview.status,200);assert.match(preview.body.prompt,/Inspect ownership/);assert.doesNotMatch(preview.body.prompt,/forged/);
 assert.equal((await req('/api/me/agent-profiles',{...body,agentId:'arbitrary-shell'})).status,400);
 assert.equal((await req('/api/me/agent-profiles',{...body,skillIds:['missing']})).status,400);
 const created=await req('/api/me/agent-profiles',body);assert.equal(created.status,201);const p=created.body;
 assert.equal(p.prompt,preview.body.prompt);assert.equal((await req('/api/me/agent-profiles',undefined,{Authorization:'Bearer '+otherToken})).body.length,0);
 assert.equal((await req('/api/analyze',{logText:log(manifest.cases[1]),autoSource:'false',agentProfileId:p.id},{Authorization:'Bearer '+otherToken})).status,400);
 const analyzed=await req('/api/analyze',{logText:log(manifest.cases[1]),autoSource:'false',agentProfileId:p.id});assert.equal(analyzed.status,202);const j=await waitJob(analyzed.body[0].id);assert.equal(j.agentProfile.hash,p.hash);assert.deepEqual(j.skillSelection.ids,['memory-oob']);
 const updated=await fetch(base+'/api/me/agent-profiles/'+p.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,extraPrompt:'Changed'})}).then(r=>r.json());assert.equal(updated.revision,2);assert.notEqual(updated.hash,p.hash);assert.equal((await req('/api/jobs')).body.find(x=>x.id===j.id).agentProfile.hash,p.hash);
 const another=await req('/api/me/agent-profiles',{...body,name:'另一个常用组合'});assert.equal((await req('/api/me/agent-profiles')).body.filter(x=>x.isDefault).length,1);
 assert.equal((await req('/api/benchmark/runs',{agentProfileId:another.body.id,publish:true,score:100})).status,409);
 assert.equal((await req('/api/benchmark/leaderboard')).body.rows.length,0);assert.equal((await req('/api/me')).body.agentProfiles.length,2);
 const removed=await fetch(base+'/api/me/agent-profiles/'+p.id,{method:'DELETE',headers:{Authorization:'Bearer '+otherToken}});assert.equal(removed.status,404);
 assert.equal((await req('/api/benchmark/runs/not-found')).status,404);
});
