"""Fetch public checkpoint files and verify against separately obtained official metadata."""
import argparse,pathlib,json,hashlib,urllib.request,urllib.parse,concurrent.futures,time,threading,shutil
p=argparse.ArgumentParser();p.add_argument('--metadata',type=pathlib.Path,required=True);p.add_argument('--destination',type=pathlib.Path,required=True);p.add_argument('--endpoint',default='https://hf-mirror.com');p.add_argument('--workers',type=int,default=3);a=p.parse_args()
d=json.loads(a.metadata.read_text(encoding='utf-8'));assert d['id']=='Qwen/Qwen3.5-9B';revision=d['sha'];a.destination.mkdir(parents=True,exist_ok=True)
files=[f for f in d["siblings"] if f["rfilename"]!=".gitattributes"]
assert len([f for f in files if f["rfilename"].endswith(".safetensors")])==4
lock=threading.Lock();started=time.monotonic();progress={};verified=[]
def digest(path,info):
 h=hashlib.sha256() if info.get('lfs') else hashlib.sha1()
 if not info.get('lfs'):h.update(f'blob {path.stat().st_size}\0'.encode())
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def fetch(info):
 name=info['rfilename'];dest=a.destination/name;dest.parent.mkdir(parents=True,exist_ok=True);size=info['size'];expected=(info.get('lfs') or {}).get('sha256') or info['blobId'];part=dest.with_name(dest.name+'.part')
 if dest.exists():
  assert dest.stat().st_size==size and digest(dest,info)==expected,name
 else:
  for attempt in range(5):
   have=part.stat().st_size if part.exists() else 0
   if have==size:break
   assert have<size,name
   headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'identity'}
   if have:headers['Range']=f'bytes={have}-'
   url=a.endpoint.rstrip('/')+'/'+d['id']+'/resolve/'+revision+'/'+urllib.parse.quote(name,safe='/')+'?download=true'
   try:
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=45) as r:
     if have:assert r.status==206 and r.headers.get('Content-Range','').startswith(f'bytes {have}-'),name
     with part.open('ab' if have else 'wb') as f:
      last=time.monotonic()
      while True:
       b=r.read(4*1024*1024)
       if not b:break
       f.write(b);have+=len(b)
       with lock:progress[name]=have
       if time.monotonic()-last>30:
        print(json.dumps({'file':name,'bytes':have,'total':size,'elapsed':round(time.monotonic()-started)}),flush=True);last=time.monotonic()
    if have==size:break
   except Exception as e:
    print(json.dumps({'file':name,'attempt':attempt+1,'errorType':type(e).__name__,'bytes':have}),flush=True)
    if attempt==4:raise
    time.sleep(2)
  assert part.stat().st_size==size and digest(part,info)==expected,name
  part.replace(dest)
 with lock:verified.append({'name':name,'bytes':size,'officialDigest':expected,'algorithm':'sha256' if info.get('lfs') else 'git-blob-sha1'})
 print(json.dumps({'verified':name,'bytes':size,'completedFiles':len(verified),'totalFiles':len(files)}),flush=True)
required=sum(f['size'] for f in files if not (a.destination/f['rfilename']).exists())
assert shutil.disk_usage(a.destination).free>required+2*1024**3,'Insufficient disk headroom'
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:list(pool.map(fetch,files))
(a.destination/'verified-checkpoint.json').write_text(json.dumps({'model':d['id'],'revision':revision,'files':sorted(verified,key=lambda x:x['name']),'complete':True,'seconds':time.monotonic()-started},indent=2),encoding='utf-8')
print('CHECKPOINT_VERIFIED',revision,flush=True)
