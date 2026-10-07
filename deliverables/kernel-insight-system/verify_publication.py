#!/usr/bin/env python3
"""Check the offline slide publication and its frozen evidence, without a model."""
import argparse
import hashlib
import html
import json
import pathlib
import re

HERE=pathlib.Path(__file__).resolve().parent
MANIFEST=HERE/'发布清单.json'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def files():
    return sorted(p for p in HERE.rglob('*') if p.is_file() and p!=MANIFEST
                  and '__pycache__' not in p.parts and '.git' not in p.parts
                  and not p.name.endswith('.pyc'))

def check():
    deck=(HERE/'deck.html').read_text(encoding='utf-8')
    titles=[html.unescape(t) for t in re.findall(r'data-title="([^"]+)"',deck)]
    speech=(HERE/'逐页演讲稿.md').read_text(encoding='utf-8')
    heads=[(int(n),t) for n,t in re.findall(r'^## (\d{2}) (.+)$',speech,re.M)]
    assert len(titles)==48 and heads==list(enumerate(titles,1)), 'Speech/deck page mismatch'
    assets=re.findall(r'\bsrc="([^"]+)"',deck)
    assert assets and all(not re.match(r'(?:https?:)?//',a) and (HERE/a).is_file() for a in assets), 'Missing/nonlocal slide asset'
    data=json.loads((HERE/'analysis-data.json').read_text(encoding='utf-8'))
    for key,src in data['sources'].items():
        path=(HERE/src['reportEvidence']).resolve()
        assert path.is_relative_to(HERE/'evidence') and path.is_file(), key
        assert digest(path)==src['sha256'], f'{key}: frozen source hash mismatch'
    assert (HERE/'vendor/kelip-slide/assets/deck-template.html').is_file()
    assert (HERE/'vendor/kelip-slide/LICENSE').is_file()
    assert data['aggregates']['before']['modelRequests']==21
    assert data['aggregates']['after']['modelRequests']==6
    findings=[]
    forbidden=[r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
               r'\b(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{30,})',
               r'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}',r'\bAKIA[A-Z0-9]{16}\b']
    for p in files():
        assert p.stat().st_size<50*1024*1024, f'Oversized publication file: {p.name}'
        assert p.name not in ['accounts.json','state.json','admin-key.txt','.env'], 'Runtime state in publication'
        if p.suffix.lower() in ['.md','.py','.json','.html','.svg','.csv','.txt']:
            value=p.read_text(encoding='utf-8-sig',errors='replace')
            if any(re.search(pattern,value) for pattern in forbidden): findings.append(str(p.relative_to(HERE)))
    assert not findings, f'Credential patterns require review: {findings}'
    return {'pages':len(titles),'speechPages':len(heads),'speechChineseCharacters':len(re.findall(r'[\u4e00-\u9fff]',speech)),
            'localImageReferences':len(assets),'frozenEvidenceFiles':len(data['sources']),
            'credentialPatternFindings':0,'newModelExperimentsExecuted':False,
            'websiteFunctionalAcceptanceExecuted':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write-manifest',action='store_true')
    args=parser.parse_args();checks=check()
    inventory=[{'path':p.relative_to(HERE).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in files()]
    if args.write_manifest:
        value={'schema':'kernel-insight-slide-publication/v1','date':'2026-10-07',
               'checks':checks,'files':inventory,
               'scope':'Offline deck, 48-page speech, figures, screenshots, frozen public evidence, template, scripts and QA. No private business state or large kernel artifacts.',
               'manifestSelfHashExcluded':True}
        MANIFEST.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    else:
        saved=json.loads(MANIFEST.read_text(encoding='utf-8'))
        assert saved['files']==inventory, 'Publication changed; review and regenerate the manifest'
        assert saved['checks']==checks
    print(json.dumps({'passed':True,**checks,'publicationFiles':len(inventory),'bytes':sum(x['bytes'] for x in inventory)},ensure_ascii=False))

if __name__=='__main__':main()
