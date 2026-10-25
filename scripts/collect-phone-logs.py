"""Fetch publisher-checksummed ABRLog extracted raw-content blocks, preserving capture layout."""
import argparse,hashlib,json,pathlib,shutil,urllib.request,zipfile
URL='https://zenodo.org/api/records/21892365'
def archive_sha(file):
 with file.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def collect(root):
 root.mkdir(parents=True,exist_ok=True)
 with urllib.request.urlopen(URL,timeout=60) as r:record=json.load(r)
 f=next(x for x in record['files'] if x['key']=='ABRLog_Dataset.zip');target=root/f['key'];partial=target.with_suffix('.part')
 if not target.exists():
  if shutil.disk_usage(root).free<3*2**30:raise ValueError('Need at least 3 GiB free')
  print('Downloading '+f['key'],flush=True)
  with urllib.request.urlopen(f['links']['self'],timeout=180) as src,partial.open('wb') as dst:shutil.copyfileobj(src,dst,1024*1024)
  partial.replace(target)
 algorithm,expected=f['checksum'].split(':');h=hashlib.new(algorithm)
 with target.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 if target.stat().st_size!=f['size'] or h.hexdigest()!=expected:raise ValueError('Publisher size/checksum mismatch')
 content=root/'content';content.mkdir(exist_ok=True)
 with zipfile.ZipFile(target) as z:
  total=sum(x.file_size for x in z.infolist())
  if total>2*2**30 or len(z.infolist())>10000:raise ValueError('Unexpected extraction size')
  for member in z.infolist():
   dest=(content/member.filename).resolve()
   if not dest.is_relative_to(content.resolve()) or (member.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe ZIP member')
  z.extractall(content)
 files=[{'path':p.relative_to(content).as_posix(),'bytes':p.stat().st_size} for p in sorted(content.rglob('*')) if p.is_file()]
 provenance={'license':record.get('metadata',{}).get('license'),'source':URL,'record':'21892365','archive':f['key'],'publisherChecksum':f['checksum'],'archiveSha256':archive_sha(target),'compressedBytes':f['size'],'expandedBytes':total,'fileCount':len(files),'rootCauseLabels':False,'earlyBootCoverage':'not asserted','purpose':'Real mobile log ingestion and retrieval; excluded from accuracy denominator','files':files}
 (root/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in provenance.items() if k!='files'}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output',type=pathlib.Path);collect(p.parse_args().output)
