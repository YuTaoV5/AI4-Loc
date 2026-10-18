"""Validate reviewed decisions and export a NEW training directory; standard library only."""
import argparse,pathlib,json,hashlib,collections,re
CLASSES=['memory_lifetime','memory_bounds','memory_leak','locking','blocked_task','watchdog_lockup','rcu_progress','oom','memory_protection','refcount','explicit_panic_or_warning','other_or_no_fault']
QUESTION='Which fault family best describes the FIRST diagnostic in the supplied kernel log?'
def sha(b):return hashlib.sha256(b).hexdigest()
def validate(rows,classes):
    if not 2<=len(classes)<=26 or len(set(classes))!=len(classes):raise ValueError('Require 2..26 distinct classes')
    groups={};seen={};ids=set();records=[];counts=collections.Counter()
    for i,r in enumerate(rows,1):
        missing=set(['id','group','source','split','input','label','evidence','reviewed_by'])-set(r)
        if missing:raise ValueError(f'row {i}: missing {sorted(missing)}')
        if any(not isinstance(r[k],str) or not r[k].strip() for k in ['id','group','source','input','label','evidence','reviewed_by']):raise ValueError(f'row {i}: nonempty strings required')
        if r['id'] in ids:raise ValueError(f'row {i}: duplicate id')
        ids.add(r['id']);s=r['split']
        if s not in ['train','dev','test'] or r['label'] not in classes:raise ValueError(f'row {i}: unknown split/label')
        if r['evidence'] not in r['input']:raise ValueError(f'row {i}: evidence must occur verbatim in input')
        sig=r['evidence'].lower()
        if re.search(r'(?:circular|recursive) locking',sig) and r['label']!='locking':raise ValueError(f'row {i}: locking evidence requires locking, not substring RCU')
        if r['label']=='rcu_progress' and not re.search(r'\brcu(?:[:_\s]|$)',sig):raise ValueError(f'row {i}: RCU evidence needs explicit token boundary')
        if re.search(r'/sys/kernel/debug/provoke-crash|KI_BENCH|\bSCENARIO\s*[=:]|echo[^\n]*(?:lkdtm|DIRECT)',r['input'],re.I):raise ValueError(f'row {i}: remove injection metadata from model input')
        if re.search(r'-----BEGIN .*PRIVATE KEY-----|\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}',r['input']):raise ValueError(f'row {i}: credential-like content')
        if r['group'] in groups and groups[r['group']]!=s:raise ValueError(f'row {i}: group crosses splits')
        groups[r['group']]=s
        norm='\n'.join(' '.join(x.split()) for x in r['input'].replace('\r\n','\n').strip().splitlines());h=sha(norm.encode())
        if h in seen:raise ValueError(f'row {i}: duplicate normalized input (including cross-split duplicates)')
        seen[h]=s;counts[s]+=1
        records.append({'case':r['id'],'group':r['group'],'source':r['source'],'split':s,'label':r['label'],'input':r['input'],'input_sha256':sha(r['input'].encode()),'normalized_input_sha256':h,'evidence':r['evidence'],'reviewed_by':r['reviewed_by']})
    if set(counts)!=set(['train','dev','test']):raise ValueError('All three splits required')
    return records,dict(counts)
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--classes',type=pathlib.Path);p.add_argument('--question',default=QUESTION);a=p.parse_args()
    if a.output.exists():raise ValueError('Output must be a NEW directory; never overwrite a frozen run')
    rows=[json.loads(x) for x in a.input.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
    classes=json.loads(a.classes.read_text(encoding='utf-8')) if a.classes else CLASSES
    records,counts=validate(rows,classes);a.output.mkdir(parents=True)
    raw=json.dumps(records,ensure_ascii=False,indent=2).encode();private=a.output/'dataset.private.json';private.write_bytes(raw)
    if hasattr(private,'chmod'):private.chmod(0o600)
    label_counts={s:dict(collections.Counter(r['label'] for r in records if r['split']==s)) for s in counts}
    # Do not duplicate log excerpts in the public metadata.
    public=[{k:v for k,v in r.items() if k not in ['input','evidence','reviewed_by']} for r in records]
    frozen={'schema':'ai4loc-reviewed-choice/v1','classes':classes,'question':a.question,'records':public,'counts':counts,'label_counts':label_counts,'private_sha256':sha(raw),'label_basis':'human-reviewed first diagnostic; reviewer/evidence retained privately'}
    (a.output/'dataset-frozen.json').write_text(json.dumps(frozen,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'passed':True,'counts':counts,'groups':len(set(r['group'] for r in records)),'group_overlap':False,'input_duplicates':False,'label_counts':label_counts,'uncovered_classes':{s:[c for c in classes if c not in label_counts[s]] for s in counts},'synthetic_examples':any(r['source']=='synthetic-format-example' for r in records)}
    (a.output/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
