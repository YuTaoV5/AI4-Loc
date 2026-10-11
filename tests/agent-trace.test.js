const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),os=require('os'),vm=require('vm');
const {readTrace}=require('../server/agent-trace');
function fixture(work){const data=fs.mkdtempSync(path.join(os.tmpdir(),'agent-trace-'));const dir=path.join(data,'agent-runs','fixture');fs.mkdirSync(dir,{recursive:true});try{work(data,dir);}finally{fs.rmSync(data,{recursive:true,force:true});}}
test('trace exposes Decision questions/options/probabilities but no input, headers or raw model responses',()=>fixture((data,dir)=>{
 fs.writeFileSync(path.join(dir,'decision-trace.json'),JSON.stringify({calls:[{status:'returned',request:{input:{private:'hidden log'},questions:[{id:'family',type:'choice',question:'Which detector?',options:[{name:'kasan',description:'KASAN'},{name:'other',description:'Other'}]}],headers:{Authorization:'Bearer private'}},response:{answers:{family:{choice:'kasan',probabilities:{kasan:.8,other:.2},label_mass:.1}},usage:{prompt_tokens:12,completion_tokens:0}},rawResponse:{reasoning:'hidden reasoning'}}]}));
 const result=readTrace(data,{id:'fixture',status:'running'});assert.equal(result.entries[0].questions[0].answer.probabilities.kasan,.8);assert.equal(result.entries[0].questions[0].question,'Which detector?');assert.equal(result.entries[0].usage.prompt_tokens,12);assert.doesNotMatch(JSON.stringify(result),/hidden log|private|hidden reasoning|Authorization/);
}));
test('live API records deduplicate attempts and tool result credentials are scrubbed',()=>fixture((data,dir)=>{
 fs.writeFileSync(path.join(dir,'api-calls.jsonl'),[{index:1,status:'started'},{index:1,status:'error',error:'Bearer test-secret',usage:{promptTokens:20}}].map(JSON.stringify).join('\n')+'\n{"partial":');
 fs.writeFileSync(path.join(dir,'tool-trace.jsonl'),JSON.stringify({id:'T1',tool:'source_read',arguments:{path:'a.c'},result:{apiKey:'hidden',text:dir+' password=private <think>reasoning</think>'}})+'\n');
 const r=readTrace(data,{id:'fixture',status:'failed'});assert.equal(r.entries.filter(x=>x.kind==='api').length,1);assert.equal(r.entries[0].status,'error');assert.equal(r.entries[0].usage.promptTokens,20);assert.doesNotMatch(JSON.stringify(r),/test-secret|private|reasoning|apiKey/);assert.match(JSON.stringify(r),/<workspace>/);
}));
test('history falls back to retained report metadata and oversized files report a gap',()=>fixture((data,dir)=>{
 fs.writeFileSync(path.join(dir,'decision-trace.json'),' '.repeat(2*1024*1024+1));
 const r=readTrace(data,{id:'fixture',status:'needs_review',analysis:{agent:{metrics:{requests:[{index:1,model:'fixture'}]},evidence:{commands:[{id:'T1',tool:'incident',result:{}}]}}}});
 assert.equal(r.entries.length,2);assert.equal(r.running,false);assert.ok(r.warnings.length);
}));
test('trace UI escapes question text, shows exact probabilities and retains original progress tab',()=>{
 const context={document:{addEventListener(){}},esc:x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),date:x=>x};vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../public/task-trace-ui.js'),'utf8')+'\nthis.ui=TaskTraceUI;',context);
 const ui=context.ui;assert.match(ui.frame('fixture',()=>'<p>original progress</p>'),/original progress/);ui.tab='trace';ui.trace={entries:[{id:'d1',kind:'decision',questions:[{id:'q',question:'<img onerror=bad>',options:[{name:'a'}],answer:{choice:'a',probabilities:{a:.8}}}]}]};const html=ui.frame('fixture',()=>'<p>original progress</p>');assert.match(html,/80.0000%/);assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img|original progress/);
});
