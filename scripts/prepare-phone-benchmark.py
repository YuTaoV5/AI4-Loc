"""Build deterministic, explicitly synthetic phone incident bundles; answers stay outside ZIPs."""
import argparse,hashlib,json,pathlib,zipfile
STAGES=['xloader','bl2','bl31','uefi','kernel','android']
SCENARIOS=[
 ('healthy','none','none','none','confirm_normal',None),
 ('ddr','bl2','ddr','ddr_training_failure','check_ddr','DDR training failed channel=1 error=0x31'),
 ('handoff','bl31','secure_monitor','handoff_failure','check_handoff','handoff rejected: non-secure entry address outside allowed DRAM'),
 ('avb','uefi','verified_boot','image_verification_failure','verify_image','AVB boot_a digest mismatch; verification failed; refusing boot'),
 ('storage','kernel','ufs','storage_io_timeout','check_storage','ufshcd: command timeout tag=7; SCSI READ failed; errno=-110'),
 ('zygote','android','zygote','zygote_restart_loop','inspect_crash','init: Service zygote exited status=1; restart_count=8'),
 ('encrypted','unknown','unknown','insufficient_evidence','request_decoding',None),
 ('missing','unknown','unknown','insufficient_evidence','request_early_logs',None),
]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(root):
 root=pathlib.Path(root);root.mkdir(parents=True,exist_ok=True);cases=[];gold={}
 for n,(scenario,stage,component,mechanism,action,error) in enumerate(SCENARIOS):
  cid=hashlib.sha256(('phone-synthetic-v1:'+str(n)).encode()).hexdigest()[:16];folder=root/'cases'/cid;folder.mkdir(parents=True,exist_ok=True)
  boot='sim-'+cid[:8];files={'metadata.json':json.dumps({'synthetic':True,'platform':'illustrative-mobile-tfa-uefi','bootId':boot,'warning':'Constructed test data; not captured from a real phone.'})}
  baseline={'xloader':'storage initialized; loading BL2','bl2':'DDR training passed; loading BL31','bl31':'runtime services ready; exit to non-secure UEFI','uefi':'AVB verification passed; launching Linux','kernel':'Linux version 6.6.0-synthetic; init mounted userdata','android':'init: zygote ready; system_server ready; sys.boot_completed=1'}
  evidence=[]
  if scenario=='encrypted':
   files['vendor.bin']=b'PHONE-SYNTHETIC-ENCRYPTED\x00\xff\x01\x9a';files['capture.txt']='vendor payload encrypted; codec and key unavailable';evidence=[{'file':'capture.txt','quote':files['capture.txt']}]
  elif scenario=='missing':
   files['android.log']='boot='+boot+' boot attempt=2; reboot_reason=watchdog; early boot logs unavailable'
   evidence=[{'file':'android.log','quote':'early boot logs unavailable'}]
  else:
   last=STAGES.index(stage) if stage in STAGES else 5
   for i,s in enumerate(STAGES[:last+1]):
    message=error if s==stage else baseline[s]
    files[s+'.log']=f'boot={boot} attempt=1 t={i+1}.000 [{s}] {message}\n'
    if s==stage:evidence.append({'file':s+'.log','quote':error})
   if scenario=='healthy':evidence=[{'file':'android.log','quote':'sys.boot_completed=1'}]
   if scenario=='storage':
    files['android.log']=f'boot={boot} attempt=1 t=6.000 [android] vold: userdata mount failed EIO; system_server waiting for storage\n'
  package=folder/'input.zip'
  with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
   for name,value in files.items():
    item=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,value.encode() if isinstance(value,str) else value)
  cases.append({'id':cid,'origin':'synthetic','archive':f'cases/{cid}/input.zip','sha256':digest(package),'bytes':package.stat().st_size,'stagesPresent':[s for s in STAGES if s+'.log' in files]})
  gold[cid]={'stage':stage,'component':component,'mechanism':mechanism,'nextAction':action,'evidence':evidence}
 manifest={'schema':'phone-benchmark/v1','version':'phone-synthetic-v1','synthetic':True,'platformNote':'Illustrative platform, not a universal vendor boot sequence. Early fatal failures truncate later stages.','cases':cases}
 (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 private=root/'private';private.mkdir(exist_ok=True);(private/'gold.json').write_text(json.dumps(gold,indent=2),encoding='utf-8')
 return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output',type=pathlib.Path);a=p.parse_args();print(json.dumps({'cases':len(build(a.output)['cases']),'directory':str(a.output)}))
