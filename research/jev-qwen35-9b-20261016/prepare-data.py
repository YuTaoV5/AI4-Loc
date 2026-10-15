"""Freeze grouped weak supervision; model inputs never include annotation metadata.

This is first-diagnostic triage, NOT independently annotated root-cause truth.
Split by normalized injection mechanism across both kernel builds, before
permuting options. Old test groups remain test; no test-selected checkpoint.
"""
import collections,hashlib,json,pathlib,re
E=pathlib.Path(__file__).resolve().parent
STRICT=pathlib.Path('/opt/kernel-insight/data/evaluation-datasets/stability-v1')
APP=pathlib.Path('/root/gpufree-data/kernel-insight-lab/benchmark/app-format')
CLASSES=['memory_lifetime','memory_bounds','memory_leak','locking','blocked_task',
         'watchdog_lockup','rcu_progress','oom','memory_protection','refcount',
         'explicit_panic_or_warning','other_or_no_fault']
QUESTION='Which fault family best describes the FIRST diagnostic in the supplied kernel log?'
MARKER=re.compile(r'BUG: KASAN|BUG: KFENCE|BUG: unable|general protection fault|WARNING: CPU:|'
                  r'INFO: task .+blocked|(?:rcu: )?INFO: rcu_|rcu: INFO:|watchdog: BUG|'
                  r'BUG: soft lockup|BUG: hard LOCKUP|Out of memory|oom-kill:|'
                  r'possible circular locking dependency|possible recursive locking|'
                  r'BUG: sleeping function|BUG: scheduling while atomic|'
                  r'refcount_t:|[1-9][0-9]* new suspected memory leaks|'
                  r'list_(?:add|del) corruption|Kernel panic')
def sha(b):return hashlib.sha256(b).hexdigest()
def mechanism(name):
    s=name.lower().removeprefix('lkdtm_')
    # Paired read/write/near-identical variants must never cross splits.
    for pattern,replacement in [(r'(read|write)_buddy_after_free','buddy_after_free'),
        (r'(read|write)_after_free','after_free'),(r'refcount_.*','refcount'),
        (r'usercopy_.*','usercopy'),(r'exec_.*','exec_protection'),
        (r'corrupt_stack.*','corrupt_stack'),(r'stack_guard_page_.*','stack_guard'),
        (r'write_ro.*','write_ro'),(r'leak_.*','leak'),
        (r'lock_(?:spin|mutex)_abba','lock_abba'),(r'warning.*','warning')]:
        s=re.sub('^'+pattern+'$',replacement,s)
    return s
def annotation(raw,baseline=False):
    m=MARKER.search(raw)
    if not m:return ('other_or_no_fault',raw[-5000:],None) if baseline else None
    tail=raw[m.start():m.start()+1000].lower();sig=m.group().lower()
    if 'kasan' in sig or 'kfence' in sig:
        if re.search(r'use.after.free|double.free|invalid.free',tail):label='memory_lifetime'
        elif re.search(r'out.of.bounds|out.of.bound',tail):label='memory_bounds'
        else:label='memory_protection'
    elif 'unable' in sig or 'general protection' in sig:label='memory_protection'
    elif 'refcount' in sig:label='refcount'
    elif 'memory leak' in sig:label='memory_leak'
    elif 'out of memory' in sig or 'oom-kill' in sig:label='oom'
    elif 'rcu' in sig:label='rcu_progress'
    elif 'lockup' in sig:label='watchdog_lockup'
    elif 'blocked' in sig:label='blocked_task'
    elif any(x in sig for x in ['circular locking','recursive locking','sleeping function','scheduling while atomic']):label='locking'
    elif 'kernel panic' in sig and 'hung_task' in tail[:180]:label='blocked_task'
    else:label='explicit_panic_or_warning'
    start=max(0,m.start()-200)
    text=raw[start:start+5000]
    return label,text,m.group()
