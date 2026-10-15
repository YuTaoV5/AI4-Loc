"""Privately retain training adapters, raw requests/SSE and scheduler evidence.

Never include process environment or redownloadable base model weights.
Symlinked source/dependency directories are not recursively followed.
"""
import pathlib,json,hashlib,tarfile,os
E=pathlib.Path(__file__).resolve().parent
assert json.loads((E/'completion.json').read_text()).get('restored') is True
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
excluded={'original-process.private.json','lease.private.json','retained-evidence.tgz','retained-files.json','archive.json','public.tgz'}
files=[p for p in E.rglob('*') if p.is_file() and not p.is_symlink() and p.name not in excluded
       and not set(p.relative_to(E).parts)&{'public','deps','__pycache__'}]
manifest={str(p.relative_to(E)):sha(p) for p in files}
(E/'retained-files.json').write_text(json.dumps(manifest,indent=2))
with tarfile.open(E/'retained-evidence.tgz','w:gz',compresslevel=3) as tar:
    for p in files+[E/'retained-files.json']:tar.add(p,arcname=str(p.relative_to(E)),recursive=False)
os.chmod(E/'retained-evidence.tgz',0o600)
audit={'file':'retained-evidence.tgz','bytes':(E/'retained-evidence.tgz').stat().st_size,'sha256':sha(E/'retained-evidence.tgz'),
       'files_including_manifest':len(files)+1,'private_raw_inputs_included':True,
       'training_adapters_included':any(p.name.startswith('adapter-epoch') and p.suffix=='.pt' for p in files),
       'process_environment_included':False,'redownloadable_base_and_merged_weights_included':False,
       'merged_checkpoint_hash_manifest_included':(E/'trained-checkpoint-manifest.json').exists()}
(E/'archive.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit),flush=True)
