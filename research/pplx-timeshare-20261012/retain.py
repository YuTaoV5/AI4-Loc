"""Retain completed server evidence without private process environments or weights."""
import pathlib,json,tarfile,hashlib
E=pathlib.Path('/opt/kernel-insight/experiments/pplx-timeshare-20261012')
P=E.with_name('pplx-timeshare-20261011')
assert json.loads((E/'completion.json').read_text())['restoration']['restored']
assert json.loads((E/'results.json').read_text())['complete']
selected=[]
for folder,prefix in [(E,''),(P,'initial-attempt/')]:
 for p in sorted(folder.rglob('*')):
  rel=p.relative_to(folder)
  if not p.is_file() or p.is_symlink():continue
  if any(x.startswith('prepare-') or x in ['__pycache__','venv'] for x in rel.parts):continue
  if '.private.' in p.name or p.suffix in ['.tgz','.sha256']:continue
  if p.name in ['evidence-manifest.json','retain.py']:continue
  if p.suffix not in ['.py','.json','.log']:continue
  selected.append((p,prefix+rel.as_posix()))
manifest={name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,name in selected}
(E/'evidence-manifest.json').write_text(json.dumps(manifest,indent=2))
archive=E/'retained-evidence.tgz'
with tarfile.open(archive,'w:gz') as out:
 for p,name in selected:out.add(p,arcname=name,recursive=False)
 out.add(E/'evidence-manifest.json',arcname='evidence-manifest.json')
result={'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(selected),'excludes':'private process environments/lease, weights, venv, temporary preparation copies'}
(E/'archive.sha256').write_text(json.dumps(result,indent=2));print(json.dumps(result))
