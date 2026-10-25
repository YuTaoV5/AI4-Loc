"""Read-only bounded phone-log inventory. Hints are not identity or fault conclusions."""
import argparse,json,pathlib,re
LIMIT=256*1024
PROPERTIES={'ro.product.model','ro.product.device','ro.product.brand','ro.hardware','ro.soc.model','ro.build.display.id','ro.build.version.release','ro.build.version.sdk'}
PATTERNS={'xloader':r'\bxloader\b','bl2':r'\bBL2\b','bl31':r'\bBL31\b','uefi':r'\bUEFI\b','kernel':r'Linux version|\bufshcd\b|\bKASAN\b|Kernel panic','android':r'\blogcat\b|\bzygote\b|\bsystem_server\b','harmony':r'\bHarmonyOS\b|\bHiLog\b'}

def inventory(root):
 root=pathlib.Path(root).resolve()
 if not root.is_dir():raise ValueError('Input content directory is unavailable')
 rows=[];properties=[];hints=set();skipped=0
 for p in sorted(root.rglob('*')):
  if p.is_symlink():skipped+=1;continue
  if not p.is_file():continue
  if len(rows)>=500:skipped+=1;continue
  # Recheck every parent: never follow an incident symlink outside the evidence root.
  if not p.resolve().is_relative_to(root) or any(parent.is_symlink() for parent in p.parents if parent!=root):skipped+=1;continue
  size=p.stat().st_size
  with p.open('rb') as stream:sample=stream.read(LIMIT)
  relative=p.relative_to(root).as_posix();status='empty' if not size else 'text'
  try:text=sample.decode('utf-8-sig')
  except UnicodeDecodeError:text='';status='opaque'
  if '\x00' in text:text='';status='opaque'
  local=[stage for stage,pattern in PATTERNS.items() if re.search(pattern,text,re.I)]
  hints.update(local)
  lines=text.splitlines()
  if size and len(lines)<=8 and re.search(r'Permission denied|Operation not permitted|failed to read|can.t open|command not found',text,re.I):status='capture-command-failed'
  rows.append({'file':relative,'bytes':size,'sampledBytes':len(sample),'sampleTruncated':size>LIMIT,'status':status,'stageHints':local})
  if status=='text':
   for number,line in enumerate(lines,1):
    m=re.fullmatch(r'\s*\[([^\]]+)\]:\s*\[([^\]]*)\]\s*',line)
    if m and m[1] in PROPERTIES:properties.append({'key':m[1],'value':m[2][:200],'file':relative,'line':number,'quote':line[:500]})
 return {'schema':'kirin-log-inventory/v1','warning':'Bounded sampling and keyword hints only; verify identity, stage and cause against actual evidence.','maxSampleBytesPerFile':LIMIT,'files':rows,'skippedEntries':skipped,'stageHints':sorted(hints),'observedProperties':properties}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path);a=p.parse_args();value=json.dumps(inventory(a.root),ensure_ascii=False,indent=2)
 if a.output:
  if a.output.resolve().is_relative_to(a.root.resolve()):raise ValueError('Output must be outside read-only evidence')
  a.output.write_text(value+'\n',encoding='utf-8')
 else:print(value)
