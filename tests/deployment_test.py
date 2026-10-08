"""Deployment must include all tool code and must not bundle private application state."""
import importlib.util, os, pathlib, subprocess, sys, tarfile, unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('deployment_doctor',ROOT/'scripts/deployment-doctor.py')
doctor=importlib.util.module_from_spec(spec);spec.loader.exec_module(doctor)

class DeploymentTest(unittest.TestCase):
    def test_full_preflight_rejects_missing_tools_and_model(self):
        with patch.dict(os.environ,{},clear=True),patch.object(doctor.shutil,'which',return_value=None):
            result=doctor.inspect(full=True)
        self.assertFalse(result['ok'])
        for name in ['modelName','modelUrl','agentPython','sandbox','bwrap','qemu-system-x86_64']:
            self.assertFalse(result['checks'][name]['ok'],name)

    def test_release_contains_full_tooling_but_no_private_state(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/package-deployment.py')],check=True,capture_output=True)
        with tarfile.open(ROOT/'data/deployment/site.tar.gz') as archive:
            names=set(archive.getnames())
            for name in ['scripts/localization_agent.py','scripts/start-linux-site.sh','scripts/start-windows-site.ps1',
                         'scripts/deployment-doctor.py','tools/kernel-lab/collect_dataset.py',
                         'tools/kernel-lab/dataset_contract.py','docs/CROSS_PLATFORM_DEPLOYMENT.md']:
                self.assertIn(name,names)
            for name in names:
                self.assertFalse(name.startswith(('data/server-snapshots/','data/windows-local/','data/local-archive/')))
                self.assertNotIn(name,{'data/accounts.json','data/state.json','data/admin-key.txt'})
                if name.endswith('.sh'):
                    self.assertNotIn(b'\r\n',archive.extractfile(name).read())
                    self.assertTrue(archive.getmember(name).mode & 0o111)

if __name__=='__main__':unittest.main()
