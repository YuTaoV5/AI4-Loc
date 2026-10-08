"""Read-only capability preflight; no inference, fault injection or service mutation."""
import argparse, json, os, pathlib, platform, shutil, subprocess, sys, urllib.request

def inspect(full=False, check_model=False):
    root=pathlib.Path(__file__).resolve().parent.parent
    checks={}
    def check(name, ok, detail): checks[name]={'ok': bool(ok), 'detail': str(detail)}
    for name in ['node','git','curl'] + (['bwrap','rg','llvm-readelf','llvm-objdump','llvm-symbolizer','gdb','crash','qemu-system-x86_64','java','dot','make','cc','flex','bison','bc','cpio'] if full else []):
        check(name, shutil.which(name), shutil.which(name) or 'missing')
    check('node_modules', (root/'node_modules/express/package.json').is_file(), 'npm ci --omit=dev --ignore-scripts')
    if shutil.which('node'):
        try:
            version=subprocess.check_output(['node','-p','process.versions.node'],text=True,timeout=10).strip()
            check('nodeVersion',int(version.split('.')[0])>=20,version+' (requires >=20)')
        except Exception as error:check('nodeVersion',False,type(error).__name__)
    if full:
        check('linux', sys.platform=='linux', platform.platform())
        check('nonRoot', hasattr(os,'geteuid') and os.geteuid()!=0, 'dedicated non-root user required')
        python=os.environ.get('KERNEL_AGENT_PYTHON','')
        check('agentPython', python and pathlib.Path(python).is_file(), python or 'KERNEL_AGENT_PYTHON missing')
        check('sandbox', pathlib.Path(os.environ.get('KERNEL_AGENT_SANDBOX','/nonexistent')).is_file(), 'KERNEL_AGENT_SANDBOX required')
        check('modelName', os.environ.get('KERNEL_AGENT_MODEL'), 'KERNEL_AGENT_MODEL')
        check('modelUrl', os.environ.get('KERNEL_AGENT_BASE_URL'), 'KERNEL_AGENT_BASE_URL')
        check('plantumlJar', pathlib.Path(os.environ.get('PLANTUML_JAR','/nonexistent')).is_file(), 'PLANTUML_JAR')
    dataset=os.environ.get('KERNEL_BENCHMARK_DIR')
    if dataset: check('benchmarkManifest',(pathlib.Path(dataset)/'manifest.json').is_file(),dataset)
    if check_model:
        try:
            native=os.environ.get('KERNEL_AGENT_TRANSPORT')=='ollama-native'
            endpoint=os.environ['KERNEL_AGENT_BASE_URL'].rstrip('/')+('/api/tags' if native else '/models')
            headers={}
            if os.environ.get('KERNEL_AGENT_API_KEY'):headers['Authorization']='Bearer '+os.environ['KERNEL_AGENT_API_KEY']
            with urllib.request.urlopen(urllib.request.Request(endpoint,headers=headers),timeout=10) as response: data=json.load(response)
            names=[m.get('name',m.get('model')) for m in data.get('models',[])] if native else [m.get('id') for m in data.get('data',[])]
            check('modelConnected',os.environ.get('KERNEL_AGENT_MODEL') in names,'configured model listed by API')
        except Exception as error:check('modelConnected',False,type(error).__name__)
    return {'schema':'ai4loc-deployment-doctor/v1','fullRequested':full,'ok':all(c['ok'] for c in checks.values()),'checks':checks,
            'limits':'Static dependency checks only; sandbox startup, inference, business acceptance and causal replay need separate validation.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--full',action='store_true');parser.add_argument('--check-model',action='store_true');args=parser.parse_args()
    report=inspect(args.full,args.check_model);print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(0 if report['ok'] else 1)
