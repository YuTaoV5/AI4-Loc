const fs=require('fs'),path=require('path'),crypto=require('crypto'),YAML=require('yaml');
const {execFile}=require('child_process'),run=require('util').promisify(execFile);
const digest=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const publicRoot=data=>path.join(data,'harness-home','skills');
const privateRoot=(data,id)=>path.join(data,'skill-pulls',id,'package');
const words=value=>Array.isArray(value)?value.flatMap(words):typeof value==='string'?value.split(/[,，;；\n]/).map(x=>x.trim().replace(/^[-*]\s+/,'').replace(/^[`"']|[`"']$/g,'')).filter(Boolean):[];

function parseSkill(text){
 const match=text.replace(/^\uFEFF/,'').match(/^---\s*\r?\n([\s\S]*?)\r?\n---\s*(?:\r?\n|$)/);
 if(!match)throw Error('SKILL.md 需要包含 name 和 description 的 YAML 头部');
 const metadata=YAML.parse(match[1],{maxAliasCount:50})||{};
 if(typeof metadata.name!=='string'||!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(metadata.name)||metadata.name.length>80)throw Error('Skill name 须为英文小写 kebab-case，例如 kernel-oops');
 if(typeof metadata.description!=='string'||!metadata.description.trim())throw Error('SKILL.md 缺少 description');
 const patterns=[];
 for(const source of [metadata,metadata.metadata||{}])for(const key of ['triggers','trigger_words','triggerWords','keywords','patterns','触发词','触发关键词'])patterns.push(...words(source[key]));
 const body=text.slice(match[0].length);let section=false;
 for(const line of body.split(/\r?\n/)){
  if(/^#{1,6}\s/.test(line)){section=/^#{1,6}\s*(?:触发词|触发关键词|匹配词|Triggers?|Trigger words|Keywords)\s*[:：]?\s*$/i.test(line);continue;}
  const inline=line.match(/^(?:触发词|触发关键词|匹配词|Triggers?|Trigger words|Keywords)\s*[:：]\s*(.+)$/i);
  if(inline)patterns.push(...words(inline[1]));else if(section&&/^\s*[-*]\s+/.test(line))patterns.push(...words(line.trim()));
 }
 return {name:metadata.name,description:metadata.description.trim(),version:String(metadata.version||metadata.metadata?.version||'1.0.0'),category:metadata.category||metadata.metadata?.category,patterns:[...new Set(patterns)].filter(w=>w.length<=200).slice(0,20)};
}

async function ingest(data,id,file){
 const directory=privateRoot(data,id);fs.mkdirSync(directory,{recursive:true,mode:0o700});
 const original=path.join(directory,'original');fs.copyFileSync(file.path,original);
 const content=path.join(directory,'content');
 const {stdout}=await run(process.env.KERNEL_AGENT_PYTHON||(process.platform==='win32'?'python':'python3'),[path.join(__dirname,'../scripts/problem-extract.py'),original,content],{timeout:120000,maxBuffer:1024*1024,windowsHide:true});
 const extraction=JSON.parse(stdout);if(extraction.status!=='extracted')throw Error('Skill 压缩包无法展开：'+extraction.message);
 const entries=[];let count=0;
 function scan(dir){for(const item of fs.readdirSync(dir,{withFileTypes:true})){if(item.name==='__MACOSX'||item.name==='.git')continue;const file=path.join(dir,item.name);if(item.isDirectory())scan(file);else if(item.isFile()&&item.name==='SKILL.md'){
  if(++count>20)throw Error('每个 Skill 包最多包含 20 个 SKILL.md');
  if(fs.statSync(file).size>100000)throw Error('单个 SKILL.md 不能超过 100000 字节');
  const text=fs.readFileSync(file,'utf8'),metadata=parseSkill(text);entries.push({...metadata,path:path.relative(content,path.dirname(file)).split(path.sep).join('/')||'.',content:text});
 }}}
 scan(content);if(!entries.length)throw Error('压缩包内未找到 SKILL.md');
 if(entries.reduce((total,e)=>total+e.content.length,0)>100000)throw Error('Skill 包正文合计不能超过 100000 字符');
 if(new Set(entries.map(e=>e.name)).size!==entries.length)throw Error('压缩包内 Skill name 不能重复');
 const patterns=[...new Set(entries.flatMap(e=>e.patterns))].slice(0,20),allowed=['内存越界','释放后使用','任务挂起','锁依赖','RCU / 锁死','OOM'];
 let category=entries.map(e=>e.category).find(c=>allowed.includes(c));
 if(!category){const hints=patterns.join(' ').toLowerCase();category=/use.after.free|uaf/.test(hints)?'释放后使用':/out.of.bounds|oob|kasan/.test(hints)?'内存越界':/oom|out of memory/.test(hints)?'OOM':/rcu|lockup/.test(hints)?'RCU / 锁死':/hung|blocked for more/.test(hints)?'任务挂起':/lockdep|deadlock|locking/.test(hints)?'锁依赖':'待专家分析';}
 const record={sha256:digest(original),originalName:path.basename(file.originalname),files:extraction.files,bytes:extraction.bytes,entries:entries.map(({content,...entry})=>entry)};
 fs.writeFileSync(path.join(directory,'manifest.json'),JSON.stringify(record,null,2),{mode:0o600});
 return {name:entries[0].name,version:entries[0].version,category,patterns,guidance:entries.map(e=>e.description).join('\n').slice(0,4000),content:entries.map(e=>e.content).join('\n\n'),package:record};
}

function fileManifest(content){
 const files={};
 function scan(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true}).sort((a,b)=>a.name<b.name?-1:1)){const file=path.join(dir,entry.name);if(entry.isDirectory())scan(file);else if(entry.isFile())files[path.relative(content,file)]=digest(file);else throw Error('Skill 包不能包含链接或特殊文件');}}
 scan(content);return files;
}
function verify(data,skill){
 if(!skill.package)return;
 const original=path.join(privateRoot(data,skill.id),'original');if(digest(original)!==skill.package.sha256)throw Error('Skill 压缩包指纹已变化，请重新投稿');
 // A manifest of every expanded file prevents helpers changing after review.
 const manifestFile=path.join(privateRoot(data,skill.id),'files.json');
 const content=path.join(privateRoot(data,skill.id),'content');
 if(!fs.existsSync(manifestFile)||JSON.stringify(fileManifest(content))!==JSON.stringify(JSON.parse(fs.readFileSync(manifestFile))))throw Error('Skill 文件已变化，请重新投稿');
}
function seal(data,id){
 const root=privateRoot(data,id);fs.writeFileSync(path.join(root,'files.json'),JSON.stringify(fileManifest(path.join(root,'content'))),{mode:0o600});
}
function publish(data,skill){
 if(!skill.package)return;
 if(skill.pull?.reviewDecision!=='approve'||!skill.evaluation?.passed||skill.pull.status!=='benchmark_passed')throw Error('Skill 包必须审核通过且 Benchmark 通过后才能进入公共目录');
 verify(data,skill);const root=publicRoot(data);fs.mkdirSync(root,{recursive:true});
 for(const entry of skill.package.entries)if(fs.existsSync(path.join(root,entry.name)))throw Error('公共 Skill 名称已存在：'+entry.name+'；请在包内使用不同 name');
 const created=[],staging=path.join(privateRoot(data,skill.id),'publish');fs.mkdirSync(staging,{recursive:true});
 try{
  for(const entry of skill.package.entries)fs.cpSync(path.join(privateRoot(data,skill.id),'content',entry.path),path.join(staging,entry.name),{recursive:true});
  for(const entry of skill.package.entries){const target=path.join(root,entry.name);fs.renameSync(path.join(staging,entry.name),target);created.push(target);}
 }
 catch(error){for(const target of created)fs.rmSync(target,{recursive:true,force:true});throw error;}
 skill.package.published=true;
}
function stage(data,skills,workspace){
 const root=path.join(workspace,'dsh-home','skills'),names=[];fs.mkdirSync(root,{recursive:true});
 for(const skill of skills.filter(s=>s.package?.published)){
  verify(data,skill);
  for(const entry of skill.package.entries){
   if(names.includes(entry.name))throw Error('选中的 Skill 名称冲突：'+entry.name);
   fs.cpSync(path.join(privateRoot(data,skill.id),'content',entry.path),path.join(root,entry.name),{recursive:true});names.push(entry.name);
  }
 }
 return names;
}
module.exports={ingest,parseSkill,seal,verify,publish,stage,publicRoot,privateRoot};
