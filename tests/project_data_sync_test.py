import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('project_data_sync', Path(__file__).resolve().parents[1] / 'scripts/sync-project-data.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class ProjectDataSyncTests(unittest.TestCase):
    def test_remote_inventory_cannot_supply_arbitrary_local_paths(self):
        valid = {'schema':'kernel-project-snapshot/v1','archives':[{'name':name,'bytes':1,'sha256':'a'*64} for name in ['lab.tar.gz','service.tar.gz','release.tar.gz']]}
        sync.validate_inventory(valid)
        valid['archives'][0]['name']='../../outside'
        with self.assertRaises(ValueError):sync.validate_inventory(valid)

    def test_private_state_must_match_captured_hash(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=b'{"users":[]}'
            archive=self.archive(root,[('service/data/accounts.json',data,'file')])
            self.assertEqual(sync.validate_private_state(archive,{'data/accounts.json':hashlib.sha256(data).hexdigest()}),{'data/accounts.json':True})
            with self.assertRaises(ValueError):sync.validate_private_state(archive,{'data/accounts.json':'0'*64})

    def archive(self, root, entries):
        path = root / 'input.tar.gz'
        with tarfile.open(path, 'w:gz') as archive:
            for name, content, kind in entries:
                member = tarfile.TarInfo(name)
                if kind == 'file':
                    member.size = len(content)
                    archive.addfile(member, io.BytesIO(content))
                else:
                    member.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE
                    member.linkname = content
                    archive.addfile(member)
        return path

    def test_binary_log_bytes_are_preserved_and_other_prefix_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self.archive(root, [('lab/data/serial.log', b'bad\xff\r\n', 'file'), ('private/accounts.json', b'private', 'file')])
            self.assertEqual(sync.extract_prefix(archive, 'lab/data', root / 'output'), 1)
            self.assertEqual((root / 'output/serial.log').read_bytes(), b'bad\xff\r\n')
            self.assertFalse((root / 'output/accounts.json').exists())

    def test_traversal_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self.archive(root, [('lab/data/../escaped', b'bad', 'file')])
            with self.assertRaises(ValueError):
                sync.extract_prefix(archive, 'lab/data', root / 'output')
            self.assertFalse((root / 'escaped').exists())

    def test_symbolic_links_are_not_materialized_on_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self.archive(root, [('lab/data/link', '/etc/passwd', 'symlink')])
            with self.assertRaises(ValueError):
                sync.extract_prefix(archive, 'lab/data', root / 'output')

    def test_windows_drive_and_backslash_escape_are_rejected(self):
        for name in ['lab/data/C:/escaped', 'lab/data/..\\escaped']:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                archive = self.archive(root, [(name, b'bad', 'file')])
                with self.assertRaises(ValueError):
                    sync.extract_prefix(archive, 'lab/data', root / 'output')

    def test_archive_hardlinks_are_materialized_as_exact_regular_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self.archive(root, [('lab/original', b'original', 'file'), ('lab/data/copy', 'lab/original', 'hardlink')])
            sync.extract_prefix(archive, 'lab/data', root / 'output')
            self.assertEqual((root / 'output/copy').read_bytes(), b'original')

    def test_experiment_hardlinks_can_remain_in_archive_without_duplicate_expansion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            archive=self.archive(root,[('lab/original',b'large artifact','file'),('lab/data/copy','lab/original','hardlink'),('lab/data/trace.json',b'{}','file')])
            links=[]
            self.assertEqual(sync.extract_prefix(archive,'lab/data',root/'output',skip_hardlinks=True,skipped=links),1)
            self.assertEqual(links,['lab/data/copy'])
            self.assertFalse((root/'output/copy').exists())
            self.assertEqual((root/'output/trace.json').read_bytes(),b'{}')

    def test_existing_dataset_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self.archive(root, [('lab/data/file', b'new', 'file')])
            (root / 'output').mkdir()
            (root / 'output/file').write_bytes(b'original')
            with self.assertRaises(FileExistsError):
                sync.extract_prefix(archive, 'lab/data', root / 'output')
            self.assertEqual((root / 'output/file').read_bytes(), b'original')


if __name__ == '__main__':
    unittest.main()
