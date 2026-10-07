import importlib.util,pathlib,unittest
spec=importlib.util.spec_from_file_location('review',pathlib.Path(__file__).resolve().parents[1]/'scripts/review-localization.py');review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
class ReviewTests(unittest.TestCase):
    def fixture(self):return {'datasetManifestSha256':'digest','runs':[{'caseId':'c','profile':'log','status':'completed','scores':{},'analysis':{'firstScene':{'evidenceRefs':['T1']}}}]}
    def test_missing_reviews_stay_unknown(self):
        result=review.apply_reviews(self.fixture(),{'datasetManifestSha256':'digest','reviews':[]});self.assertIsNone(result['independentReview']['mechanismAccuracyOnReviewedRuns'])
    def test_review_wrong_dataset_rejected(self):
        with self.assertRaises(ValueError):review.apply_reviews(self.fixture(),{'datasetManifestSha256':'other'})
    def test_failed_mechanism_joins_regression_queue(self):
        r={'datasetManifestSha256':'digest','reviews':[{'caseId':'c','profile':'log','reviewer':'test','basis':'waiting stack does not identify completion producer','evidenceRefs':['T1'],'mechanismCorrect':False}]}
        result=review.apply_reviews(self.fixture(),r);self.assertEqual(len(result['regressionQueue']),1);self.assertEqual(result['independentReview']['mechanismAccuracyOnReviewedRuns'],0)
if __name__=='__main__':unittest.main()
