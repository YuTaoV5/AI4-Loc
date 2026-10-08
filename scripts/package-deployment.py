"""Package source and public fixtures only; never include local account/runtime data."""
import hashlib, io, json, pathlib, tarfile
root=pathlib.Path(__file__).resolve().parent.parent
target=root/'data/deployment/site.tar.gz'
target.parent.mkdir(parents=True,exist_ok=True)
def add(archive,file,name):
    if file.suffix=='.sh':
        content=file.read_bytes().replace(b'\r\n',b'\n')
        info=tarfile.TarInfo(name);info.size=len(content);info.mode=0o755
        archive.addfile(info,io.BytesIO(content))
    else:archive.add(file,arcname=name,recursive=False)
with tarfile.open(target,'w:gz') as archive:
    for directory in ['public','server','scripts','plugins','deployment','tools/kernel-debug','tools/kernel-lab','data/benchmark']:
        for file in (root/directory).rglob('*'):
            if file.is_file() and '__pycache__' not in file.parts and file.name!='remote-admin.py':
                name=file.relative_to(root).as_posix()
                add(archive,file,name)
    for name in ['package.json','package-lock.json','README.md','handover.md','docs/KERNEL_AGENT_DESIGN.md','docs/REMOTE_AGENT_DEPLOYMENT.md','docs/SERVER_STATUS_20261007.md','docs/CROSS_PLATFORM_DEPLOYMENT.md','docs/DEPLOYMENT_RUNBOOK.md','docs/KERNEL_TOOLKIT.md','docs/AGENT_BENCHMARK_PLATFORM.md']:
        archive.add(root/name,arcname=name)
    for file in (root/'data/toolchains/linux').glob('*'):
        if file.is_file():add(archive,file,'runtime-seed/linux/'+file.name)
    for file in (root/'data/toolchains/linux').glob('ripgrep-*/rg'):
        archive.add(file,arcname='runtime-seed/linux/rg')
print(json.dumps({'bundle':str(target),'size':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
