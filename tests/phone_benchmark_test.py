import importlib.util,json,pathlib,tempfile,unittest,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def module(name,file):
 s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
prepare=module('phone_prepare','prepare-phone-benchmark.py');scoring=module('phone_score','phone-scoring.py')
class PhoneBenchmarkTests(unittest.TestCase):
 def test_deterministic_inputs_and_private_labels(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);a=prepare.build(root);b=prepare.build(root)
   self.assertEqual(a,b);self.assertEqual(len(a['cases']),8)
   for c in a['cases']:
    self.assertEqual(prepare.digest(root/c['archive']),c['sha256'])
    with zipfile.ZipFile(root/c['archive']) as z:
     self.assertNotIn('gold.json',z.namelist());self.assertTrue(json.loads(z.read('metadata.json'))['synthetic'])
   self.assertEqual(a['cases'][1]['stagesPresent'],['xloader','bl2'])
 def test_scoring_requires_real_supporting_quote_and_strict_json(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);m=prepare.build(root);gold=json.loads((root/'private/gold.json').read_text());c=m['cases'][4];g=gold[c['id']]
   self.assertEqual(scoring.score(g,g,root/c['archive'])['points'],100)
   wrong={**g,'stage':'android','evidence':[{'file':'android.log','quote':g['evidence'][0]['quote']}]}
   self.assertEqual(scoring.score(wrong,g,root/c['archive'])['points'],50)
   with self.assertRaises(ValueError):scoring.parse('prose ```json\n{}\n```')
   self.assertEqual(scoring.parse('```json\n{"stage":"kernel"}\n```')['stage'],'kernel')
 def test_real_capture_packages_do_not_mix_devices_or_captures(self):
  real=module('phone_real','prepare-phone-real-samples.py')
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);files=[]
   for device,capture in [('Phone-A','capture1'),('Phone-A','capture2'),('Phone-B','capture1')]:
    p=root/'content'/device/capture/'logcat.txt';p.parent.mkdir(parents=True);p.write_text(device+':'+capture);files.append({'path':p.relative_to(root/'content').as_posix()})
   (root/'provenance.json').write_text(json.dumps({'files':files,'source':'https://example.invalid/publisher'}))
   real.prepare(root);m=json.loads((root/'samples.json').read_text());self.assertEqual(len(m['cases']),3)
   for c in m['cases']:
    with zipfile.ZipFile(root/c['archive']) as z:
     self.assertEqual(z.read('logcat.txt').decode(),c['device']+':'+c['capture']);self.assertFalse(json.loads(z.read('provenance.json'))['synthetic'])
if __name__=='__main__':unittest.main()
