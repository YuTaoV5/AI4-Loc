"""Bounded, read-only evidence collection. Never execute supplied binaries/scripts.

Input is one isolated job workspace, not a shell command. Artifact paths must
resolve inside it. Artifact matching is a claim to verify, not automatic proof.
"""
import hashlib, json, pathlib, re, shutil, subprocess, sys, time
from kernel_artifacts import identity, events

SIGNALS = {
    'memory': r'KASAN|KFENCE|use-after-free|out.of.bounds|double.free|slab.*corrupt',
    'leak': r'kmemleak|unreferenced object|memory leak',
    'watchdog': r'watchdog|soft lockup|hard LOCKUP',
    'locks': r'lockdep|circular locking|held locks|spinlock|sleeping function',
    'hung': r'blocked for more than|hung.task|D state',
    'rcu': r'rcu.*stall|RCU.*stall|rcu_.*kthread',
    'oom': r'Out of memory|oom-kill|Killed process|page allocation failure',
    'exception': r'BUG:|WARNING:|Oops:|general protection fault|Kernel panic',
}
VERSION = r'Linux version|CPU:|PID:|Comm:|Tainted:|Hardware name|Build[Ii][Dd]|Kernel config SHA256|RIP:|pc :|Call Trace|Allocated by|Freed by|Read of size|Write of size'

