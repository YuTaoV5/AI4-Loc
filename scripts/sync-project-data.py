"""Snapshot project-owned server data, resume downloads, and verify local datasets.

Credentials are prompted in memory. Archives contain private application state;
the destination must remain ignored by Git. External model stores are excluded.
"""
import argparse
import concurrent.futures
import datetime
import getpass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import sys
import tarfile
import time
import uuid

REMOTE = r'''
import datetime, hashlib, json, os, pathlib, sys, tarfile
snapshot=sys.argv[1]
lab=pathlib.Path('/root/gpufree-data/kernel-insight-lab')
service=pathlib.Path('/opt/kernel-insight')
out=lab/'backups'/('project-export-'+snapshot)
out.mkdir(mode=0o700,parents=True,exist_ok=True)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(4*1024*1024):h.update(b)
 return h.hexdigest()
manifest=out/'inventory.json'
if manifest.exists():
 print('SNAPSHOT_REUSE '+str(manifest),flush=True)
 raise SystemExit(0)
rows=[]
def pack(name,root,prefix,exclude):
 target=out/name;partial=out/(name+'.part');counts={'files':0,'logicalBytes':0}
 def select(info):
  rel=pathlib.PurePosixPath(info.name).relative_to(prefix)
  if exclude(rel):return None
  if not (info.isfile() or info.isdir() or info.issym() or info.islnk()):return None
  if info.isfile():counts['files']+=1;counts['logicalBytes']+=info.size
  return info
 print('PACK_START '+name,flush=True)
 with tarfile.open(partial,'w:gz',compresslevel=1) as archive:
  archive.add(root,arcname=prefix,filter=select)
 os.chmod(partial,0o600);partial.replace(target)
 rows.append({'name':name,'sha256':digest(target),'bytes':target.stat().st_size,**counts})
 print('PACK_COMPLETE '+json.dumps(rows[-1]),flush=True)
pack('lab.tar.gz',lab,'lab',lambda p: '__pycache__' in p.parts or (len(p.parts)>1 and p.parts[0]=='backups' and p.parts[1].startswith('project-export-')))
mutable=[service/'data/state.json',service/'data/accounts.json']
before={str(p.relative_to(service)):digest(p) for p in mutable if p.is_file()}
pack('service.tar.gz',service,'service',lambda p: bool(p.parts) and (p.parts[0] in ['app','releases','incoming','supervisor.sock'] or '__pycache__' in p.parts or 'node_modules' in p.parts or str(p) in ['data/supervisor.pid','data/npm-cache','data/diagram-cache','data/.java']))
after={str(p.relative_to(service)):digest(p) for p in mutable if p.is_file()}
if before!=after:raise RuntimeError('Application state changed during capture; retry with no active writes')
pack('release.tar.gz',(service/'app').resolve(),'release',lambda p:'node_modules' in p.parts or '__pycache__' in p.parts)
record={'schema':'kernel-project-snapshot/v1','snapshot':snapshot,'createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'lab':str(lab),'release':str((service/'app').resolve()),'archives':rows,'applicationStateHashes':after,'exclusions':['External Ollama/SGLang model weights and platform services','npm-cache, node_modules, diagram-cache, JVM cache, pid/socket files','Old release copies and incoming deployment packages','Earlier project-export archives, Python bytecode'],'consistency':'Lab artifacts are frozen; accounts/state unchanged across service capture. Live logs may have different cutoff times.'}
manifest.write_text(json.dumps(record,indent=2)+'\n');os.chmod(manifest,0o600)
print('SNAPSHOT_READY '+str(manifest),flush=True)
'''


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def validate_inventory(inventory):
    required = {'lab.tar.gz', 'service.tar.gz', 'release.tar.gz'}
    rows = inventory.get('archives', [])
    if inventory.get('schema') != 'kernel-project-snapshot/v1' or len(rows) != 3:
        raise ValueError('Unknown or incomplete snapshot inventory')
    if {row.get('name') for row in rows} != required:
        raise ValueError('Unexpected archive names')
    for row in rows:
        if type(row.get('bytes')) is not int or row['bytes'] <= 0 or not re.fullmatch('[a-f0-9]{64}', row.get('sha256', '')):
            raise ValueError('Invalid archive identity')


