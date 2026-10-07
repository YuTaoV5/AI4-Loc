"""Portable dataset integrity contract; evaluator labels never enter input views."""
import hashlib, itertools, json, pathlib, re

SCHEMA='kernel-stability-dataset/v1'
INPUTS=('log','artifacts','source')
PROFILES={'+'.join(s):list(s) for n in (3,2,1) for s in itertools.combinations(INPUTS,n)}
REQUIRED_FAMILIES={'memory_oob','memory_uaf','memory_leak','lock_order','atomic_sleep','hung_task','watchdog','rcu_stall','oom'}

def sha256(file):
    h=hashlib.sha256()
    with pathlib.Path(file).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def record(root,file):
    root=pathlib.Path(root).resolve();file=pathlib.Path(file).resolve()
    if not file.is_relative_to(root) or not file.is_file():raise ValueError('Dataset path escapes root or is not a file')
    return {'path':file.relative_to(root).as_posix(),'sha256':sha256(file),'bytes':file.stat().st_size}

def resolve(root,item):
    p=(pathlib.Path(root)/item['path']).resolve()
    if not p.is_relative_to(pathlib.Path(root).resolve()) or not p.is_file():raise ValueError('Missing/escaping dataset file: '+item['path'])
    return p

def agent_log(raw):
    """Keep the raw bytes separately; derived log keeps original line numbering."""
    output=[];notes=False
    for line in raw.decode('utf-8','replace').splitlines(keepends=True):
        if 'KI_RUNTIME_NOTES_BEGIN' in line:notes=True
        hide=notes or 'KI_' in line or 'lkdtm: Performing direct entry' in line or re.search(r'ki_bench: (?:trigger action=|(?:leak_|oob_|uaf_|mutex_abba|spin_abba|recursive_spin|sleep_atomic|rcu_stall).*:)',line)
        if 'KI_RUNTIME_NOTES_END' in line:notes=False
        if hide:line='[collector metadata withheld]\n'
        line=re.sub(r'ki\.(scn|act)=\S+',r'ki.\1=<withheld>',line)
        output.append(line)
    return ''.join(output).encode('utf-8')

