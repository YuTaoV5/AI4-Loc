const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path');
const {analyze,builtins}=require('../server/analyzer');
test('generic phone triggers retain Skill attribution without masking any supported fault category',()=>{
 const phone={id:'phone-guide',name:'Phone evidence guide',status:'active',category:'待专家分析',patterns:['HUAWEI','Kirin']},fixture=path.join(__dirname,'fixtures/community-v1'),cases=JSON.parse(fs.readFileSync(path.join(fixture,'manifest.json'))).cases;
 for(const c of cases){const result=analyze('HUAWEI Kirin\n'+fs.readFileSync(path.join(fixture,c.logPath),'utf8'),[phone,...builtins],cases);assert.equal(result.category,c.category);assert.ok(result.skills.some(s=>s.id===phone.id));}
 assert.equal(analyze('HUAWEI Kirin: boot complete; no fault evidence',[phone,...builtins],[]).category,'待专家分析');
});
