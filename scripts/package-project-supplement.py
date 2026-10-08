"""Build a private GitHub supplement, excluding downloaded sources and dependencies."""
import datetime, hashlib, io, json, os, pathlib, shutil, subprocess, tarfile, tempfile, zipfile

ROOT=pathlib.Path(__file__).resolve().parent.parent
BASE='711319f15b49b9391205aa8e142cbe012688f541'
OUT=ROOT/'data/deployment/AI4Loc-supplement-20261007.zip'
SKIP={'node_modules','.git','.cache','__pycache__','source','source-tree','source-context','downloads'}
DATA_SKIP={'deployment','server-snapshots','source-repositories','kernels','toolchains','diagram-runtime','diagram-cache','local-archive','test-tmp','linux-runtime','ui-validation'}

RESTORE=r'''import argparse, datetime, hashlib, json, pathlib, shutil, subprocess
p=argparse.ArgumentParser();p.add_argument('project',type=pathlib.Path);a=p.parse_args()
bundle=pathlib.Path(__file__).resolve().parent
manifest=json.loads((bundle/'MANIFEST.json').read_text(encoding='utf-8'))
target=a.project.resolve()
head=subprocess.check_output(['git','-C',str(target),'rev-parse','HEAD'],text=True).strip()
if head!=manifest['githubCommit']:raise SystemExit('Git HEAD differs from required base; checkout '+manifest['githubCommit'])
def digest(file):
 h=hashlib.sha256()
 with file.open('rb') as f:
  while b:=f.read(4*1024*1024):h.update(b)
 return h.hexdigest()
backup=target/'data/local-archive'/('before-supplement-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
for row in manifest['files']:
 source=(bundle/row['storedPath']).resolve();dest=(target/row['target']).resolve()
 if not source.is_relative_to(bundle) or not dest.is_relative_to(target):raise SystemExit('Unsafe manifest path')
 if digest(source)!=row['sha256']:raise SystemExit('Checksum mismatch: '+row['storedPath'])
 if dest.is_file():
  if digest(dest)==row['sha256']:continue
  old=backup/row['target'];old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,old)
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
 if row.get('executable'):dest.chmod(dest.stat().st_mode|0o111)
print('Merged',len(manifest['files']),'files. Existing different files were backed up under',backup)
'''

def excluded(rel):
    parts=rel.parts
    if any(p in SKIP for p in parts):return True
    if parts[0]=='tools' and len(parts)>1 and parts[1]=='kelip-slide':return True
    if parts[0]=='data' and len(parts)>1 and parts[1] in DATA_SKIP:return True
    if rel.name in {'source.tar.gz','source.tar.xz'} or rel.suffix in {'.pyc','.o','.a'} or rel.name.endswith('.cmd'):return True
    if 'bootstages' in parts and 'cfg' in parts:
        if parts[-1]=='cfg':return False
        return rel.name not in {'vmlinux','bzImage','System.map','.config','kernel.config'}
    if 'bootstages' in parts and 'irfs' in parts:return True
    return False