def validate_private_state(archive_path, expected):
    matched = {}
    with tarfile.open(archive_path, 'r:gz') as archive:
        for member in archive:
            key = member.name.removeprefix('service/')
            if key in expected:
                data = archive.extractfile(member).read()
                if hashlib.sha256(data).hexdigest() != expected[key]:
                    raise ValueError('Captured application state differs from inventory')
                json.loads(data)
                matched[key] = True
                if len(matched) == len(expected):break
    if set(matched) != set(expected):
        raise ValueError('Private application state absent from service archive')
    return matched


def extract_prefix(archive_path, prefix, destination, *, archived_only=(), skip_links=False, skip_hardlinks=False, skipped=None, contiguous=False):
    """Expand only regular data files; retain Linux-only trees in their archives."""
    marker = PurePosixPath(prefix)
    if destination.exists():
        raise FileExistsError('Refusing to overwrite dataset: ' + str(destination))
    stage = destination.with_name(destination.name + '.extracting-' + uuid.uuid4().hex)
    stage.mkdir(parents=True)
    count = 0
    found = False
    with tarfile.open(archive_path, 'r:gz') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if not name.is_relative_to(marker):
                if contiguous and found:
                    break
                continue
            found = True
            relative = name.relative_to(marker)
            if any(relative.is_relative_to(PurePosixPath(item)) for item in archived_only):
                continue
            if '..' in relative.parts or relative.is_absolute() or any(':' in part or '\\' in part for part in relative.parts):
                raise ValueError('Unsafe archive path')
            target = stage.joinpath(*relative.parts)
            if not target.resolve().is_relative_to(stage.resolve()):
                raise ValueError('Archive destination escaped staging directory')
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile() or (member.islnk() and not skip_hardlinks):
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError('Unreadable archive file')
                with source, target.open('wb') as output:
                    for block in iter(lambda: source.read(4 * 1024**2), b''):
                        output.write(block)
                count += 1
            elif (member.issym() and skip_links) or (member.islnk() and skip_hardlinks):
                if skipped is not None:skipped.append(member.name)
            else:
                raise ValueError('Dataset contains a link or special file: ' + member.name)
    if not count:
        raise ValueError('Archive prefix absent: ' + prefix)
    if destination.exists():
        raise FileExistsError('Destination appeared while extracting: ' + str(destination))
    # MoveFileEx(REPLACE_EXISTING) can reject directories on Windows drives;
    # rename to a new name preserves the no-overwrite contract.
    stage.rename(destination)
    return count


