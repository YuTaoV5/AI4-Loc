import pathlib,sys,tempfile,unittest,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools/kernel-lab'))
from dataset_contract import PROFILES,agent_log,record,resolve,export_view

class DatasetTests(unittest.TestCase):
    def test_all_seven_nonempty_input_profiles(self):
        self.assertEqual(len(PROFILES),7);self.assertTrue(all(PROFILES.values()))
    def test_collector_answer_metadata_redacted_without_renumbering(self):
        raw=b'Linux ki.scn=corrupt_uaf_kmalloc\nKI_RUNTIME_NOTES_BEGIN\nYWJj\nKI_RUNTIME_NOTES_END\nki_bench: uaf_kmalloc: writing to freed object\nBUG: KASAN: use-after-free in ki_uaf_kmalloc\n'
        out=agent_log(raw).decode().splitlines();self.assertEqual(len(out),6);self.assertNotIn('corrupt_uaf_kmalloc','\n'.join(out));self.assertEqual(out[5],'BUG: KASAN: use-after-free in ki_uaf_kmalloc')
    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)
            with self.assertRaises(ValueError):resolve(root,{'path':'../outside'})
    def test_export_does_not_copy_evaluator_annotations(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);(root/'agent.log').write_text('BUG: sample\n');(root/'ground-truth.json').write_text('secret root cause')
            manifest={'cases':[{'id':'c','status':'ready','files':{'agentLog':record(root,root/'agent.log'),'groundTruth':record(root,root/'ground-truth.json')}}]}
            (root/'manifest.json').write_text(json.dumps(manifest));dest=root/'view';export_view(root,'c','log',dest)
            self.assertEqual(set(p.name for p in dest.iterdir()),{'input.log','inputs.json'});self.assertEqual(json.loads((dest/'inputs.json').read_text())['missingInputs'],['artifacts','source'])
if __name__=='__main__':unittest.main()
