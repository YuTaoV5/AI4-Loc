import io,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from localization_agent import Inspector,run
from boundary_router import QUESTIONS,boundary_state

class BoundaryTests(unittest.TestCase):
    def test_first_usercopy_report_precedes_panic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'input.log').write_text('boot complete\nusercopy: Kernel memory exposure attempt detected from stack\nkernel BUG at mm/usercopy.c:99!\nKernel panic\n')
            self.assertEqual(Inspector(root).execute('incident',{})['firstDiagnosticLine'],2)

    def test_collector_and_labels_blocked_while_implementation_is_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'source').mkdir()
            for f in ['guest_init.sh','labels.json','worker.c']:(root/'source'/f).write_text('sentinel')
            i=Inspector(root)
            for f in ['guest_init.sh','labels.json','../worker.c']:
                self.assertIn('error',i.execute('source_read',{'path':f,'start':1,'count':5}))
            self.assertNotIn('error',i.execute('source_read',{'path':'worker.c','start':1,'count':5}))

    def test_decision_failure_falls_back_to_chat_and_counts_both_attempts(self):
        with tempfile.TemporaryDirectory(prefix='secret_case_') as tmp:
            root=pathlib.Path(tmp);(root/'input.log').write_text('BUG: observed fault\n')
            report={'summary':'bounded','category':'待专家分析','hypotheses':[],'nextSteps':[],'limitations':[],
                    'firstScene':{'evidenceRefs':['T1']},'localization':{'status':'insufficient','locations':[],'introducingCommit':None}}
            def answer(req,**kwargs):
                if req.full_url.endswith('/decisions'):raise ValueError('unavailable')
                self.assertNotIn(tmp,req.data.decode());return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(report)}}]}).encode())
            with patch('urllib.request.urlopen',side_effect=answer):result=run({'workspace':tmp,'baseUrl':'http://chat/v1','model':'fixture','maxModelCalls':3,'timeout':10,'eagerBoundary':True,'boundaryRouter':{'baseUrl':'http://decision'}})
            self.assertIsNotNone(result['analysis']);self.assertEqual(result['metrics']['modelRequests'],2)
            self.assertEqual(result['metrics']['decisionModelRequests'],1);self.assertIsNotNone(result['metrics']['boundarySeconds'])

    def test_boundary_questions_do_not_request_root_cause_or_source(self):
        self.assertEqual([x['id'] for x in QUESTIONS],['family','stage','reporter'])
        self.assertNotIn('source',boundary_state({'lines':[]}))

if __name__=='__main__':unittest.main()
