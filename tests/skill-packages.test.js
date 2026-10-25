const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),os=require('os');
const {execFileSync}=require('child_process'),packages=require('../server/skill-packages');

test('Skill metadata reads YAML and body triggers without manual fields',()=>{
 const parsed=packages.parseSkill('---\nname: inspect-oops\ndescription: Inspect first faults\ntriggers: ["BUG:", "Oops:"]\nmetadata:\n  keywords: KASAN, overflow\n---\n## 触发词\n- `panic`\n- "watchdog"\n## Investigation\n- not-a-trigger\n');
 assert.deepEqual(parsed.patterns,['BUG:','Oops:','KASAN','overflow','panic','watchdog']);assert.equal(parsed.name,'inspect-oops');
 assert.throws(()=>packages.parseSkill('no header'),/YAML/);assert.throws(()=>packages.parseSkill('---\nname: ../bad\ndescription: bad\n---\n'),/kebab-case/);
});

test('archive assets remain private until both gates pass, then stage into native Harness skills',async()=>{
 const data=fs.mkdtempSync(path.join(os.tmpdir(),'skill-package-')),id=require('crypto').randomUUID();
 const source=path.join(data,'fixture','inspect-oops');fs.mkdirSync(path.join(source,'references'),{recursive:true});
 fs.writeFileSync(path.join(source,'SKILL.md'),'---\nname: inspect-oops\ndescription: Inspect original evidence\ncategory: 内存越界\ntriggers: ["ovl_inode_upper"]\n---\nRead references/check.txt before reporting.\n');
 fs.writeFileSync(path.join(source,'references','check.txt'),'PACKAGE_RESOURCE_ONLY');const archive=path.join(data,'fixture.tar');execFileSync('tar',['-cf',archive,'-C',path.join(data,'fixture'),'.']);
 try{
  const extracted=await packages.ingest(data,id,{path:archive,originalname:'fixture.tar'});packages.seal(data,id);
  const skill={id,...extracted,pull:{status:'approved',reviewDecision:'approve'},evaluation:{passed:false}};
  assert.deepEqual(skill.patterns,['ovl_inode_upper']);assert.equal(skill.package.entries[0].name,'inspect-oops');
  assert.throws(()=>packages.publish(data,skill),/Benchmark/);assert.equal(fs.existsSync(packages.publicRoot(data)),false);
  const privateTask=path.join(data,'private-task');packages.stage(data,[skill],privateTask);assert.equal(fs.readdirSync(path.join(privateTask,'dsh-home','skills')).length,0);
  skill.pull.status='benchmark_passed';skill.evaluation.passed=true;skill.pull.reviewDecision='skip';assert.throws(()=>packages.publish(data,skill),/审核/);
  skill.pull.reviewDecision='approve';packages.publish(data,skill);assert.equal(skill.package.published,true);
  assert.equal(fs.readFileSync(path.join(packages.publicRoot(data),'inspect-oops','references','check.txt'),'utf8'),'PACKAGE_RESOURCE_ONLY');
  const task=path.join(data,'approved-task');assert.deepEqual(packages.stage(data,[skill],task),['inspect-oops']);
  assert.ok(fs.existsSync(path.join(task,'dsh-home','skills','inspect-oops','SKILL.md')));
  assert.throws(()=>packages.publish(data,skill),/名称已存在/);
  fs.writeFileSync(path.join(packages.privateRoot(data,id),'content','injected.txt'),'changed');assert.throws(()=>packages.verify(data,skill),/文件已变化/);
 }finally{assert.ok(data.startsWith(path.resolve(os.tmpdir())+path.sep));fs.rmSync(data,{recursive:true,force:true});}
});
