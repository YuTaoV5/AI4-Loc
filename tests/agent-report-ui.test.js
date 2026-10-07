const {test}=require('node:test'),assert=require('assert/strict'),ui=require('../public/agent-report-ui');
test('website report headline skips normal debug and lock metadata before real fault',()=>{
 const {analyze,builtins}=require('../server/analyzer');const r=analyze('printk: debug: ignoring loglevel setting.\nmemory used by lock dependency info: 6365 kB\nBUG: KASAN: use-after-free in owner\n',builtins,[]);assert.match(r.headline,/^BUG: KASAN/);assert.equal(r.evidence[0].line,3);
});
test('closed-loop evidence renders first scene and code without legacy evidence arrays',()=>{
 const html=ui.render({id:'job'},{summary:'candidate',firstScene:{stage:'runtime',reportingComponent:'KASAN',affectedComponent:'module',description:'write after free',evidenceRefs:['T1']},localization:{mechanism:'lifetime',locations:[{path:'a.c',startLine:3,endLine:5,symbol:'f',evidenceRefs:['T3']}]},evidence:{commands:[{id:'T1',tool:'incident',result:{lines:[]}}]},metrics:{modelRequests:1,toolCalls:3}});
 assert.match(html,/a.c:3–5/);assert.match(html,/KASAN/);assert.match(html,/1 次模型请求/);assert.match(html,/根因已验证/);
});
test('legacy reports and untrusted model text render safely',()=>{
 const html=ui.render({id:'old'},{summary:'<script>alert(1)</script>',hypotheses:[],nextSteps:[],limitations:[],evidence:{commands:[{id:'C1',tool:'rg',exitCode:0,output:'<img src=x onerror=x>'}],logEvidence:[]}});assert.doesNotMatch(html,/<script|<img/);assert.match(html,/&lt;script/);
});
