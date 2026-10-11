"""Archive only experiment evidence, excluding runtime, caches and model weights."""
import hashlib, json, pathlib, tarfile, urllib.request, subprocess, time
base = pathlib.Path('/opt/kernel-insight/experiments/pplx-decider-20261011')
assert json.loads((base / 'completion.json').read_text())['status'] == 'completed'
assert json.loads((base / 'results.json').read_text())['complete']
health = {}
for port, path in [(30000, '/v1/models'), (8787, '/api/health'), (30002, '/health')]:
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=10) as response:
            health[str(port)] = {'status': response.status, 'body': json.load(response)}
    except Exception as error:
        health[str(port)] = {'error': type(error).__name__}
checks = {'checkedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'services': health,
          'gpu': subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.used,memory.total', '--format=csv,noheader'], text=True).strip(),
          'productionPid65Exists': pathlib.Path('/proc/65').exists(),
          'checkpointDisk': subprocess.check_output(['df', '-h', '/root/gpufree-data'], text=True).strip()}
(base / 'postcheck.json').write_text(json.dumps(checks, indent=2))
archive = base / 'retained-evidence.tgz'
included = []
with tarfile.open(archive, 'w:gz') as output:
    for path in sorted(base.rglob('*')):
        relative = path.relative_to(base)
        if not path.is_file() or path.is_symlink(): continue
        if any(part in ['reference-venv', '__pycache__', 'prepare-input'] for part in relative.parts): continue
        if path.suffix == '.pyc' or path.name in ['retained-evidence.tgz', 'archive-manifest.json']: continue
        output.add(path, arcname=str(relative), recursive=False)
        included.append({'path': str(relative), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
manifest = {'archive': archive.name, 'bytes': archive.stat().st_size,
            'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'files': included}
(base / 'archive-manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps({'bytes': manifest['bytes'], 'sha256': manifest['sha256'], 'fileCount': len(included), 'postcheck': checks}))