def main():
    tracked=set(subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True).splitlines())
    changed=set(subprocess.check_output(['git','diff',BASE,'--name-only'],cwd=ROOT,text=True).splitlines())
    rows=[];seen={};excluded_counts={'githubUnchanged':0,'regenerable':0};OUT.parent.mkdir(parents=True,exist_ok=True)
    partial=OUT.with_suffix('.zip.part')
    with zipfile.ZipFile(partial,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
        def add(stream,target,size,executable=False):
            h=hashlib.sha256()
            with tempfile.SpooledTemporaryFile(max_size=8*1024*1024,dir=OUT.parent) as temp:
                while block:=stream.read(4*1024*1024):h.update(block);temp.write(block)
                digest=h.hexdigest()
                stored=seen.get(digest)
                if stored is None:
                    stored='payload/'+target;temp.seek(0)
                    info=zipfile.ZipInfo(stored);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o100755 if executable else 0o100600)<<16
                    with archive.open(info,'w',force_zip64=True) as dest:shutil.copyfileobj(temp,dest,4*1024*1024)
                    seen[digest]=stored
                rows.append({'target':target,'storedPath':stored,'bytes':size,'sha256':digest,'executable':executable})
        for directory,dirs,files in os.walk(ROOT,followlinks=False):
            base=pathlib.Path(directory)
            dirs[:]=[d for d in dirs if not excluded((base/d).relative_to(ROOT)) and not (base/d).is_symlink()]
            for name in sorted(files):
                file=base/name;rel=file.relative_to(ROOT);key=rel.as_posix()
                if file.is_symlink() or excluded(rel):excluded_counts['regenerable']+=1;continue
                if key in tracked and key not in changed:excluded_counts['githubUnchanged']+=1;continue
                # Linux shell content must remain LF even when the local checkout uses CRLF.
                if file.suffix=='.sh':
                    content=file.read_bytes().replace(b'\r\n',b'\n');add(io.BytesIO(content),key,len(content),True)
                else:
                    with file.open('rb') as source:add(source,key,file.stat().st_size)
            print('PACK',base.relative_to(ROOT).as_posix(),len(rows),flush=True) if base==ROOT/'data/datasets/stability-v1/shared' else None
        # Keep remote business state separate: do not overwrite the local demo accounts.
        snapshot=ROOT/'data/server-snapshots/20261007-full/service.tar.gz'
        print('Reading private server snapshot (dependencies and source caches excluded)',flush=True)
        with tarfile.open(snapshot,'r|gz') as source:
            for member in source:
                parts=pathlib.PurePosixPath(member.name).parts
                if not member.isfile() or len(parts)<2:continue
                rel=pathlib.PurePosixPath(*parts[1:])
                if rel.parts[0]!='data' and str(rel) not in {'supervisord.conf','verified-source-registry.json'}:continue
                if any(p in SKIP for p in rel.parts) or any(p in {'kernels','backups','tool-evidence','npm-cache','.java'} for p in rel.parts):continue
                if rel.name in {'source.tar.gz','source.tar.xz','supervisor.pid'} or rel.suffix in {'.pyc','.o','.a'}:continue
                with source.extractfile(member) as stream:add(stream,'data/restored-server/'+rel.as_posix(),member.size,bool(member.mode&0o111))
        manifest={'schema':'ai4loc-github-supplement/v1','githubRepository':'https://github.com/YuTaoV5/AI4-Loc.git','githubCommit':BASE,
                  'createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'private':True,'files':rows,
                  'uniquePayloads':len(seen),'logicalBytes':sum(r['bytes'] for r in rows),'exclusions':excluded_counts}
        archive.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        archive.writestr('merge_into_project.py',RESTORE)
        archive.writestr('README-合并与恢复.md',README)
    partial.replace(OUT)
    print('Verifying every compressed entry and CRC...',flush=True)
    with zipfile.ZipFile(OUT) as archive:
        bad=archive.testzip()
        if bad:raise RuntimeError('ZIP CRC failed: '+bad)
        if 'payload/data/datasets/stability-v1/shared/source.tar.gz' in archive.namelist():raise RuntimeError('Source archive unexpectedly included')
    h=hashlib.sha256()
    with OUT.open('rb') as source:
        while block:=source.read(4*1024*1024):h.update(block)
    result={'archive':str(OUT),'bytes':OUT.stat().st_size,'sha256':h.hexdigest(),'files':len(rows),'uniquePayloads':len(seen),'crcVerified':True,'githubCommit':BASE}
    OUT.with_suffix('.zip.sha256').write_text(h.hexdigest()+'  '+OUT.name+'\n',encoding='ascii')
    OUT.with_suffix('.summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

README='''# AI4Loc：GitHub 补充包（含私有业务数据）

本包不能单独替代 GitHub 项目。它包含 GitHub 未上传的数据集、真实实验日志、定位轨迹、匹配编译产物、注入源码/补丁、本地新文档与部署修改，以及服务器文件备份中的私有业务状态。只用于受控本地恢复，不上传 GitHub 或公开分享。

## 合并步骤
1. 从 GitHub 获取代码并固定版本：
   git clone https://github.com/YuTaoV5/AI4-Loc.git AI4Loc
   git -C AI4Loc checkout 711319f15b49b9391205aa8e142cbe012688f541
2. 将本 ZIP 解压到独立目录，例如 supplement；不要直接解压覆盖项目。Windows 使用支持 ZIP64 的解压工具，Linux 可用 python3 -m zipfile -e 本包.zip supplement。
3. 执行 python supplement/merge_into_project.py AI4Loc（Windows 可使用 Python 3.10+；Linux 用 python3）。脚本核对 Git 提交和每个载荷的 SHA256，再恢复 manifest 指定路径。相同内容在包内仅保存一次，由脚本恢复所有必要路径，因此不要手动只复制 payload。
4. 原有不同文件自动备份到项目 data/local-archive/before-supplement-*。合并后遵循 docs/CROSS_PLATFORM_DEPLOYMENT.md 安装依赖、配置真实模型并启动。

## 数据与业务状态
data/datasets 下保存四个数据版本，data/experiments 保存实验与证据，其他审计目录保存指标和轨迹。本地网站演示数据与私有原数据分别保存，远端备份的服务数据放在 data/restored-server/data。不要直接混用两份 accounts/state：恢复旧业务可将 KERNEL_INSIGHT_DATA_DIR 指向该目录，并显式设置 KERNEL_BENCHMARK_DIR。
服务器 supervisord.conf、verified-source-registry.json 仅作历史配置证据，仍有原机器绝对路径，不能直接激活；应重新配置本机运行时和经核验源码注册表。业务状态来自 2026-10-07 的文件备份，不是数据库事务快照。模型权重和模型服务未包含。

## 已排除内容与重新获取
- GitHub 对应提交中未修改的全部文件，包括已上传的 slide、演讲稿和公开图表；本地新增或修改文件以覆盖文件形式附带。
- node_modules：运行 npm ci --omit=dev --ignore-scripts。
- Windows/Linux 工具、Java、PlantUML 下载及运行时：依跨平台部署文档和 scripts/setup-toolkit.py / setup-diagrams.cjs 重新安装。
- 内核源码树、源码压缩包、Git 历史、源码缓存、原始整套 lab/service/release 备份、编译 .o/.a 和临时构建目录：未打包。
- 历史运维辅助脚本、临时测试、浏览器运行时及缓存：未打包。

内核源码获取：严格数据集匹配 OpenHarmony kernel_linux_5.10，仓库 https://gitee.com/openharmony/kernel_linux_5.10.git ，commit f88704ae607f90518f67aee33790ac06d6ada77d。检出后按 data/datasets/stability-v1/shared/source.patch 和构建证据恢复补丁；注入模块源码在场景目录，启动变体要使用各自补丁/配置，不能拿另一个版本替代。其他内核版本依据各样本 manifest、日志及提交记录获取。
特别说明：依用户要求，本包也不含冻结的 shared/source.tar.gz。因此解包后原始数据集完整性校验会报告这个文件缺失；从 Git 重建的 tar.gz 不保证与原封版归档逐字节相同，不能修改原 manifest 哈希冒充通过。若需要原封版的逐字节复现，须另外取回完整主副本中的该冻结文件；若重建源码作为新材料，需另建版本并记录新哈希/构建身份。编译产物与不可再生的原始日志仍保留。

## 核验
MANIFEST.json 记录所有恢复路径、大小和 SHA256，重复文件通过 storedPath 指向单一载荷。外部 .zip.sha256 核验压缩包传输，生成程序已逐项读取 ZIP 验证 CRC。该包是补充交付，不表示新机器模型推理、WSL、沙箱和全业务已自动通过验收。
'''

if __name__=='__main__':main()
