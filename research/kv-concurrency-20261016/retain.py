"""Retain raw experiment evidence privately, excluding captured process env."""
import pathlib,json,hashlib,tarfile,os
E=pathlib.Path(__file__).resolve().parent
assert json.load(open(E/'completion.json'))=={'status':'completed','restored':True}
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
excluded={'original-process.private.json','lease.private.json','retained-evidence.tgz','retained-files.json','archive.json','public.tgz'}
files=[p for p in E.rglob('*') if p.is_file() and p.name not in excluded and 'public' not in p.relative_to(E).parts and '__pycache__' not in p.relative_to(E).parts]
manifest={str(p.relative_to(E)):sha(p) for p in files}
(E/'retained-files.json').write_text(json.dumps(manifest,indent=2))
with tarfile.open(E/'retained-evidence.tgz','w:gz',compresslevel=3) as tar:
    for p in files+[E/'retained-files.json']:tar.add(p,arcname=str(p.relative_to(E)),recursive=False)
os.chmod(E/'retained-evidence.tgz',0o600)
x={'file':'retained-evidence.tgz','bytes':(E/'retained-evidence.tgz').stat().st_size,'sha256':sha(E/'retained-evidence.tgz'),
   'files_including_manifest':len(files)+1,'raw_prompts_and_logs_private':True,'captured_process_environment_included':False}
(E/'archive.json').write_text(json.dumps(x,indent=2));print(json.dumps(x))
