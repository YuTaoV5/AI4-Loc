"""Package the 20-page briefing, both reusable skills and reproduction inputs."""
import pathlib,json,re,hashlib,zipfile
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((HERE/'source-provenance.json').read_text(encoding='utf-8'));qa=json.loads((HERE/'qa-report.json').read_text(encoding='utf-8'))
assert qa['passed'] and qa['pages']==20 and qa['deck_sha256']==digest(HERE/'deck.html')
for row in source['sources']:
 assert digest(ROOT/row['path'])==row['sha256']
 assert digest(HERE/'evidence'/row['path'])==row['sha256']
manifest=HERE/'发布清单.json';files=[]
for p in HERE.rglob('*'):
 if not p.is_file() or p==manifest or '__pycache__' in p.parts or p.suffix=='.pyc':continue
 if p.parent.name=='rendered':
  n=re.search(r'(?:slide-|page-)(\d+)',p.name)
  if n and int(n.group(1))>20:continue
  if n and ('step-' in p.name or '-final' in p.name) and int(n.group(1)) not in [4,5,6,13,16,18]:continue
 if re.fullmatch(r'diagram-\d+\.svg',p.name) and p.name not in json.loads((HERE/'active-diagrams.json').read_text()):continue
 if p.suffix=='.gif' and p.name not in [f'教学流程-{n:02d}.gif' for n in [4,5,6,13,16,18]]:continue
 files.append(p)
for d in [ROOT/'skills/ai4loc-decision-data',ROOT/'skills/ai4loc-decision-finetune']:
 files.extend(p for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
files += [ROOT/'skills/verify_decision_skills.py',ROOT/'skills/decision-skills-validation.json',ROOT/'docs/决策模型开发与微调复现指南_20261018.md']
files += [ROOT/r['path'] for r in source['sources']]
files += [p for p in (ROOT/'research/decision-skills-l40-20261018').iterdir() if p.is_file()]
ref=ROOT/'research/jev-qwen35-9b-20261016'
files += [ref/n for n in ['official-model-metadata.json','fetch-checkpoint.py','merge-adapter.py']]
files=sorted(set(files))
for p in files:
 assert p.name not in ['dataset.private.json','.env','accounts.json','state.json']
 if p.suffix in ['.py','.json','.md','.html','.svg']:
  value=p.read_text(encoding='utf-8',errors='replace')
  assert not re.search(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9_]{30,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}',value),p
inventory=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in files]
manifest.write_text(json.dumps({'edition':'experiment-story-20','date':'2026-10-18','pages':20,'active_teaching_gifs':6,'skills':2,'private_inputs_included':False,'files':inventory,'self_hash_excluded':True},ensure_ascii=False,indent=2),encoding='utf-8')
out=ROOT/'deliverables/releases/Jev_开发者实验主线20页_微调Skills与复现指南_20261018.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 z.writestr('打开说明.md','解压后打开 deliverables/jev-decision-explained/deck.html。第19页链接两份skill与复现指南。仅查看无需Python；新GPU训练按指南执行。包内包含构建所用公开输入，不含模型权重或私有日志。旧28页技术材料为归档，默认演示为20页实验主线版。')
 for p in files+[manifest]:z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for p in files+[manifest]:assert hashlib.sha256(z.read(p.relative_to(ROOT).as_posix())).hexdigest()==digest(p)
value={'file':out.name,'bytes':out.stat().st_size,'sha256':digest(out),'members':len(files)+2,'verified_each_member':True,'pages':20,'skills':2}
out.with_suffix('.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(value,ensure_ascii=False))
