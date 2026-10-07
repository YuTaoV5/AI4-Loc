const {test}=require('node:test'),assert=require('node:assert/strict');
const {normalize}=require('../server/agent-report');
const good=()=>({category:'内存越界',summary:'KASAN 越界，待核对对象布局',hypotheses:[{cause:'类型转换',evidenceLines:[1,2,2,0,99,'3',2.5],confidence:'high',verification:'核对精确版本结构体'}],nextSteps:['检查符号'],limitations:['缺少 vmcore']});
test('model evidence cannot fabricate out-of-range, string or duplicate log line references',()=>{
 const r=normalize(good(),4);assert.deepEqual(r.hypotheses[0].evidenceLines,[1,2]);assert.equal(r.hypotheses[0].confidence,'high');
});
test('malformed model reports fail explicitly instead of falling back to deterministic success',()=>{
 for(const patch of [{summary:''},{category:'已证明根因'},{hypotheses:[null]},{hypotheses:[{evidenceLines:'1'}]},{limitations:'unknown'},{nextSteps:null}])assert.throws(()=>normalize({...good(),...patch},4));
});
test('unrecognized confidence is conservative and does not fabricate numeric probabilities',()=>{
 const a=good();a.hypotheses[0].confidence='100%';const r=normalize(a,4);assert.equal(r.hypotheses[0].confidence,'low');assert.equal(r.probability,undefined);
});
test('hypothesis without valid log evidence cannot retain high confidence',()=>{
 const a=good();a.hypotheses[0].evidenceLines=[0,999,'1'];assert.equal(normalize(a,4).hypotheses[0].confidence,'low');
});
test('absence of programmatic fault signals overrides a model-generated diagnosis',()=>{
 const r=normalize(good(),4,{families:[]});assert.equal(r.category,'待专家分析');assert.deepEqual(r.hypotheses,[]);assert.match(r.summary,/材料不足/);
});
