"""Download pinned, verified kernel diagnosis binaries into ignored project cache."""
import hashlib, json, os, pathlib, tarfile, urllib.request, zipfile
root=pathlib.Path(__file__).resolve().parent.parent/'data/toolchains'
downloads=root/'downloads';downloads.mkdir(parents=True,exist_ok=True)
assets=[
 ('windows','https://github.com/BurntSushi/ripgrep/releases/download/15.2.0/ripgrep-15.2.0-x86_64-pc-windows-msvc.zip','71b2fef860abe467217a538ff31de02f5258807c0129f771846f87bd029aafc5'),
 ('windows','https://github.com/mstorsjo/llvm-mingw/releases/download/20260922/llvm-mingw-20260922-ucrt-x86_64.zip','e3ad77d117a4bea19a7a3b333341824d79a5a371004a10e25b8504e7b3047666'),
 ('linux','https://github.com/BurntSushi/ripgrep/releases/download/15.2.0/ripgrep-15.2.0-x86_64-unknown-linux-musl.tar.gz','33e15bcf1624b25cdd2a55813a47a2f95dbe126268203e76aa6a585d1e7b149c')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for platform,url,digest in assets:
 p=downloads/url.rsplit('/',1)[1]
 if not p.exists() or sha(p)!=digest:
  print('Downloading',p.name,flush=True)
  with urllib.request.urlopen(url,timeout=120) as response,p.open('wb') as output:
   while chunk:=response.read(1024*1024):output.write(chunk)
 if sha(p)!=digest:raise RuntimeError('SHA256 mismatch: '+p.name)
 target=root/platform;target.mkdir(exist_ok=True)
 if p.suffix=='.zip':
  with zipfile.ZipFile(p) as archive:
   for name in archive.namelist():
    q=pathlib.PurePosixPath(name)
    if q.is_absolute() or '..' in q.parts:raise ValueError('Unsafe archive member')
   archive.extractall(target)
 else:
  with tarfile.open(p) as archive:archive.extractall(target,filter='data')
 print('Verified',p.name,flush=True)
(root/'verified-downloads.json').write_text(json.dumps(assets,indent=2))
print('Linux: install distro llvm/clang, binutils, gdb, crash and strace; see docs/KERNEL_TOOLKIT.md.')