def sanitize(text):
    # Remove artificial injection commands/names from input; real reporter text stays.
    lines=[];removed=0
    for line in text.splitlines():
        if re.search(r'(?:echo .*?(?:lkdtm|DIRECT)|SCENARIO[=:]|KI_BENCH|ki_bench:.*(?:trigger|scenario)|/sys/kernel/debug/provoke-crash)',line,re.I):
            removed+=1;continue
        line=re.sub(r'lkdtm_[A-Z][A-Z0-9_]*','fault_trigger',line)
        line=re.sub(r'ki_(?:uaf|oob|leak|lock|sleep|spin|rcu)[a-zA-Z0-9_]*','fault_site',line)
        lines.append(line)
    return '\n'.join(lines),removed
def main():
    assert not (E/'dataset-frozen.json').exists(),'Do not overwrite frozen data'
    rows=[];excluded=[];testgroups=set();manifest=json.loads((STRICT/'manifest.json').read_text())
    for c in manifest['cases']:
        if c.get('status')!='ready':continue
        g=mechanism(c['id'])
        if c.get('split')=='test':testgroups.add(g)
        f=c['files']['agentLog'];b=(STRICT/f['path']).read_bytes();assert sha(b)==f['sha256']
        rows.append((c['id'],g,'stability',b,c.get('split'),c['id']=='baseline'))
    app=json.loads((APP/'manifest.json').read_text());app=app['cases'] if isinstance(app,dict) else app
    for c in app:
        b=(APP/c['logPath']).read_bytes();assert sha(b)==c['sha256']
        g=mechanism(c['scenario'])
        # Preserve historical holdouts in BOTH builds, at mechanism-group level.
        if c.get('split')=='test':testgroups.add(g)
        rows.append((c['id'],g,'openharmony',b,c.get('split'),c['scenario']=='baseline'))
    records=[];seen={}
    for name,g,source,b,oldsplit,baseline in rows:
        ans=annotation(b.decode('utf-8','replace'),baseline)
        if ans is None:excluded.append({'source':source,'case':name,'reason':'no recognized first-diagnostic marker'});continue
        label,text,marker=ans;text,removed=sanitize(text);digest=sha(text.encode())
        if digest in seen:
            assert seen[digest]['group']==g,'Exact input duplicate has conflicting mechanism';continue
        split='test' if g in testgroups else ('dev' if int(sha(('20261016:'+g).encode())[:8],16)%5==0 else 'train')
        r={'case':name,'group':g,'source':source,'source_sha256':sha(b),'input_sha256':digest,
           'split':split,'original_split':oldsplit,'label':label,'marker':marker,'removed_lines':removed,'input':text}
        records.append(r);seen[digest]=r
    for a in ['train','dev','test']:
        assert any(r['split']==a for r in records),a
        for b in ['train','dev','test']:
            if a==b:continue
            assert not {r['group'] for r in records if r['split']==a}&{r['group'] for r in records if r['split']==b}
            assert not {r['input_sha256'] for r in records if r['split']==a}&{r['input_sha256'] for r in records if r['split']==b}
    private=E/'dataset.private.json';private.write_text(json.dumps(records,ensure_ascii=False,indent=2));private.chmod(0o600)
    public=[{k:v for k,v in r.items() if k!='input'} for r in records]
    frozen={'schema':'ai4loc-qwen-jev-dataset/v1','classes':CLASSES,'question':QUESTION,'records':public,
      'counts':dict(collections.Counter(r['split'] for r in records)),
      'label_counts':{s:dict(collections.Counter(r['label'] for r in records if r['split']==s)) for s in ['train','dev','test']},
      'excluded':excluded,'private_sha256':sha(private.read_bytes()),
      'label_basis':'deterministic first diagnostic weak supervision, not independent expert truth',
      'leakage':'No annotation or source paths in model input; cross-kernel normalized mechanism groups disjoint; exact inputs disjoint; injection names masked. Natural diagnostic words are evidence, not removed. Prior tests have been seen by project developers; NOT a blind test.',
      'split_rule':'union of historical test mechanism groups; remaining groups sha256 seed20261016 mod5=0 dev, others train; no class balancing after viewing scores'}
    (E/'dataset-frozen.json').write_text(json.dumps(frozen,ensure_ascii=False,indent=2))
    print(json.dumps({k:frozen[k] for k in ['counts','label_counts']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
