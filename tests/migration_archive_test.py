import importlib.util,io,os,pathlib,unittest
p=pathlib.Path(__file__).resolve().parents[1]/'scripts/migration-archive.py';s=importlib.util.spec_from_file_location('migration_archive',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class MigrationArchiveTests(unittest.TestCase):
 def test_stream_roundtrip_and_tamper_authentication(self):
  key=os.urandom(32);source=b'private archive test\0'*(m.BLOCK//10);encrypted=io.BytesIO();first=m.encrypt(io.BytesIO(source),encrypted,key);decoded=io.BytesIO();self.assertEqual(m.decrypt(io.BytesIO(encrypted.getvalue()),decoded,key),first);self.assertEqual(decoded.getvalue(),source)
  changed=bytearray(encrypted.getvalue());changed[-18]^=1
  with self.assertRaises(Exception):m.decrypt(io.BytesIO(changed),None,key)
if __name__=='__main__':unittest.main()
