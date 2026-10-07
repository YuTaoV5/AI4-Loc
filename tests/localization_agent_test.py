import io,json,pathlib,sys,tempfile,tarfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from localization_agent import Inspector,validate_report,run,unpack_source,source_triage

class LocalizationTests(unittest.TestCase):
    def test_oom_task_filename_leads_to_actual_source_without_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'source').mkdir();(root/'source/worker.c').write_text('int main(void) { return 0; }\n')
            i=Inspector(root)
            with patch.object(i,'subprocess',side_effect=[{'output':'./worker.c\n'},{'output':''}]):
                rows=source_triage(i,{'firstDiagnosticLine':1,'lines':[{'line':1,'text':'worker invoked oom-killer: order=0'}]})
            self.assertEqual(rows[-1]['path'],'worker.c');self.assertEqual(rows[-1]['lines'][0]['line'],1)
    def test_source_triage_does_not_guess_when_no_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'source').mkdir();i=Inspector(root)
            self.assertEqual(source_triage(i,{'firstDiagnosticLine':None}),[]);self.assertEqual(i.records,[])
    def test_eager_boundary_is_visible_before_first_model_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'input.log').write_text('BUG: first\n');events=[]
            report={'summary':'unknown','category':'待专家分析','hypotheses':[],'nextSteps':[],'limitations':[],'firstScene':{'evidenceRefs':['T1']},'localization':{'status':'function_candidate','locations':[],'introducingCommit':None}}
            def respond(request,**kwargs):
                self.assertEqual(events[0]['phase'],'boundary');self.assertEqual(json.loads(request.data)['response_format']['type'],'json_schema');return io.BytesIO(json.dumps({'choices':[{'message':{'role':'assistant','content':json.dumps(report)}}]}).encode())
            with patch('urllib.request.urlopen',side_effect=respond):result=run({'workspace':tmp,'baseUrl':'http://fixture/v1','model':'fixture','timeout':10,'maxModelCalls':5,'eagerBoundary':True},events.append)
            self.assertEqual(result['metrics']['modelRequests'],1);self.assertEqual(result['metrics']['preflightToolCalls'],1);self.assertEqual(result['metrics']['modelToolCalls'],0);self.assertIsNotNone(result['metrics']['firstSceneSeconds'])
    def test_native_ollama_wire_protocol_and_explicit_thinking_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'input.log').write_text('BUG: test\n')
            report={'summary':'unknown','category':'待专家分析','hypotheses':[],'nextSteps':[],'limitations':[],'firstScene':{'evidenceRefs':['T1']},'localization':{'status':'insufficient','locations':[],'introducingCommit':None}}
            replies=[{'message':{'content':'','tool_calls':[{'function':{'name':'incident','arguments':{}}}]},'eval_count':14},{'message':{'content':json.dumps(report)},'eval_count':100}];payloads=[]
            def respond(request,**kwargs):payloads.append(json.loads(request.data));return io.BytesIO(json.dumps(replies.pop(0)).encode())
            with patch('urllib.request.urlopen',side_effect=respond):result=run({'workspace':tmp,'baseUrl':'http://fixture','transport':'ollama-native','model':'fixture','timeout':10,'maxModelCalls':5})
            self.assertFalse(payloads[0]['think']);self.assertFalse(payloads[1]['think']);self.assertIn('format',payloads[1]);self.assertEqual(payloads[1]['messages'][-2]['tool_name'],'incident');self.assertEqual(result['metrics']['requests'][0]['usage']['outputTokens'],14)
    def test_missing_source_exposes_only_available_tools_and_uses_typed_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'input.log').write_text('BUG: KASAN: use-after-free in f\n')
            report={'summary':'candidate','category':'释放后使用','hypotheses':[],'nextSteps':[],'limitations':[],'firstScene':{'evidenceRefs':['T1']},'localization':{'status':'function_candidate','locations':[],'introducingCommit':None}}
            first={'choices':[{'message':{'role':'assistant','content':None,'tool_calls':[{'id':'call1','type':'function','function':{'name':'incident','arguments':'{}'}}]}}]}
            second={'choices':[{'message':{'role':'assistant','content':json.dumps(report)}}]}
            responses=[io.BytesIO(json.dumps(value).encode()) for value in [first,second]];payloads=[]
            def respond(request,**kwargs):payloads.append(json.loads(request.data));return responses.pop(0)
            with patch('urllib.request.urlopen',side_effect=respond):result=run({'workspace':tmp,'baseUrl':'http://fixture/v1','model':'fixture','timeout':10,'maxModelCalls':5})
            self.assertEqual(result['metrics']['modelRequests'],2);self.assertEqual(result['metrics']['toolCalls'],1)
            self.assertEqual({t['function']['name'] for t in payloads[0]['tools']},{'incident','log_read','log_search'})
            self.assertEqual(payloads[1]['response_format']['type'],'json_schema');self.assertNotIn('tools',payloads[1])
    def test_source_archive_rejects_traversal_before_publishing_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            with tarfile.open(root/'source.tar.gz','w:gz') as tar:
                member=tarfile.TarInfo('../escaped.c');member.size=4;tar.addfile(member,io.BytesIO(b'evil'))
            with self.assertRaises(ValueError):unpack_source(root)
            self.assertFalse((root/'source').exists())
    def test_boot_debug_and_kasan_initialization_are_not_faults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'input.log').write_text('printk: debug: ignoring loglevel setting.\nkasan: KernelAddressSanitizer initialized\nBUG: KASAN: use-after-free\n')
            self.assertEqual(Inspector(root).execute('incident',{})['firstDiagnosticLine'],3)
    def test_oom_first_scene_is_allocator_invocation_not_terminal_panic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'input.log').write_text('boot\npressure invoked oom-killer: order=0\nCall Trace:\nKernel panic - not syncing: Out of memory\n')
            self.assertEqual(Inspector(root).execute('incident',{})['firstDiagnosticLine'],2)
    def test_first_scene_precedes_consequential_panic_and_keeps_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'input.log').write_text('boot\nBUG: KASAN: use-after-free\nread_item+0x4/0x10\nKernel panic\n');i=Inspector(root)
            self.assertEqual(i.execute('incident',{})['firstDiagnosticLine'],2)
            self.assertEqual(i.execute('log_search',{'text':'read_item'})['lines'][0]['line'],3)
    def test_paths_and_missing_history_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'source').mkdir();(root/'source/a.c').write_text('int x;');i=Inspector(root)
            self.assertIn('error',i.execute('source_read',{'path':'../manifest.json','start':1,'count':5}))
            self.assertIn('error',i.execute('git_history',{'path':'a.c'}))
    def test_hallucinated_locations_and_commit_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            i=Inspector(tmp);i.execute('incident',{})
            report={'summary':'unknown','category':'待专家分析','hypotheses':[],'nextSteps':[],'firstScene':{'evidenceRefs':['T1']},'localization':{'status':'code_candidate','locations':[{'path':'fake.c','startLine':2,'endLine':3,'evidenceRefs':['T1']}],'introducingCommit':{'hash':'abcdefabcdef','evidenceRefs':['T1']}}}
            result=validate_report(report,i);self.assertEqual(result['localization']['locations'],[]);self.assertIsNone(result['localization']['introducingCommit']);self.assertFalse(result['localization']['rootCauseVerified'])
    def test_actual_http_attempt_count_includes_failure(self):
        with tempfile.TemporaryDirectory() as tmp,patch('urllib.request.urlopen',side_effect=TimeoutError('test timeout')) as network:
            result=run({'workspace':tmp,'baseUrl':'http://127.0.0.1:1/v1','model':'fixture','timeout':10,'maxModelCalls':2})
            self.assertEqual(network.call_count,2);self.assertEqual(result['metrics']['modelRequests'],2);self.assertIsNone(result['analysis'])
    def test_source_location_must_be_in_returned_slice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'source').mkdir();(root/'source/a.c').write_text('int f(void) {\n return 1;\n}\n');i=Inspector(root);i.execute('source_read',{'path':'a.c','start':1,'count':3})
            r={'summary':'candidate','category':'待专家分析','hypotheses':[],'nextSteps':[],'firstScene':{'evidenceRefs':['T1']},'localization':{'status':'code_candidate','locations':[{'path':'a.c','symbol':'f','startLine':2,'endLine':2,'evidenceRefs':['T1']}],'introducingCommit':None}}
            self.assertEqual(len(validate_report(r,i)['localization']['locations']),1)
if __name__=='__main__':unittest.main()