def validate(root,deep=True):
    root=pathlib.Path(root);m=json.loads((root/'manifest.json').read_text());errors=[];checked=set()
    if m.get('schema')!=SCHEMA:errors.append('Unknown schema')
    def check(item):
        try:
            p=resolve(root,item)
            if p.stat().st_size!=item['bytes']:raise ValueError('Size mismatch: '+item['path'])
            if deep and item['path'] not in checked and sha256(p)!=item['sha256']:raise ValueError('Hash mismatch: '+item['path'])
            checked.add(item['path'])
        except (OSError,ValueError,KeyError) as e:errors.append(str(e))
    for item in m.get('shared',{}).values():check(item)
    ready=[];families=set();groups={};ids=set()
    for case in m.get('cases',[]):
        if case['id'] in ids:errors.append('Duplicate case id')
        ids.add(case['id'])
        for item in case.get('files',{}).values():check(item)
        if case.get('status')!='ready':continue
        ready.append(case);families.add(case['family'])
        splits=groups.setdefault(case['mechanismGroup'],set());splits.add(case['split'])
        if len(splits)>1:errors.append('Mechanism group leaks across train/test: '+case['mechanismGroup'])
        try:
            run=json.loads(resolve(root,case['files']['run']).read_text());label=json.loads(resolve(root,case['files']['groundTruth']).read_text())
            raw=resolve(root,case['files']['rawLog']).read_bytes();text=raw.decode('utf-8','replace')
            if run.get('returnCode') is None or run.get('timedOut'):errors.append(case['id']+': missing exit record or timeout')
            if not run.get('networkDisabled') or not run.get('noHostSharing'):errors.append(case['id']+': guest isolation not recorded')
            cmd=run.get('command',[])
            if '-nic' not in cmd or cmd[cmd.index('-nic')+1]!='none' or any(x in cmd for x in ['-virtfs','-fsdev','-drive','-hda','-hdb']):errors.append(case['id']+': actual QEMU command violates collection isolation')
            if run.get('runtimeBuildId')!=m['build']['buildId']:errors.append(case['id']+': runtime Build ID mismatch')
            if run.get('runtimeRelease')!=m['build']['release']:errors.append(case['id']+': runtime release mismatch')
            if label.get('status')!='evidence_verified' or not label.get('rootCause') or not label.get('rootLocation'):errors.append(case['id']+': incomplete ground truth')
            location=label['rootLocation'];source=resolve(root,case['files']['causalSource']).read_text().splitlines()
            if location['startLine']<1 or location['endLine']>len(source) or location['endLine']<location['startLine']:errors.append(case['id']+': invalid source range')
            evidence=label.get('diagnosticEvidence',[])
            if case['family']!='healthy' and not evidence:errors.append(case['id']+': no diagnostic evidence')
            lines=text.splitlines()
            for e in evidence:
                if e['line']<1 or e['line']>len(lines) or lines[e['line']-1]!=e['text']:errors.append(case['id']+': invalid evidence line')
            if resolve(root,case['files']['agentLog']).read_bytes()!=agent_log(raw):errors.append(case['id']+': derived log mismatch')
        except (OSError,ValueError,KeyError,IndexError) as e:errors.append(case['id']+': '+str(e))
    missing=sorted(REQUIRED_FAMILIES-families)
    if missing:errors.append('Missing required fault families: '+','.join(missing))
    if 'healthy' not in families:errors.append('Missing healthy baseline')
    if len(ready)<51:errors.append('Fewer than 50 fault cases plus a healthy baseline')
    for required in ['vmlinux','bzImage','config','module','sourceArchive','sourcePatch','compiler','buildLog','collector','guestInit','qemuVersion','systemMap']:
        if required not in m.get('shared',{}):errors.append('Missing build/provenance artifact: '+required)
    return {'schema':SCHEMA,'complete':not errors,'cases':len(m.get('cases',[])),'readyCases':len(ready),'faultCases':sum(c['family']!='healthy' for c in ready),'families':sorted(families),'missingFamilies':missing,'checkedFiles':len(checked),'errors':errors}

def export_view(root,case_id,profile,destination):
    import shutil
    root=pathlib.Path(root);destination=pathlib.Path(destination)
    if profile not in PROFILES:raise ValueError('Unknown input profile')
    m=json.loads((root/'manifest.json').read_text());case=next(c for c in m['cases'] if c['id']==case_id and c['status']=='ready')
    destination.mkdir(parents=True,exist_ok=False);selected=PROFILES[profile];inputs={}
    if 'log' in selected:
        shutil.copy2(resolve(root,case['files']['agentLog']),destination/'input.log');inputs['log']='input.log'
    if 'source' in selected:
        shutil.copy2(resolve(root,m['shared']['sourceArchive']),destination/'source.tar.gz');inputs['source']='source.tar.gz'
    if 'artifacts' in selected:
        files=[]
        for key in ['vmlinux','module','config','systemMap']:
            item=m['shared'][key];name=pathlib.PurePosixPath(item['path']).name;shutil.copy2(resolve(root,item),destination/name);files.append({'path':name,'sha256':item['sha256'],'kind':key})
        (destination/'artifacts.json').write_text(json.dumps({'files':files,'runtimeBuildId':m['build']['buildId'],'runtimeIdentityBasis':'raw guest GNU notes matched frozen ELF by dataset validator'}),encoding='utf-8');inputs['artifacts']='artifacts.json'
    # No scenario name, category, causal slice, annotation or injection command.
    (destination/'inputs.json').write_text(json.dumps({'schema':'kernel-agent-input/v1','inputs':inputs,'missingInputs':[x for x in INPUTS if x not in selected]}),encoding='utf-8')
