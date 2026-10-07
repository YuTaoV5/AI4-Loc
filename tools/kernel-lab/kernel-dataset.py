"""Portable validation and answer-free input export CLI."""
import argparse,json,pathlib
from dataset_contract import validate,export_view,PROFILES
p=argparse.ArgumentParser();p.add_argument('action',choices=['validate','export']);p.add_argument('root',type=pathlib.Path);p.add_argument('--case');p.add_argument('--profile',choices=PROFILES,default='log+artifacts+source');p.add_argument('--destination',type=pathlib.Path);a=p.parse_args()
if a.action=='validate':
    report=validate(a.root);print(json.dumps(report,indent=2));raise SystemExit(0 if report['complete'] else 2)
if not a.case or not a.destination:p.error('export requires --case and --destination')
report=validate(a.root)
if not report['complete']:raise SystemExit('Refusing export from incomplete dataset: '+str(report['errors']))
export_view(a.root,a.case,a.profile,a.destination)
