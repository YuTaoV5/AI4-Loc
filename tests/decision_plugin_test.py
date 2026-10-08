import io,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from decision_plugin import DecisionClient,candidates,preflight
from localization_agent import Inspector,run

class DecisionTests(unittest.TestCase):
    def test_dedicated_systemone_shape_does_not_fabricate_full_vocabulary_mass(self):
        with tempfile.TemporaryDirectory() as tmp:
            reply={'answers':{'x':{'type':'choice','choice':'a','probabilities':{'a':.7,'b':.3}}},'usage':{'input_tokens':20,'output_tokens':0}}
            def respond(req,**kwargs):
                body=json.loads(req.data);self.assertEqual(req.full_url,'http://fixture/v1/systemone')
                self.assertEqual(body['questions']['x']['criteria'],{'a':'first','b':'second'})
                self.assertNotIn('temperature',body);self.assertNotIn('return_prompt_token_ids',body)
                return io.BytesIO(json.dumps(reply).encode())
            client=DecisionClient('http://fixture',tmp,api='systemone')
            with patch('urllib.request.urlopen',side_effect=respond):value=client.decide('state',[{'id':'x','type':'choice','question':'which?','options':[{'name':'a','description':'first'},{'name':'b','description':'second'}]}])
            self.assertIsNone(value['answers']['x']['label_mass']);self.assertEqual(client.calls[0]['rawResponse'],reply)

    def test_systemone_noul_scalar_is_converted_to_yes_no_distribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            reply={'answers':{'x':{'type':'noul','noul':.75}},'usage':{'output_tokens':0}}
            with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(reply).encode())):
                value=DecisionClient('http://fixture',tmp,api='systemone').decide('state',[{'id':'x','type':'yes_no','question':'true?'}])
            self.assertEqual(value['answers']['x']['probabilities'],{'yes':.75,'no':.25})

    def test_bad_probability_is_rejected_and_failed_request_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            client=DecisionClient('http://fixture/v1',tmp)
            reply={'object':'decisions','prompt_format_version':1,'usage':{'completion_tokens':0},'answers':{'x':{'probabilities':{'yes':2,'no':-1},'label_mass':.8}}}
            with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(reply).encode())):
                with self.assertRaises(ValueError):client.decide('evidence',[{'id':'x','type':'yes_no','question':'fault?'}])
            trace=json.loads((pathlib.Path(tmp)/'decision-trace.json').read_text())
            self.assertEqual(trace['calls'][0]['status'],'error');self.assertEqual(len(client.calls),1)

    def test_label_mass_and_prompt_ids_retained_without_generated_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            client=DecisionClient('http://fixture/v1',tmp)
            reply={'object':'decisions','prompt_format_version':1,'usage':{'completion_tokens':0},'answers':{'x':{'type':'yes_no','probabilities':{'yes':.8,'no':.2},'label_mass':.5,'prompt_token_ids':[1],'label_token_ids':[2,3]}}}
            def respond(req,**kwargs):
                self.assertEqual(req.full_url,'http://fixture/v1/decisions');self.assertTrue(json.loads(req.data)['return_prompt_token_ids'])
                return io.BytesIO(json.dumps(reply).encode())
            with patch('urllib.request.urlopen',side_effect=respond):self.assertEqual(client.decide('evidence',[{'id':'x','type':'yes_no','question':'fault?'}]),reply)

    def test_interrupted_instruction_precedes_reporting_frames_without_dataset_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'source').mkdir();i=Inspector(root);queries=[]
            def execute(tool,args):queries.append(args['text']);return {'evidenceId':'T1','output':''}
            i.execute=execute
            candidates(i,{'firstDiagnosticLine':1,'lines':[{'line':1,'text':'reporter+0x1/0x5'},{'line':2,'text':'RIP: 0010:custom_worker+0x1/0x5 [external]'},{'line':3,'text':'] ? misleading_frame+0x1/0x9 [external]'}]})
            self.assertEqual(queries[0],'custom_worker')

    def test_missing_source_never_invents_source_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            i=Inspector(tmp);self.assertEqual(candidates(i,{'firstDiagnosticLine':1}),[])

    def test_failed_decision_counts_toward_shared_http_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp)/'input.log').write_text('BUG: observed fault\n')
            with patch('urllib.request.urlopen',side_effect=ValueError('endpoint unavailable')) as http:
                result=run({'workspace':tmp,'baseUrl':'http://generation/v1','model':'fixture','maxModelCalls':1,'timeout':10,'eagerBoundary':True,'decisionPlugin':{'baseUrl':'http://decision','policy':'decision'}})
            self.assertEqual(http.call_count,1);self.assertEqual(result['metrics']['modelRequests'],1)
            self.assertEqual(result['metrics']['generationModelRequests'],0);self.assertEqual(result['metrics']['decisionModelRequests'],1)
            self.assertIsNone(result['analysis'])

if __name__=='__main__':unittest.main()
