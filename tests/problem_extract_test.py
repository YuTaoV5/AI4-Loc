import importlib.util
import io
import pathlib
import tarfile
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('extractor',pathlib.Path(__file__).parents[1]/'scripts/problem-extract.py')
extractor=importlib.util.module_from_spec(spec);spec.loader.exec_module(extractor)

class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name);self.source=self.root/'upload';self.dest=self.root/'content'

    def test_binary_is_accepted_without_decoding(self):
        self.source.write_bytes(b'\x00\xffencrypted')
        self.assertEqual(extractor.extract(self.source,self.dest)['status'],'opaque')
        self.assertEqual(self.source.read_bytes(),b'\x00\xffencrypted')

    def test_zip_extracts_all_extensions(self):
        with zipfile.ZipFile(self.source,'w') as z:
            z.writestr('nested/dump.bin',b'\x00\xff');z.writestr('encrypted.vendor',b'cipher')
        self.assertEqual(extractor.extract(self.source,self.dest)['files'],2)
        self.assertEqual((self.dest/'nested/dump.bin').read_bytes(),b'\x00\xff')

    def test_traversal_keeps_original_without_partial_output(self):
        with zipfile.ZipFile(self.source,'w') as z:
            z.writestr('valid.txt','first');z.writestr('../escaped','bad')
        self.assertEqual(extractor.extract(self.source,self.dest)['status'],'opaque')
        self.assertEqual(list(self.dest.iterdir()),[])
        self.assertFalse((self.root/'escaped').exists())
        self.assertTrue(self.source.exists())

    def test_tar_symlink_is_not_followed(self):
        with tarfile.open(self.source,'w') as t:
            item=tarfile.TarInfo('link');item.type=tarfile.SYMTYPE;item.linkname='/etc/passwd';t.addfile(item)
        self.assertEqual(extractor.extract(self.source,self.dest)['status'],'opaque')

    def test_size_limit_keeps_original(self):
        with zipfile.ZipFile(self.source,'w') as z:z.writestr('large','abcd')
        original=extractor.LIMIT;extractor.LIMIT=2
        try:self.assertEqual(extractor.extract(self.source,self.dest)['status'],'opaque')
        finally:extractor.LIMIT=original
        self.assertEqual(list(self.dest.iterdir()),[])
