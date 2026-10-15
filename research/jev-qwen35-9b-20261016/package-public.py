"""Server-side root allowlist + already-audited endpoint exports."""
import pathlib,json,tarfile,hashlib,shutil,os
E=pathlib.Path(__file__).resolve().parent;P=E/'public-root';P.mkdir(exist_ok=False)
names=['dataset-frozen.json','official-model-metadata.json','training-protocol.json','training-environment.json',
       'training-complete.json','training-steps.jsonl','merge-validation.json','trained-checkpoint-manifest.json',
       'completion.json','restoration.json','provenance.json','untrained-dev.json','untrained-test.json',
       'epoch0-dev.json','epoch1-dev.json','epoch2-dev.json','selected-dev.json','selected-test.json','merged-dev.json']
for n in names:shutil.copy2(E/n,P/n)
first=E.with_name('jev-qwen35-9b-20261016')
for name in ['weight-reclamation.json','pplx-recovery-metadata.json'] :shutil.copy2(first/name,P/name)
(P/'initial-failure').mkdir()
for name in ['completion.json','restoration.json','training.log']:shutil.copy2(first/name,P/'initial-failure'/name)
shutil.copy2('/root/gpufree-data/systemone/models/Qwen3.5-9B/verified-checkpoint.json',P/'verified-base-checkpoint.json')
source={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in E.glob('*.py')}
(P/'export-source-provenance.json').write_text(json.dumps({'source_sha256':source,'purpose':'current postprocessing source snapshot; training-start code hashes separately in provenance.json'},indent=2))
manifest={str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in P.rglob('*') if p.is_file()}
(P/'PUBLIC_ROOT_SHA256.json').write_text(json.dumps(manifest,indent=2))
with tarfile.open(E/'root-public.tgz','w:gz') as t:t.add(P,arcname='.')
print('PUBLIC_ROOT_READY',len(manifest),flush=True)
