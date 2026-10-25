import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];FILE=ROOT/'tools/harness-skills/huawei-kirin-log-triage/scripts/inventory.py';spec=importlib.util.spec_from_file_location('kirin_inventory',FILE);inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
class KirinInventoryTests(unittest.TestCase):
 def test_identity_is_observed_not_target_and_failed_capture_not_kernel_fault(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/'system_properties.txt').write_text('[ro.product.model]: [DEL-LX9]\n[ro.build.version.release]: [12]\n[ro.hardware]: [Kirin9030Pro]\n[ro.serialno]: [PRIVATE]\n');(root/'kernel_log.txt').write_text('dmesg: Permission denied\n');(root/'opaque.bin').write_bytes(b'\0\xffencrypted');before={p.name:p.read_bytes() for p in root.iterdir()};result=inv.inventory(root)
   self.assertEqual({x['key'] for x in result['observedProperties']},{'ro.product.model','ro.build.version.release','ro.hardware'});self.assertNotIn('Pura 90',json.dumps(result));self.assertNotIn('PRIVATE',json.dumps(result));statuses={x['file']:x['status'] for x in result['files']};self.assertEqual(statuses['kernel_log.txt'],'capture-command-failed');self.assertEqual(statuses['opaque.bin'],'opaque');self.assertNotIn('kernel',result['stageHints']);self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
 def test_sampling_is_bounded_and_hints_do_not_imply_complete_chain(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/'firmware.log').write_bytes(b'BL31 runtime ready\n'+b'x'*inv.LIMIT+b'\nUEFI late\n');result=inv.inventory(root);self.assertEqual(result['stageHints'],['bl31']);self.assertTrue(result['files'][0]['sampleTruncated']);self.assertEqual(result['files'][0]['sampledBytes'],inv.LIMIT)
if __name__=='__main__':unittest.main()
