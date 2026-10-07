"""Cross-platform real tool smoke experiments with generated ELF fixtures."""
import argparse, json, os, pathlib, shutil, subprocess, time

parser=argparse.ArgumentParser()
parser.add_argument('--output',default='data/tool-evidence')
parser.add_argument('--bin')
parser.add_argument('--source-root')
parser.add_argument('--rg')
args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parent.parent.parent
output=pathlib.Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
if args.bin:os.environ['PATH']=str(pathlib.Path(args.bin).resolve())+os.pathsep+os.environ['PATH']
results=[]
def run(name,argv,required=()):
    start=time.perf_counter()
    result=subprocess.run(argv,capture_output=True,text=True,timeout=90,errors='replace')
    ok=result.returncode==0 and all(x in result.stdout+result.stderr for x in required)
    results.append({'name':name,'command':argv,'passed':ok,'seconds':round(time.perf_counter()-start,4),'output':(result.stdout+result.stderr)[:6000]})
    if not ok:raise RuntimeError(name+': '+result.stderr[:500])
    return result.stdout
clang=shutil.which('clang');rg=args.rg or shutil.which('rg')
fixture=root/'tools/kernel-debug/fixture.c'
for arch in ['x86_64','aarch64']:
    obj=output/('fixture-'+arch+'.o')
    run('compile-'+arch,[clang,'--target='+arch+'-linux-gnu','-g','-O0','-c',str(fixture),'-o',str(obj)])
    run('ELF-symbols-'+arch,[shutil.which('llvm-readelf'),'-h','-s',str(obj)],['ELF64','crash_site'])
    run('disassembly-'+arch,[shutil.which('llvm-objdump'),'-d','--disassemble-symbols=crash_site',str(obj)],['crash_site'])
    run('DWARF-line-'+arch,[shutil.which('llvm-symbolizer'),'--obj='+str(obj),'crash_site'],['fixture.c:'])
big=output/'large.log'
with big.open('wb') as file:
    chunk=b'[  12.123456] synthetic stress heartbeat: no kernel failure in this row\n'*10000
    for _ in range(150):file.write(chunk)
    file.write(b'[  13.0] BUG: KASAN: slab-out-of-bounds in probe_fault\n')
run('large-log-search',[rg,'-n','-F','slab-out-of-bounds',str(big)],['1500001:'])
results[-1]['inputBytes']=big.stat().st_size
if args.source_root:
    run('kernel-source-search',[rg,'-n','-F','perf_event_release_kernel',str(pathlib.Path(args.source_root)/'kernel/events/core.c')],['perf_event_release_kernel'])
if os.name!='nt':
    run('GNU-symbol-inspection',[shutil.which('readelf'),'-s',str(output/'fixture-x86_64.o')],['crash_site'])
    run('GDB-symbol-inspection',[shutil.which('gdb'),'-batch','-ex','file '+str(output/'fixture-x86_64.o'),'-ex','info address crash_site','-ex','disassemble crash_site'],['crash_site'])
    for tool in ['crash','strace']:
        run(tool+'-availability',[shutil.which(tool),'--version'])
    try:
        import drgn
        results.append({'name':'drgn-import','passed':True,'version':drgn.__version__,'boundary':'No real vmcore provided; kernel-memory diagnosis remains untested.'})
    except ImportError:pass
else:
    coff=output/'fixture-win.obj';exe=output/'fixture-win.exe';pdb=output/'fixture-win.pdb'
    run('compile-COFF',[clang,'--target=x86_64-pc-windows-msvc','-g','-gcodeview','-fno-stack-protector','-c',str(fixture),'-o',str(coff)])
    run('link-PDB',[shutil.which('ld.lld'),'-flavor','link','/entry:entry','/subsystem:console','/debug','/nodefaultlib','/out:'+str(exe),'/pdb:'+str(pdb),str(coff)])
    run('PDB-public-symbols',[shutil.which('llvm-pdbutil'),'dump','-summary','-publics',str(pdb)],['crash_site','Has Debug Info: true'])
result={'platform':os.name,'syntheticFixtures':True,'results':results,'passed':all(x['passed'] for x in results)}
(output/'tools.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'platform':os.name,'passed':result['passed'],'experiments':len(results),'largeLogBytes':big.stat().st_size,'report':str(output/'tools.json')}))
