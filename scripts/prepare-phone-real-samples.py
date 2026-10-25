"""Package complete per-capture extracted ABRLog blocks without mixing phones or captures."""
import argparse,hashlib,json,pathlib,zipfile

def prepare(root):
 root=pathlib.Path(root);content=root/'content';provenance=json.loads((root/'provenance.json').read_text(encoding='utf-8'));groups={}
 for item in provenance['files']:
  p=pathlib.Path(item['path'])
  if p.suffix=='.txt':groups.setdefault(p.parent.as_posix(),[]).append(p)
 output=root/'samples';output.mkdir(exist_ok=True);rows=[]
 for capture,files in sorted(groups.items()):
  cid=hashlib.sha256(capture.encode()).hexdigest()[:16];target=output/(cid+'.zip');parts=pathlib.PurePosixPath(capture).parts
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
   for p in files:z.write(content/p,p.name)
   z.writestr('provenance.json',json.dumps({'synthetic':False,'source':provenance['source'],'sourceCapture':capture,'rootCauseLabels':False,'representation':'Publisher extracted blocks; no log content rewritten'},ensure_ascii=False))
  rows.append({'id':cid,'device':parts[-2] if len(parts)>1 else 'unknown','capture':parts[-1],'origin':'real-abrlog','files':len(files),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'archive':'samples/'+target.name})
 manifest={'source':provenance['source'],'rootCauseLabels':False,'cases':rows};(root/'samples.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'captures':len(rows),'compressedBytes':sum(r['bytes'] for r in rows)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=pathlib.Path);prepare(p.parse_args().root)