def validate_datasets(root):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/kernel-lab'))
    from dataset_contract import validate
    reports = {'stability-v1': validate(root / 'stability-v1', deep=True)}
    names = ['linux-community-v1', 'openharmony-lkdtm-lab-v1']
    if (root / 'openharmony-lkdtm-lab-v2/manifest.json').is_file():
        names.append('openharmony-lkdtm-lab-v2')
    for name in names:
        base = root / name
        manifest = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
        errors = []
        for case in manifest['cases']:
            item = (base / case['logPath']).resolve()
            if not item.is_relative_to(base.resolve()) or not item.is_file():
                errors.append(case['id'] + ': missing/escaping log')
            elif item.stat().st_size != case['bytes'] or digest(item) != case['sha256']:
                errors.append(case['id'] + ': log hash/size mismatch')
        reports[name] = {'cases': len(manifest['cases']), 'complete': not errors, 'errors': errors}
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, default=22)
    parser.add_argument('--user', default='root')
    parser.add_argument('--snapshot', required=True, help='Stable ID for resuming the same immutable export')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--local-only', action='store_true', help='Verify and expand already downloaded archives')
    parser.add_argument('--workers', type=int, default=4, choices=range(1, 5))
    parser.add_argument('--include-private', action='store_true', help='Explicitly authorize copying account and business state in service archive')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', args.snapshot):
        parser.error('Unsafe snapshot ID')
    if not args.local_only and not args.include_private:
        parser.error('Server backup includes private account/business state; explicit --include-private is required')
    project = Path(__file__).resolve().parents[1]
    target = project / 'data/server-snapshots' / args.snapshot
    target.mkdir(parents=True, exist_ok=True)
    remote = '/root/gpufree-data/kernel-insight-lab/backups/project-export-' + args.snapshot
    if not args.local_only:
        import paramiko
        client = paramiko.SSHClient()
        client.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        password = getpass.getpass('SSH password (not saved): ')
        def connect():
            client.connect(args.host, port=args.port, username=args.user, password=password,
                           look_for_keys=False, allow_agent=False, timeout=30, banner_timeout=30)
            client.get_transport().set_keepalive(20)
        connect()
        try:
            if (target / 'inventory.json').exists():
                with client.open_sftp() as sftp:
                    try:
                        with sftp.open(remote + '/inventory.json', 'rb') as stream:
                            prior_remote = stream.read()
                    except FileNotFoundError:
                        raise RuntimeError('Remote export was cleaned; use --local-only or a new snapshot ID')
                if json.loads(prior_remote) != json.loads((target / 'inventory.json').read_text(encoding='utf-8')):
                    raise ValueError('Snapshot ID already belongs to a different inventory')
            command = 'python3 - ' + shlex.quote(args.snapshot) + " <<'KI_SNAPSHOT_PY'\n" + REMOTE + '\nKI_SNAPSHOT_PY'
            _, output, error = client.exec_command(command, timeout=3600)
            channel = output.channel
            while True:
                if channel.recv_ready():
                    print(channel.recv(32768).decode('utf-8', 'replace'), end='', flush=True)
                if channel.recv_stderr_ready():
                    print(channel.recv_stderr(32768).decode('utf-8', 'replace'), end='', flush=True)
                if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                    break
                time.sleep(.2)
            if channel.recv_exit_status() != 0:
                raise RuntimeError('Remote snapshot failed; nothing marked complete')
            with client.open_sftp() as sftp:
                sftp.get(remote + '/inventory.json', str(target / 'inventory.json'))
            if args.prepare_only:
                return 0
            inventory = json.loads((target / 'inventory.json').read_text(encoding='utf-8'))
            validate_inventory(inventory)
            for item in inventory['archives']:
                final = target / item['name']
                if final.is_file() and final.stat().st_size == item['bytes'] and digest(final) == item['sha256']:
                    print('VERIFIED_REUSE ' + item['name'], flush=True)
                    continue
                partial = target / (item['name'] + '.part')
                # Independent SSH connections avoid a single slow TCP flow. Each
                # part is bounded; only a full-file SHA256 authorizes completion.
                workers = args.workers if item['bytes'] > 32*1024**2 else 1
                span = (item['bytes'] + workers - 1) // workers
                pieces = [target / (item['name'] + f'.part.{workers}.{i}') for i in range(workers)]
                if partial.exists():
                    with partial.open('rb') as prior:
                        for i, piece in enumerate(pieces):
                            available = max(0, min(span, partial.stat().st_size-i*span))
                            prior.seek(i*span)
                            if available and not piece.exists():
                                with piece.open('wb') as output:
                                    while available:
                                        block = prior.read(min(4*1024**2, available))
                                        if not block:raise EOFError('Truncated previous partial')
                                        output.write(block);available -= len(block)
                    partial.unlink()
                def download_piece(index):
                    piece=pieces[index];start=index*span;size=min(span,item['bytes']-start)
                    for attempt in range(5):
                        peer=paramiko.SSHClient();peer.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'));peer.set_missing_host_key_policy(paramiko.RejectPolicy())
                        try:
                            offset=piece.stat().st_size if piece.exists() else 0
                            if offset>size:raise ValueError('Oversized partial piece')
                            if offset==size:return
                            peer.connect(args.host,port=args.port,username=args.user,password=password,look_for_keys=False,allow_agent=False,timeout=30,banner_timeout=30)
                            peer.get_transport().set_keepalive(20)
                            with peer.get_transport().open_session(window_size=32*1024**2,max_packet_size=64*1024) as source:
                                source.settimeout(60)
                                source.exec_command('dd if='+shlex.quote(remote+'/'+item['name'])+' bs=1M iflag=skip_bytes,count_bytes skip='+str(start+offset)+' count='+str(size-offset)+' status=none')
                                last=time.monotonic()
                                with piece.open('ab',buffering=8*1024**2) as output:
                                    while offset<size:
                                        block=source.recv(min(1024**2,size-offset))
                                        if not block:raise EOFError('Premature SSH stream EOF')
                                        output.write(block);offset+=len(block)
                                        if time.monotonic()-last>15:
                                            output.flush();print(f'PART_PROGRESS {item["name"]} {index+1}/{workers} {offset}/{size}',flush=True);last=time.monotonic()
                                if source.recv_exit_status()!=0:raise OSError('Bounded archive reader failed')
                            print(f'PART_COMPLETE {item["name"]} {index+1}/{workers}',flush=True)
                            return
                        except (OSError,EOFError,paramiko.SSHException):
                            if attempt==4:raise
                            time.sleep(2)
                        finally:peer.close()
                print(f'DOWNLOAD_PARALLEL {item["name"]} workers={workers}',flush=True)
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    for future in concurrent.futures.as_completed([executor.submit(download_piece,i) for i in range(workers)]):future.result()
                with partial.open('wb') as output:
                    for piece in pieces:
                        with piece.open('rb') as source:
                            for block in iter(lambda:source.read(4*1024**2),b''):output.write(block)
                if partial.stat().st_size != item['bytes'] or digest(partial) != item['sha256']:
                    raise ValueError('Downloaded archive hash mismatch: ' + item['name'])
                partial.replace(final)
                for piece in pieces:piece.unlink()
                print('DOWNLOAD_VERIFIED ' + item['name'], flush=True)
        finally:
            password = None
            client.close()
    inventory = json.loads((target / 'inventory.json').read_text(encoding='utf-8'))
    validate_inventory(inventory)
    for item in inventory['archives']:
        path = target / item['name']
        if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise ValueError('Archive verification failed: ' + item['name'])
    datasets = project / 'data/datasets'
    mappings = [('lab.tar.gz', 'lab/datasets/stability-v1', 'stability-v1'),
                ('lab.tar.gz', 'lab/benchmark/app-format', 'openharmony-lkdtm-lab-v1'),
                ('service.tar.gz', 'service/data/backups/benchmark.linux-community-v1.20261007-130120', 'linux-community-v1')]
    with tarfile.open(target / 'release.tar.gz', 'r:gz') as archive:
        member = archive.extractfile('release/data/benchmark/manifest.json')
        version = json.load(member)['version']
    if version != 'openharmony-lkdtm-lab-v1':
        if version != 'openharmony-lkdtm-lab-v2':
            raise ValueError('Unrecognized current release dataset version: ' + version)
        mappings.append(('release.tar.gz', 'release/data/benchmark', version))
    extraction_report = target / 'extractions.json'
    extractions = json.loads(extraction_report.read_text()) if extraction_report.exists() else {}
    for archive, prefix, name in mappings:
        destination = datasets / name
        if not destination.exists():
            print('EXTRACT ' + name, flush=True)
            excluded = ('shared/source-tree',) if name == 'stability-v1' else ()
            links = []
            count = extract_prefix(target / archive, prefix, destination, archived_only=excluded, skip_links=True, skipped=links, contiguous=True)
            extractions[name] = {'files':count,'archivedOnlyTrees':list(excluded),'linksPreservedInArchive':links}
            extraction_report.write_text(json.dumps(extractions,indent=2)+'\n')
    for name in ['bootstages', 'benchmark', 'iterations', 'evidence', 'scenarios', 'dataset-audit']:
        destination = project / 'data/experiments/kernel-lab' / name
        if not destination.exists():
            print('EXTRACT_EXPERIMENT ' + name, flush=True)
            links = []
            count = extract_prefix(target / 'lab.tar.gz', 'lab/' + name, destination, skip_links=True, skip_hardlinks=True, skipped=links, contiguous=True)
            extractions['experiments/'+name] = {'files':count,'linksPreservedInArchive':links}
            extraction_report.write_text(json.dumps(extractions,indent=2)+'\n')
    reports = validate_datasets(datasets)
    private_state = validate_private_state(target / 'service.tar.gz', inventory.get('applicationStateHashes', {}))
    report = {'schema': 'kernel-local-project-data/v1', 'snapshot': args.snapshot,
              'verifiedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'archives': inventory['archives'], 'datasets': reports, 'privateStateVerified': private_state,
              'complete': all(row['complete'] for row in reports.values())}
    (target / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    sys.exit(main())
