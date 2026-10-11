"""Offline independent checks of public trial accounting and finite distributions."""
import collections, hashlib, json, math, pathlib
from scipy.stats import binomtest

root = pathlib.Path(__file__).resolve().parent
read = lambda n: json.loads((root / 'results' / n).read_text(encoding='utf-8'))
rows, protocol, stats = read('trials.json'), read('protocol.json'), read('statistics.json')
assert len(rows) == 121
assert collections.Counter(r['arm'] for r in rows) == {'generic': 43, 'pplx': 78}
assert len({r['caseId'] for r in rows if r['arm'] == 'pplx'}) == 60
assert sum(r['split'] == 'test' for r in rows) == 54
assert sum(not r['scored'] for r in rows) == 35
assert len({r['caseId'] for r in rows if r['scored']}) == 25
assert len({(r['caseId'], r['repeat'], r['arm']) for r in rows}) == 121
for row, scheduled in zip(sorted(rows, key=lambda r: r['ordinal']), protocol['schedule']):
    assert all(row[k] == scheduled[k] for k in ['caseId', 'repeat', 'arm', 'scored'])
    assert row['isolationPassed']
    assert row['correct'] is None if not row['scored'] else isinstance(row['correct'], bool)
    assert row['status'] == 'completed'
    assert math.isfinite(row['seconds']) and row['seconds'] > 0
    assert set(row['answers']) == {'family', 'stage', 'reporter'}
    for answer in row['answers'].values():
        probabilities = answer['probabilities']
        assert all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities.values())
        assert abs(sum(probabilities.values()) - 1) < 1e-5
        assert answer['choice'] in probabilities
        assert probabilities[answer['choice']] >= max(probabilities.values()) - 1e-6
for arm in ['generic', 'pplx']:
    test = [r for r in rows if r['arm'] == arm and r['split'] == 'test']
    assert sum(r['correct'] for r in test) == stats['primary'][arm]['success']
    single = [r for r in rows if r['arm'] == arm and r['scored'] and r['repeat'] == 0]
    assert sum(r['correct'] for r in single) == stats['secondarySingleRepeat25'][arm]['success']
for name in ['primaryMcNemar', 'secondaryMcNemar']:
    result = stats[name]
    b, c = result['genericOnlyCorrect'], result['pplxOnlyCorrect']
    assert result['exactTwoSidedP'] == (binomtest(b, b+c).pvalue if b+c else 1.0)
print('PASS: 121 trials; counts, schedule, isolation, finite probabilities and score accounting.')
