import importlib.util, json, pathlib, tempfile, unittest, hashlib, sys, struct, io
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
spec=importlib.util.spec_from_file_location('kernel_triage',pathlib.Path(__file__).resolve().parents[1]/'scripts/kernel_triage.py')
triage=importlib.util.module_from_spec(spec);spec.loader.exec_module(triage)
from kernel_artifacts import identity, events

def elf_fixture(kind,build='abcd1234',release=None,machine=62):
    def note(name,data,typ):
        name+=b'\0';return struct.pack('<III',len(name),len(data),typ)+name+b'\0'*((-len(name))%4)+data+b'\0'*((-len(data))%4)
    notes=note(b'GNU',bytes.fromhex(build),3) if release is None else note(b'VMCOREINFO',('OSRELEASE='+release+'\nBUILD-ID='+build+'\n').encode(),0)
    header=bytearray(64);header[:7]=b'\x7fELF\x02\x01\x01';struct.pack_into('<HH',header,16,kind,machine);struct.pack_into('<Q',header,32,64);struct.pack_into('<HH',header,54,56,1)
    ph=bytearray(56);struct.pack_into('<I',ph,0,4);struct.pack_into('<Q',ph,8,120);struct.pack_into('<Q',ph,32,len(notes))
    return bytes(header+ph)+notes

