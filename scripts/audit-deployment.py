"""Inventory local disk and compare public release files; optionally inspect SSH read-only."""
import argparse, collections, datetime, getpass, hashlib, json, os, pathlib, stat, tarfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

def local_inventory():
    totals = collections.defaultdict(lambda: {'bytes': 0, 'files': 0})
    largest = []
    def walk(directory):
        with os.scandir(directory) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT if hasattr(info, 'st_file_attributes') else entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    walk(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    rel = pathlib.Path(entry.path).relative_to(ROOT)
                    key = '/'.join(rel.parts[:2]) if rel.parts[0] == 'data' else rel.parts[0]
                    totals[key]['bytes'] += info.st_size
                    totals[key]['files'] += 1
                    largest.append((info.st_size, rel.as_posix()))
    walk(ROOT)
    return {'logicalBytes': sum(v['bytes'] for v in totals.values()),
            'groups': dict(sorted(totals.items(), key=lambda x: -x[1]['bytes'])),
            'largestFiles': [{'path': p, 'bytes': n} for n, p in sorted(largest, reverse=True)[:20]],
            'note': 'Logical file bytes; reparse points excluded. Not physical NTFS allocation.'}

def compare(files):
    missing, changed, relocated, same = [], [], [], 0
    for name, digest in files.items():
        file = ROOT / name
        if not file.is_file():
            alternate = ROOT / 'data/datasets/openharmony-lkdtm-lab-v2' / pathlib.PurePosixPath(name).name
            if name.startswith('data/benchmark/') and alternate.is_file() and hashlib.sha256(alternate.read_bytes()).hexdigest() == digest:
                relocated.append(name)
            else: missing.append(name)
        elif hashlib.sha256(file.read_bytes()).hexdigest() != digest: changed.append(name)
        else: same += 1
    return {'files': len(files), 'identical': same, 'changed': changed, 'relocatedIdentical': relocated, 'missing': missing}

def snapshot_compare():
    file = ROOT / 'data/server-snapshots/20261007-full/release.tar.gz'
    hashes = {}
    with tarfile.open(file) as archive:
        for item in archive:
            rel = pathlib.PurePosixPath(item.name).relative_to('release')
            if item.isfile(): hashes[str(rel)] = hashlib.sha256(archive.extractfile(item).read()).hexdigest()
    return compare(hashes)

REMOTE = r'''
import pathlib,hashlib,json,shutil,subprocess
root=pathlib.Path('/opt/kernel-insight/app').resolve()
hashes={}
for base in ['server','public','scripts','tools/kernel-debug']:
 for p in (root/base).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts: hashes[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['package.json','package-lock.json']:
 p=root/name
 if p.is_file():hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
tools={n:shutil.which(n) for n in ['node','python3','bwrap','rg','git','gdb','crash','qemu-system-x86_64','llvm-symbolizer','java','dot']}
status=subprocess.run(['/opt/kernel-insight/runtime/venv/bin/supervisorctl','-c','/opt/kernel-insight/supervisord.conf','status'],capture_output=True,text=True,timeout=15)
print(json.dumps({'release':str(root),'hashes':hashes,'toolsOnLoginPath':tools,'supervisor':status.stdout.strip()}))
'''

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--remote', action='store_true')
    args = parser.parse_args()
    report = {'capturedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'local': local_inventory(), 'archivedReleaseComparison': snapshot_compare()}
    if args.remote:
        import paramiko
        client = paramiko.SSHClient()
        client.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect('120.209.70.195', port=30113, username='root', password=getpass.getpass('SSH password: '),
                       look_for_keys=False, allow_agent=False, timeout=30)
        try:
            import shlex
            _, out, err = client.exec_command('python3 -c ' + shlex.quote(REMOTE), timeout=60)
            data = json.loads(out.read().decode())
            hashes = data.pop('hashes')
            report['remote'] = {**data, 'publicRuntimeComparison': compare(hashes)}
        finally: client.close()
    target = ROOT / 'docs/deployment-audit-20261007.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
