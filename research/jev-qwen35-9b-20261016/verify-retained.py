"""Verify private archives without extracting or printing their contents."""
import pathlib,json,hashlib,tarfile
E=pathlib.Path(__file__).resolve().parent
LOCAL=E.parents[1]/'data/local-archive/jev-qwen35-9b-20261016'
results=[]
for tag in ['main','agent32k-initial','agent32k-fixed']:
    meta=json.loads((E/('archive-'+tag+'.json')).read_text())
    path=LOCAL/('retained-'+tag+'.tgz');h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    assert path.stat().st_size==meta['bytes'] and h.hexdigest()==meta['sha256'],tag
    observed={};manifest=None
    with tarfile.open(path,'r|gz') as t:
        for m in t:
            assert m.isfile() and not m.issym() and not m.islnk()
            assert not pathlib.PurePosixPath(m.name).is_absolute() and '..' not in pathlib.PurePosixPath(m.name).parts
            assert pathlib.PurePosixPath(m.name).name not in ['original-process.private.json','lease.private.json']
            f=t.extractfile(m)
            if m.name=='retained-files.json':manifest=json.load(f);continue
            hh=hashlib.sha256()
            for block in iter(lambda:f.read(1024*1024),b''):hh.update(block)
            observed[m.name]=hh.hexdigest()
    assert manifest==observed,tag
    assert len(observed)+1==meta['files_including_manifest']
    results.append({'archive':tag,'bytes':meta['bytes'],'sha256':h.hexdigest(),'verified_files':len(observed)+1,'process_environment_absent':True})
(E/'retention-verification.json').write_text(json.dumps({'archives':results,'all_verified':True},indent=2))
print(json.dumps({'archives_verified':len(results),'files_verified':sum(r['verified_files'] for r in results),'all_verified':True},indent=2))