class EvidenceTests(unittest.TestCase):
    def setup_workspace(self, root):
        log='healthy\n'*100+'BUG: KASAN: use-after-free in release_item+0x10/0x80\nFreed by task 20\n'
        (root/'input.log').write_text(log,encoding='utf-8')
        return hashlib.sha256((root/'input.log').read_bytes()).hexdigest()

    def test_original_lines_and_input_immutability(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);before=self.setup_workspace(root);phases=[]
            result=triage.collect(root,lambda phase,message:phases.append(phase))
            self.assertIn('memory',result['families'])
            self.assertEqual(result['logEvidence'][0]['line'],101)
            self.assertEqual(before,hashlib.sha256((root/'input.log').read_bytes()).hexdigest())
            self.assertEqual(phases,['triage','source','symbols','hypotheses'])
            self.assertFalse(result['rootCauseVerified'])

    def test_source_hash_mismatch_is_not_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);self.setup_workspace(root)
            (root/'source-context/mm').mkdir(parents=True)
            (root/'source-context/mm/fault.c').write_text('wrong bytes')
            (root/'source-context.json').write_text(json.dumps({'files':[{'file':'mm/fault.c','sha256':'0'*64}]}))
            result=triage.collect(root)
            self.assertEqual(result['sourceEvidence'],[])
            self.assertTrue(any('哈希不符' in gap for gap in result['gaps']))

    def test_artifact_path_escape_never_runs_elf_tool(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);self.setup_workspace(root)
            (root/'artifacts.json').write_text(json.dumps({'files':[{'path':'../outside','expectedBuildId':'abcd'}]}))
            result=triage.collect(root)
            self.assertEqual(result['artifacts'],[])
            self.assertTrue(all(command['tool']=='rg' for command in result['commands']))

    def test_healthy_log_does_not_invent_fault_or_verified_root_cause(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);(root/'input.log').write_text('normal shutdown\n')
            result=triage.collect(root)
            self.assertEqual(result['families'],[])
            self.assertFalse(result['rootCauseVerified'])
            self.assertEqual(result['commands'][0]['exitCode'],1)

    def test_multiple_reports_preserve_boundaries_and_panic_cascade(self):
        with tempfile.TemporaryDirectory() as temp:
            log=pathlib.Path(temp)/'input.log';log.write_text('BUG: KASAN: use-after-free\ntrace\nKernel panic - not syncing\n# FILE: second.log\nINFO: task worker blocked for more than 120 seconds\n')
            grouped=events(log);self.assertEqual([e['startLine'] for e in grouped['events']],[1,5]);self.assertEqual(grouped['events'][0]['possibleCascadeLines'],[3]);self.assertEqual(grouped['primaryEventId'],'E1')

    def test_bounded_elf_identity_and_vmcore_notes(self):
        with tempfile.TemporaryDirectory() as temp:
            f=pathlib.Path(temp)/'elf';f.write_bytes(elf_fixture(4,release='6.6-test'))
            d=identity(f);self.assertEqual(d['buildId'],'abcd1234');self.assertEqual(d['architecture'],'x86_64');self.assertEqual(d['kernelRelease'],'6.6-test')
            f.write_bytes(b'\x7fELF');self.assertRaises(ValueError,identity,f)

    def test_runtime_mismatch_prevents_all_dump_queries(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);(root/'input.log').write_text('Linux version 6.6-test\nBUG: KASAN: out-of-bounds\n')
            (root/'vmlinux').write_bytes(elf_fixture(2));(root/'vmcore').write_bytes(elf_fixture(4,build='ffffffff',release='6.6-test'))
            (root/'artifacts.json').write_text(json.dumps({'files':[{'path':'vmlinux','kind':'symbols'},{'path':'vmcore','kind':'vmcore'}]}))
            result=triage.collect(root);self.assertFalse(result['artifacts'][0]['runtimeMatchVerified']);self.assertEqual(result['dumpQueries'],[])
            self.assertTrue(any('停止 crash/drgn' in gap for gap in result['gaps']))

    def test_verified_dump_only_runs_fixed_queries_and_never_marks_root_cause_proven(self):
        class Process:
            def __init__(self,output):self.stdout=io.BytesIO(output.encode());self.returncode=0
            def wait(self):return 0
            def poll(self):return 0
            def kill(self):self.returncode=-9
        calls=[]
        def spawn(argv,**kwargs):
            calls.append(argv)
            if pathlib.Path(argv[0]).name.startswith('rg'):return Process('1:Linux version 6.6-test\n2:BUG: KASAN: out-of-bounds\n')
            if '-S' in argv:return Process('[1] .debug_info PROGBITS\n')
            return Process('fixed query output')
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);(root/'input.log').write_text('Linux version 6.6-test\nBUG: KASAN: out-of-bounds\n')
            (root/'vmlinux').write_bytes(elf_fixture(2));(root/'vmcore').write_bytes(elf_fixture(4,release='6.6-test'))
            (root/'artifacts.json').write_text(json.dumps({'files':[{'path':'vmlinux','kind':'symbols'},{'path':'vmcore','kind':'vmcore'}]}))
            with patch.object(triage.subprocess,'Popen',side_effect=spawn),patch.object(triage.shutil,'which',side_effect=lambda name:name):result=triage.collect(root)
            self.assertTrue(result['artifacts'][0]['matchesVmcoreBuild']);self.assertFalse(result['artifacts'][0]['runtimeMatchVerified']);self.assertEqual(len(result['dumpQueries']),2);self.assertFalse(result['rootCauseVerified'])
            self.assertEqual((root/'crash-queries.txt').read_text(),'sys\nbt\nquit\n');self.assertTrue(any('--no_crashrc' in c for c in calls))

    def test_config_hash_conflict_stops_dump_queries(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);(root/'input.log').write_text('Linux version 6.6-test\nKernel config SHA256: '+'0'*64+'\nBUG: KASAN: out-of-bounds\n')
            (root/'vmlinux').write_bytes(elf_fixture(2));(root/'vmcore').write_bytes(elf_fixture(4,release='6.6-test'));(root/'config').write_text('CONFIG_DEBUG_INFO=y\n')
            (root/'artifacts.json').write_text(json.dumps({'files':[{'path':'vmlinux','kind':'symbols'},{'path':'vmcore','kind':'vmcore'},{'path':'config','kind':'kernelConfig'}]}))
            result=triage.collect(root);self.assertTrue(result['kernelConfig']['runtimeMismatch']);self.assertEqual(result['dumpQueries'],[])

if __name__=='__main__': unittest.main()
