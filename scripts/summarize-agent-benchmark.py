"""Rebuild public tables and research figures from the sanitized acceptance summary.

Standard library produces CSV/statistics; --figures additionally needs matplotlib.
Never reads private prompts, accounts, model responses or the retained archive.
"""
import argparse
import csv
import hashlib
import json
import math
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIELDS = ['boundarySeconds', 'rootLocationSeconds', 'reportOutputSeconds', 'totalTokens', 'modelRequests']
WEIGHTS = [4, 6, 2, 4, 4]
REFERENCES = [5, 60, 20, 12000, 4]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', action='store_true')
    args = parser.parse_args()
    source = ROOT / 'docs/agent-benchmark-platform-results-20261009.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    rows = data['cases']
    out = ROOT / 'docs/results/agent-benchmark-20261009'
    out.mkdir(parents=True, exist_ok=True)
    numeric = []
    contributions = [0.0] * len(FIELDS)
    for row in rows:
        hits = [int(row['scores'][k]) for k in ['stageHit', 'panicTypeHit', 'codeLocationHit']]
        metrics = row['metrics']
        assert metrics['tokensComplete'] and row['status'] == 'completed'
        accuracy = sum(w * h for w, h in zip([10, 20, 50], hits))
        parts = [w * r / (r + metrics[k]) if all(hits) else 0
                 for k, w, r in zip(FIELDS, WEIGHTS, REFERENCES)]
        contributions = [a + b / len(rows) for a, b in zip(contributions, parts)]
        numeric.append({'caseId': row['caseId'], 'stageHit': hits[0], 'panicTypeHit': hits[1],
                        'codeLocationHit': hits[2], **{k: metrics[k] for k in FIELDS},
                        'inputTokens': metrics['inputTokens'], 'outputTokens': metrics['outputTokens'],
                        'generationModelRequests': metrics['generationModelRequests'],
                        'decisionModelRequests': metrics['decisionModelRequests'],
                        'accuracyPoints': accuracy, 'efficiencyPoints': sum(parts),
                        'totalPoints': accuracy + sum(parts)})
    for metric in FIELDS:
        assert math.isclose(sum(r[metric] for r in numeric), data['score']['totals'][metric], abs_tol=1e-8)
    for metric in ['accuracyPoints', 'efficiencyPoints']:
        assert math.isclose(statistics.mean(r[metric] for r in numeric), data['score'][metric], abs_tol=1e-8)
    assert math.isclose(statistics.mean(r['totalPoints'] for r in numeric), data['score']['total'], abs_tol=1e-8)
    with (out / 'cases.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(numeric[0]))
        writer.writeheader()
        writer.writerows(numeric)
    summary = {'schema': 'public-agent-benchmark-analysis/v1',
               'source': str(source.relative_to(ROOT)).replace('\\', '/'),
               'sourceSha256': hashlib.sha256(source.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
               'sourceHashEncoding': 'UTF-8 bytes with CRLF normalized to LF for cross-platform Git checkouts',
               'n': len(rows), 'percentileDefinition': 'nearest rank: sorted[ceil(p*n)-1]; n=9 p95 is maximum',
               'distributions': {},
               'efficiencyContributions': dict(zip(FIELDS, contributions)),
               'inputTokens': sum(r['inputTokens'] for r in numeric),
               'outputTokens': sum(r['outputTokens'] for r in numeric),
               'generationModelRequests': sum(r['generationModelRequests'] for r in numeric),
               'decisionModelRequests': sum(r['decisionModelRequests'] for r in numeric)}
    for metric in FIELDS:
        values = sorted(r[metric] for r in numeric)
        summary['distributions'][metric] = {'sum': sum(values), 'mean': statistics.mean(values),
                                           'median': statistics.median(values),
                                           'p95': values[math.ceil(.95 * len(values)) - 1],
                                           'min': values[0], 'max': values[-1]}
    (out / 'statistics.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    if args.figures:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                             'svg.fonttype': 'none', 'svg.hashsalt': 'ai4loc-20261009',
                             'axes.spines.top': False, 'axes.spines.right': False})
        fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout='constrained')
        ax = axes[0, 0]
        labels = ['Stage\n7/9', 'Fault type\n8/9', 'Code + healthy\n4/9', 'Fault code\n3/8']
        values = [7/9, 8/9, 4/9, 3/8]
        ax.bar(labels, values, color=['#426b9b', '#426b9b', '#c7783b', '#c7783b'])
        for x, v in enumerate(values):
            ax.text(x, v+.025, f'{v:.1%}', ha='center')
        ax.set(ylim=(0, 1.12), ylabel='Observed fraction (single run)', title='A. Boundary accuracy exceeds code localization')
        ax = axes[0, 1]
        names = [r['caseId'].replace('lkdtm_', '').replace('corrupt_', '').replace('USERCOPY_', 'UC_') for r in numeric]
        y = list(range(len(names)))
        report = [r['reportOutputSeconds'] for r in numeric]
        before = [r['rootLocationSeconds']-r['reportOutputSeconds'] for r in numeric]
        ax.barh(y, before, label='Before final valid report', color='#426b9b')
        ax.barh(y, report, left=before, label='Final report request + validation', color='#8fb4d1')
        ax.set_yticks(y, names)
        ax.invert_yaxis()
        ax.set(xlabel='Seconds from worker start; boundary is included', title='B. Time to validated location report')
        ax.legend(fontsize=8, loc='lower right')
        ax = axes[1, 0]
        ax.barh(y, [r['inputTokens'] for r in numeric], label='Input', color='#426b9b')
        ax.barh(y, [r['outputTokens'] for r in numeric], left=[r['inputTokens'] for r in numeric], label='Output', color='#c7783b')
        ax.set_yticks(y, names)
        ax.invert_yaxis()
        ax.set(xlabel='Measured tokens, all Decision + Chat calls', title='C. Input accounts for 98.33% of total tokens')
        ax.legend(fontsize=8, loc='lower right')
        ax = axes[1, 1]
        for label, key, color in [('Accuracy / 80', 'accuracyPoints', '#426b9b'), ('Efficiency / 20', 'efficiencyPoints', '#c7783b')]:
            ax.barh(y, [r[key] for r in numeric], left=[r['accuracyPoints'] if key=='efficiencyPoints' else 0 for r in numeric], label=label, color=color)
        ax.set_yticks(y, names)
        ax.invert_yaxis()
        ax.set(xlim=(0, 100), xlabel='Case score / 100; suite mean = 51.6763', title='D. Efficiency is gated on all accuracy hits')
        ax.legend(fontsize=8, loc='lower right')
        fig.suptitle('AI4Loc | Fixed nine-case development suite | 2026-10-09\nPrivate acceptance; not a blind generalization estimate', fontsize=14)
        fig.savefig(out / 'benchmark-analysis.svg', metadata={'Date': None})
        svg = out / 'benchmark-analysis.svg'
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
        fig.savefig(out / 'benchmark-analysis.png', dpi=180)
        plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
