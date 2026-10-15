"""Remove only fixed-revision, hash-verified, inactive PPLX weight shards.

Run after explicit authorization. Keep tokenizer/config/code and recovery metadata.
Never touch production Qwen weights, datasets, checkpoints or experiment records.
"""
import hashlib,json,pathlib,socket,time
E=pathlib.Path(__file__).resolve().parent
root=pathlib.Path('/root/gpufree-data/systemone/models/PPLX-Decider-v1-27B').resolve()
assert str(root)=='/root/gpufree-data/systemone/models/PPLX-Decider-v1-27B'
with socket.socket() as s:assert s.connect_ex(('127.0.0.1',30002))!=0,'PPLX service active'
for p in pathlib.Path('/proc').iterdir():
    if not p.name.isdigit():continue
    for name in ['maps','cmdline']:
        try:assert str(root).encode() not in (p/name).read_bytes(),f'In use: {p}/{name}'
        except (FileNotFoundError,PermissionError,ProcessLookupError):pass
    try:
        for fd in (p/'fd').iterdir():
            try:assert not str(fd.resolve()).startswith(str(root)+'/'),f'Open weight: {fd}'
            except (FileNotFoundError,PermissionError):pass
    except (FileNotFoundError,PermissionError,ProcessLookupError):pass
meta=json.loads((E/'pplx-recovery-metadata.json').read_text())
assert meta['id']=='perplexity-ai/pplx-decider-v1-27b'
assert meta['sha']=='b01a5cbaca5391f73bd55103d4f27e8982cd5e60'
records=[]
for f in meta['siblings']:
    name=f['rfilename']
    if not(name.startswith('model-') and name.endswith('.safetensors')):continue
    p=(root/name).resolve();assert p.parent==root and p.is_file() and not p.is_symlink()
    assert p.stat().st_size==f['size']
    h=hashlib.sha256()
    with p.open('rb') as src:
        for b in iter(lambda:src.read(16*1024*1024),b''):h.update(b)
    assert h.hexdigest()==f['lfs']['sha256'],name
    records.append({'file':str(p),'bytes':f['size'],'sha256':h.hexdigest()})
assert len(records)==11
audit={'revision':meta['sha'],'recovery_repository':meta['id'],'files':records,
       'authorization':'User explicitly allowed deleting unnecessary redownloadable weights',
       'checked_inactive':True,'timestamp_ns':time.time_ns(),'deleted':False}
(E/'weight-reclamation.json').write_text(json.dumps(audit,indent=2))
for r in records:pathlib.Path(r['file']).unlink()
audit['deleted']=True
(E/'weight-reclamation.json').write_text(json.dumps(audit,indent=2))
verified=root/'verified-checkpoint.json'
if verified.exists():
    historical=root/'verified-checkpoint.historical-before-reclamation.json'
    assert not historical.exists()
    verified.rename(historical)
verified.write_text(json.dumps({'complete':False,'state':'weight_shards_removed_by_authorized_reclamation',
                              'revision':meta['sha'],'recovery_repository':meta['id'],
                              'reclamation_manifest':str(E/'weight-reclamation.json')},indent=2))
print('RECLAIMED_BYTES',sum(r['bytes'] for r in records),flush=True)
