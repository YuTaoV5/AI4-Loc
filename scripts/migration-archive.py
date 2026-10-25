"""Streaming AES-256-GCM archive encryption for private migrations; keys never enter Git."""
import argparse,hashlib,os,pathlib
MAGIC=b'AI4LOC-PRIVATE-v1\n';BLOCK=1024*1024

def encrypt(source,target,key):
 from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
 nonce=os.urandom(12);cipher=Cipher(algorithms.AES(key),modes.GCM(nonce)).encryptor();cipher.authenticate_additional_data(MAGIC)
 target.write(MAGIC+nonce);digest=hashlib.sha256()
 for block in iter(lambda:source.read(BLOCK),b''):digest.update(block);target.write(cipher.update(block))
 target.write(cipher.finalize());target.write(cipher.tag);return digest.hexdigest()

def decrypt(source,target,key):
 from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
 if source.read(len(MAGIC))!=MAGIC:raise ValueError('Invalid archive header')
 nonce=source.read(12);start=source.tell();source.seek(-16,2);end=source.tell();tag=source.read(16);source.seek(start);cipher=Cipher(algorithms.AES(key),modes.GCM(nonce,tag)).decryptor();cipher.authenticate_additional_data(MAGIC);digest=hashlib.sha256();remaining=end-start
 while remaining:
  block=source.read(min(BLOCK,remaining))
  if not block:raise ValueError('Truncated archive')
  plain=cipher.update(block);remaining-=len(block);digest.update(plain)
  if target:target.write(plain)
 plain=cipher.finalize();digest.update(plain)
 if target:target.write(plain)
 return digest.hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['encrypt','decrypt','verify']);p.add_argument('--input',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path);p.add_argument('--key',type=pathlib.Path,required=True);a=p.parse_args()
 if a.mode!='verify' and (not a.output or a.output.exists()):p.error('Specify a new, nonexistent --output file')
 if a.mode=='encrypt' and not a.key.exists():
  with a.key.open('xb') as stream:os.chmod(a.key,0o600);stream.write(os.urandom(32))
 key=a.key.read_bytes()
 if len(key)!=32:raise ValueError('Key must contain exactly 32 raw bytes')
 partial=a.output.with_name(a.output.name+'.partial') if a.output else None
 if partial and partial.exists():raise ValueError('Partial output exists; inspect before retrying')
 try:
  with a.input.open('rb') as source:
   if a.mode=='verify':digest=decrypt(source,None,key)
   else:
    with partial.open('xb') as target:
     os.chmod(partial,0o600);digest=encrypt(source,target,key) if a.mode=='encrypt' else decrypt(source,target,key)
    partial.replace(a.output)
 except Exception:
  if partial and partial.exists():partial.unlink()
  raise
 print('verifiedPlaintextSha256='+digest)
if __name__=='__main__':main()
