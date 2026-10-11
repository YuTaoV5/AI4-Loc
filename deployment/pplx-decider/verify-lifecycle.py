"""Explicit stop/start check of this service only; preserves failed attempts as JSON."""
import argparse,json,pathlib,subprocess,time,sys
p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();home=pathlib.Path(__file__).resolve().parent
record={'checkedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'passed':False,'steps':[]}
try:
 record['oldPid']=json.loads((home/'state/process.json').read_text())['pid']
 for action in ['stop','start','status']:
  r=subprocess.run([sys.executable,str(home/'service.py'),action],capture_output=True,text=True,timeout=150)
  record['steps'].append({'action':action,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
  if r.returncode:raise RuntimeError(f'{action} failed')
 record['newPid']=json.loads((home/'state/process.json').read_text())['pid'];assert record['oldPid']!=record['newPid'];record['passed']=True
except Exception as error:record['error']=str(error);raise
finally:a.output.write_text(json.dumps(record,indent=2))
print(json.dumps(record))
