"""Recheck complete cached checkpoint against independent pinned official metadata."""
import argparse,hashlib,json,pathlib,time
p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=pathlib.Path,required=True);p.add_argument('--metadata',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();start=time.monotonic()
manifest=json.loads((a.checkpoint/'verified-checkpoint.json').read_text());official=json.loads(a.metadata.read_text());revision='b01a5cbaca5391f73bd55103d4f27e8982cd5e60'
assert manifest['revision']==official['sha']==revision and manifest['model']==official['id']=='perplexity-ai/pplx-decider-v1-27b'
index={f['rfilename']:f for f in official['siblings']};files=[]
assert len(manifest['files'])==30
for f in manifest['files']:
 path=a.checkpoint/f['name'];info=index[f['name']];expected=(info.get('lfs') or {}).get('sha256') or info['blobId'];assert path.stat().st_size==info['size']==f['bytes']
 h=hashlib.sha256() if info.get('lfs') else hashlib.sha1()
 if not info.get('lfs'):h.update(f'blob {path.stat().st_size}\0'.encode())
 with path.open('rb') as source:
  for b in iter(lambda:source.read(8*1024**2),b''):h.update(b)
 assert h.hexdigest()==expected==f['officialDigest'],f['name'];files.append({'name':f['name'],'verified':True})
result={'model':official['id'],'revision':revision,'complete':True,'files':files,'seconds':time.monotonic()-start};a.output.write_text(json.dumps(result,indent=2));print(json.dumps({'complete':True,'files':len(files),'seconds':result['seconds']}))
