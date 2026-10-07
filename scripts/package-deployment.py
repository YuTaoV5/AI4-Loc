"""Package source and public fixtures only; never include local account/runtime data."""
import hashlib, json, pathlib, tarfile
root=pathlib.Path(__file__).resolve().parent.parent
target=root/'data/deployment/site.tar.gz'
target.parent.mkdir(parents=True,exist_ok=True)
with tarfile.open(target,'w:gz') as archive:
    for directory in ['public','server','scripts','tools/kernel-debug','data/benchmark']:
        for file in (root/directory).rglob('*'):
            if file.is_file() and '__pycache__' not in file.parts and file.name!='remote-admin.py':
                archive.add(file,arcname=str(file.relative_to(root)).replace('\\','/'),recursive=False)
    for name in ['package.json','package-lock.json','README.md','handover.md','docs/KERNEL_AGENT_DESIGN.md','docs/REMOTE_AGENT_DEPLOYMENT.md','docs/SERVER_STATUS_20261007.md']:
        archive.add(root/name,arcname=name)
    for file in (root/'data/toolchains/linux').glob('*'):
        if file.is_file():archive.add(file,arcname='runtime-seed/linux/'+file.name)
    for file in (root/'data/toolchains/linux').glob('ripgrep-*/rg'):
        archive.add(file,arcname='runtime-seed/linux/rg')
print(json.dumps({'bundle':str(target),'size':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
