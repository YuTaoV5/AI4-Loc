"""Audit retained requests without publishing full prompts or incident logs."""
import hashlib, json, pathlib, collections
home = pathlib.Path(__file__).resolve().parent
private = home.parents[1] / 'data/local-archive/pplx-decider-20261011'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
raw = read(private / 'results.json'); protocol = read(private / 'protocol.json')
assert raw['complete'] and len(raw['rows']) == 121
source_checks = {}
for name, expected in protocol['code'].items():
    source_checks[name] = hashlib.sha256((private / 'frozen' / name).read_bytes()).hexdigest() == expected
assert all(source_checks.values())
assert hashlib.sha256((private / 'run-benchmark.py').read_bytes()).hexdigest() == protocol['evaluatorSha256']
counts = collections.Counter(); cases = set(); diagnostics = []
for row in raw['rows']:
    workspace = private / 'workspaces' / row['workspaceId']
    trace = read(workspace / 'decision-trace.json'); assert len(trace['calls']) == 1
    call = trace['calls'][0]; request = call['request']
    assert call['status'] == 'returned' and set(request) == {'model', 'state', 'questions'}
    assert set(request['state']) == {'instruction', 'firstDiagnosticLine', 'lines', 'lifetimeEvidence', 'available'}
    counts['tracesReturned'] += 1
    # Case IDs coincide with real kernel function names in some natural logs.
    if row['caseId'] in json.dumps(request):
        counts['requestsContainingCaseNameAsLogText'] += 1; cases.add(row['caseId'])
    if row['caseId'] in ['lkdtm_LOOP', 'lkdtm_SOFTLOCKUP'] and row['arm'] == 'pplx':
        line_number = request['state']['firstDiagnosticLine']
        line = next(x for x in request['state']['lines'] if x['line'] == line_number)
        diagnostics.append({'caseId': row['caseId'], 'line': line_number, 'text': line['text'], 'frozenInjectionTarget': row['gold'], 'prediction': row['family']})
result = {'formalRequests': 121, 'counts': dict(counts), 'caseNameTextUniqueCases': len(cases),
          'frozenSourceHashesPassed': source_checks,
          'labelFieldAudit': 'No caseId, gold, injectionFamily, evaluator result or dataset path fields in actual model requests. Natural LKDTM stack symbols and workload clues remain; this is not a blinded or shortcut-free test.',
          'firstDiagnosticReview': diagnostics,
          'archive': {k: read(private / 'archive-manifest.json')[k] for k in ['bytes', 'sha256']},
          'completion': read(private / 'completion.json'), 'postcheck': read(private / 'postcheck.json')}
(home / 'results' / 'evidence-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'counts': dict(counts), 'uniqueCasesWithNaturalName': len(cases), 'frozenHashesPassed': all(source_checks.values())}))
