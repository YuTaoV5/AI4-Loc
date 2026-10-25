"""Trusted structured scoring. A reported quote must exist in input and support the gold fact."""
import json,pathlib,re,zipfile
WEIGHTS={'stage':20,'component':20,'mechanism':20,'evidence':30,'nextAction':10}
def parse(text):
 text=text.strip();m=re.fullmatch(r'```(?:json)?\s*([\s\S]*?)\s*```',text)
 value=json.loads(m.group(1) if m else text)
 if not isinstance(value,dict):raise ValueError('Diagnosis must be a JSON object')
 return value

def score(prediction,gold,archive):
 fields={k:prediction.get(k)==gold[k] for k in ['stage','component','mechanism','nextAction']}
 with zipfile.ZipFile(archive) as z:
  files={n:z.read(n).decode('utf-8',errors='replace') for n in z.namelist() if not n.endswith('/')}
 claimed=prediction.get('evidence',[])
 fields['evidence']=isinstance(claimed,list) and all(any(isinstance(p,dict) and p.get('file')==g['file'] and isinstance(p.get('quote'),str) and 0<len(p['quote'])<=1000 and g['quote'] in p['quote'] and p['quote'] in files.get(g['file'],'') for p in claimed) for g in gold['evidence'])
 # At least one valid evidence item; arbitrary unrelated text earns no evidence credit.
 return {'points':sum(WEIGHTS[k] for k,v in fields.items() if v),'checks':fields,'weights':WEIGHTS}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('prediction',type=pathlib.Path);p.add_argument('gold',type=pathlib.Path);p.add_argument('archive',type=pathlib.Path);a=p.parse_args();print(json.dumps(score(parse(a.prediction.read_text(encoding='utf-8-sig')),json.loads(a.gold.read_text(encoding='utf-8-sig')),a.archive)))