def collect(workspace, progress=lambda *args: None):
    root = pathlib.Path(workspace).resolve()
    records, commands, gaps = [], [], []
    deadline = time.monotonic() + 40

    def tool(args, limit=18000):
        executable = shutil.which(args[0])
        if not executable:
            gaps.append('工具不可用: ' + args[0]); return ''
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            gaps.append('证据工具预算耗尽'); return ''
        started = time.monotonic()
        # Temp output is bounded on disk by killing the child once over budget.
        def limits():
            import resource
            resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
            resource.setrlimit(resource.RLIMIT_CPU,(8,8))
            resource.setrlimit(resource.RLIMIT_FSIZE,(1024**2,1024**2))
        clean_home=root/'tool-home';clean_home.mkdir(exist_ok=True)
        environment={**__import__('os').environ,'HOME':str(clean_home),'DEBUGINFOD_URLS':'','PYTHONPATH':'','PYTHONSTARTUP':''}
        process = subprocess.Popen([executable, *args[1:]], cwd=root,env=environment,stdin=subprocess.DEVNULL,
                                   preexec_fn=limits if sys.platform=='linux' else None,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        import threading
        timer = threading.Timer(min(8, remaining), process.kill)
        timer.start(); output = bytearray(); truncated = False
        try:
            while True:
                chunk = process.stdout.read(1024)
                if not chunk: break
                output.extend(chunk)
                if len(output)>limit:
                    truncated=True; process.kill(); break
            process.wait()
        finally:
            timer.cancel()
            if process.poll() is None: process.kill(); process.wait()
            process.stdout.close()
        text = bytes(output[:limit]).decode('utf-8', 'replace')
        commands.append({'id': 'T'+str(len(commands)+1), 'tool':args[0],
                         'arguments':args[1:], 'exitCode':process.returncode,
                         'truncated':truncated, 'seconds':round(time.monotonic()-started,3),
                         'output':text})
        return text

    progress('triage', '正在用 rg 提取异常族、首个故障与版本证据')
    raw = tool(['rg','--no-heading','--color','never','-n','-i','-m','64',
                '|'.join(SIGNALS.values())+'|'+VERSION, 'input.log'])
    # Original line numbers are preserved; never renumber filtered output.
    for line in raw.splitlines():
        match = re.match(r'^(\d+):(.*)', line)
        if match:
            number, text = int(match[1]), match[2][:1000]
            records.append({'line':number, 'text':text})
    families = [name for name, pattern in SIGNALS.items() if any(
        re.search(pattern, row['text'], re.I) for row in records)]
    progress('source', '正在核对精确源码上下文与故障函数')
    source_info = {'files':[], 'errors':[]}
    info = root/'source-context.json'
    if info.is_file(): source_info=json.loads(info.read_text(encoding='utf-8'))
    source_evidence=[]
    for item in source_info.get('files',[])[:6]:
        candidate=(root/'source-context'/item['file']).resolve()
        if not candidate.is_relative_to(root/'source-context') or not candidate.is_file(): continue
        digest=hashlib.sha256(candidate.read_bytes()).hexdigest()
        if digest!=item.get('sha256'):
            gaps.append('源码哈希不符: '+item['file']); continue
        source_evidence.append({**item,'verifiedDownloadHash':True})
    # Only inspect explicit path:line references, not entire trees or answer files.
    for item in source_evidence[:3]:
        refs=re.findall(re.escape(item['file'])+r':(\d+)',raw)
        if not refs: continue
        line=int(refs[0]); lines=(root/'source-context'/item['file']).read_text(encoding='utf-8').splitlines()
        item['excerpt']=[{'line':n,'text':lines[n-1][:400]} for n in range(max(1,line-4),min(len(lines),line+4)+1)]
    gaps.extend(source_info.get('errors',[]))
    if not source_evidence: gaps.append('缺少可核验的精确版本源码上下文')

    progress('symbols', '正在检查符号材料与可用的只读分析工具')
    capabilities={name:bool(shutil.which(name)) for name in ['rg','llvm-readelf','llvm-objdump','llvm-symbolizer','gdb','crash','drgn']}
    artifacts=[];dump=None;config=None
    manifest=root/'artifacts.json'
    if manifest.is_file():
        for item in json.loads(manifest.read_text(encoding='utf-8')).get('files',[])[:6]:
            file=(root/str(item.get('path',''))).resolve()
            if not file.is_relative_to(root) or not file.is_file() or file.stat().st_size>2*1024**3:
                gaps.append('拒绝越界、缺失或过大的符号文件'); continue
            if item.get('kind')=='kernelConfig':
                if file.stat().st_size>2*1024**2:gaps.append('内核配置过大');continue
                content=file.read_bytes();config={'sha256':hashlib.sha256(content).hexdigest(),'debugInfo':b'CONFIG_DEBUG_INFO=y' in content,'runtimeMatchVerified':False}
                continue
            with file.open('rb') as stream: magic=stream.read(4)
            if magic!=b'\x7fELF': gaps.append('非 ELF 符号文件: '+file.name); continue
            try:elf=identity(file)
            except (ValueError,OSError) as error:gaps.append('ELF 无效: '+str(error));continue
            if item.get('kind')=='vmcore':
                if elf['elfType']!=4:gaps.append('vmcore 必须为 ELF core dump');continue
                dump={**elf,'path':str(file.relative_to(root))};continue
            if elf['elfType'] not in (1,2,3):gaps.append('符号文件必须为 ELF executable/shared object');continue
            header=tool(['llvm-readelf','-h','-n',str(file.relative_to(root))],10000)
            build=re.search(r'Build ID:\s*([0-9a-f]+)',header,re.I)
            actual=elf.get('buildId') or (build[1].lower() if build else None)
            expected=str(item.get('expectedBuildId','')).lower()
            # A supplied expectation is not evidence it is the crashed build.
            match=bool(actual and expected and actual==expected)
            artifact={'path':str(file.relative_to(root)),'buildId':actual,'architecture':elf['architecture'],'elfType':elf['elfType'],
                      'matchesSuppliedBuildId':match,'runtimeMatchVerified':False}
            artifacts.append(artifact)
            if not match: gaps.append('Build ID 缺失或不匹配，停止该文件的地址解释'); continue
            symbol=re.search(r'\b([A-Za-z_][A-Za-z0-9_]{2,100})\+0x[0-9a-f]+/0x[0-9a-f]+',raw)
            if symbol:
                artifact['symbol']=symbol[1]
                artifact['disassembly']=tool(['llvm-objdump','-d','--disassemble-symbols='+symbol[1],str(file.relative_to(root))],7000)
            gaps.append('符号文件仅与提交者声明的 Build ID 匹配；尚未证明与崩溃运行构建一致，未转换 KASLR 地址')
    if not artifacts: gaps.append('未提供匹配 vmlinux/模块，无法验证符号化、反汇编或 vmcore 根因')
    dump_queries=[]
    if config:
        observed=re.search(r'Kernel config SHA256:\s*([a-f0-9]{64})',raw,re.I)
        expected_config=observed[1].lower() if observed else (dump or {}).get('configSha256')
        config['runtimeMatchVerified']=bool(expected_config and expected_config==config['sha256'])
        config['runtimeMismatch']=bool(expected_config and expected_config!=config['sha256'])
        if not config['runtimeMatchVerified']:gaps.append('配置 SHA256 尚未与运行日志或 VMCOREINFO 匹配')
    if dump:
        runtime_release=dump.get('kernelRelease')
        log_versions=re.findall(r'Linux version\s+(\S+)',raw)
        runtime=next((a for a in artifacts if a.get('elfType')==2 and dump.get('buildId') and a['buildId']==dump['buildId'] and a['architecture']==dump['architecture'] and a['architecture']!='unknown'),None)
        if runtime and runtime_release and runtime_release in log_versions and not (config or {}).get('runtimeMismatch'):
            runtime['matchesVmcoreBuild']=True
            gaps.append('符号与所提交转储的构建标识一致；转储来源仍需人工确认，不能据此证明根因')
            sections=tool(['llvm-readelf','--wide','-S',runtime['path']],18000)
            if not sections or any(s in sections for s in ['.debug_gdb_scripts','.gnu_debuglink','.gnu_debugaltlink','.debug_sup','.gnu_debugdata']) or commands[-1]['truncated'] or commands[-1]['exitCode']!=0:
                gaps.append('无法安全核对 ELF 调试节，停止转储查询')
            else:
                progress('dump','构建标识匹配，执行固定转储摘要与任务查询')
                script=root/'crash-queries.txt';script.write_text('sys\nbt\nquit\n',encoding='ascii')
                for args in [['crash','--no_crashrc','--no_scroll','-s','-i',str(script),runtime['path'],dump['path']],
                             [sys.executable,str(pathlib.Path(__file__).with_name('dump-query.py')),str(root/dump['path']),str(root/runtime['path'])]]:
                    output=tool(args,12000);dump_queries.append({'tool':args[0],'output':output})
        else:gaps.append('vmcore 与 vmlinux 的 Build ID、架构、日志内核版本缺失/不匹配，或配置哈希不一致，停止 crash/drgn 查询')
    else:gaps.append('未提供 ELF vmcore，未执行 crash/drgn 内存检查')
    grouped=events(root/'input.log')
    document={'schemaVersion':2,**grouped,'families':families,'logEvidence':records,
              'sourceEvidence':source_evidence,'artifacts':artifacts,
              'capabilities':capabilities,'commands':commands,'gaps':list(dict.fromkeys(gaps)),
              'vmcore':dump,'kernelConfig':config,'dumpQueries':dump_queries,
              'rootCauseVerified':False}
    (root/'evidence.json').write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8')
    brief=['Families (hints): '+','.join(families), 'Events (boundaries, not proven independent causes): '+json.dumps(grouped,ensure_ascii=False)[:1800], 'Verification gaps: '+json.dumps(document['gaps'],ensure_ascii=False)[:1400]]
    for row in records[:24]: brief.append('input.log:L%d %s'%(row['line'],row['text'][:240]))
    for item in source_evidence[:2]:
        brief.append('SOURCE '+item['file']+' revision='+item['revision']+' sha256='+item['sha256'])
        for row in item.get('excerpt',[])[:5]: brief.append('SOURCE:L%d %s'%(row['line'],row['text'][:160]))
    for command in commands: brief.append('TOOL '+command['id']+' '+command['tool']+' exit='+str(command['exitCode'])+' truncated='+str(command['truncated']))
    (root/'evidence-brief.txt').write_text('\n'.join(brief)[:9000],encoding='utf-8')
    progress('hypotheses', '证据收集完成，模型正在比较根因假设与验证条件')
    return document

if __name__=='__main__':
    collect(sys.argv[1],lambda phase,message: print(json.dumps({'phase':phase,'message':message},ensure_ascii=False),flush=True))
