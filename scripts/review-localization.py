"""Join independent human mechanism reviews; missing review stays unknown."""
import argparse,json,pathlib

def apply_reviews(results,reviews):
    if reviews.get('datasetManifestSha256')!=results.get('datasetManifestSha256'):raise ValueError('Review dataset fingerprint mismatch')
    entries={}
    for item in reviews.get('reviews',[]):
        key=(item['caseId'],item['profile'])
        if key in entries:raise ValueError('Duplicate review')
        if not item.get('reviewer') or not item.get('basis') or not item.get('evidenceRefs'):raise ValueError('Review needs reviewer, causal basis and evidence references')
        if not isinstance(item.get('mechanismCorrect'),bool):raise ValueError('Mechanism review must be a boolean')
        entries[key]=item
    known={(r['caseId'],r['profile']) for r in results['runs']}
    if set(entries)-known:raise ValueError('Review refers to an absent model run')
    for row in results['runs']:
        review=entries.get((row['caseId'],row['profile']))
        if not review:continue
        report=row.get('analysis') or {};refs=set((report.get('firstScene') or {}).get('evidenceRefs',[]))
        for loc in (report.get('localization') or {}).get('locations',[]):refs.update(loc.get('evidenceRefs',[]))
        if not set(review['evidenceRefs']).issubset(refs):raise ValueError('Review references evidence not cited by the report')
        row['review']=review;row['scores']['rootCauseMechanismCorrect']=review['mechanismCorrect'];row['scores']['requiresHumanMechanismReview']=False
    reviewed=[r for r in results['runs'] if 'review' in r]
    results['independentReview']={'reviewedRuns':len(reviewed),'totalRuns':len(results['runs']),'mechanismAccuracyOnReviewedRuns':sum(r['scores']['rootCauseMechanismCorrect'] for r in reviewed)/len(reviewed) if reviewed else None,'unreviewedRunsRemainUnknown':True}
    results['regressionQueue']=[{'caseId':r['caseId'],'profile':r['profile'],'reason':r.get('error') or 'independent mechanism review failed'} for r in results['runs'] if r['status']=='failed' or r['scores'].get('rootCauseMechanismCorrect') is False]
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',type=pathlib.Path,required=True);p.add_argument('--reviews',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    if a.output.resolve() in [a.results.resolve(),a.reviews.resolve()]:p.error('Use a new output file to preserve original evidence')
    result=apply_reviews(json.loads(a.results.read_text()),json.loads(a.reviews.read_text()));a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['independentReview']))
