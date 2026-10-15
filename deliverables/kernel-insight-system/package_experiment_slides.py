"""Bundle the offline presentation plus all three complete public study directories."""
import pathlib,json,hashlib,zipfile
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OUT=ROOT/'deliverables/releases';OUT.mkdir(exist_ok=True)
NAME='AI4Loc_模型微调动图_Slide与完整公开数据_20261016.zip'
folders=[HERE,ROOT/'research/kv-concurrency-20261015',ROOT/'research/kv-concurrency-20261016',ROOT/'research/jev-qwen35-9b-20261016']
files=sorted(p for folder in folders for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.pyc'))
assert all('local-archive' not in p.parts and not p.name.endswith('.tgz') for p in files)
intro='''# AI4Loc 模型微调、并发实验、动态回放和完整公开数据

新版70页，输入59看Qwen3.5-9B模型与微调章节，9个新GIF在media/finetune。
396条真实训练记录、87例配对结果、校准与16种性能回放，完整Agent负结果均保留。
research/jev-qwen35-9b-20261016含本轮全部公开数据与详细报告。
新增动图口径：deliverables/kernel-insight-system/模型微调动图与数据说明.md。
训练实际秒与机制教学步分开标注；GIF约10秒回放+2秒末帧。

解压后双击 deliverables/kernel-insight-system/deck.html，输入49进入此前27B并发章节。
5个GIF在同目录media/kv。方向键翻页、P播放、J/K事件走步，56页切换八种条件。
完整字段说明：deliverables/kernel-insight-system/实验数据与动图说明.md。
完整报告及所有公开逐请求、KV、状态、token、NVML记录：research/kv-concurrency-20261016。
生产原配置启动区段校准：research/kv-concurrency-20261015，独立保存不可混合分母。
70页逐页演讲稿、发布清单、预览、执行源码和离线重建脚本均随包附带。

旧5个并发GIF为8秒教学回放+2秒停留；新增9个约10秒+2秒停留。
实测动画打印t为真实相对秒；机制动画仅标教学步。交互版推理可原速播放。
两端同一时间尺，不会单独加速较慢组；token只在原生prefill完成时结算。
业务原始日志、完整私有请求、账号、模型权重和可下载内核源码不在公开包中。
只看演示不需要服务器或Python；重建请查requirements-render.txt。
'''
def entry(tar,name,content):
    z=zipfile.ZipInfo(name,date_time=(2026,10,16,0,0,0));z.compress_type=zipfile.ZIP_DEFLATED;z.external_attr=0o100644<<16;tar.writestr(z,content)
with zipfile.ZipFile(OUT/NAME,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as tar:
    entry(tar,'打开说明.md',intro.encode())
    for p in files:entry(tar,p.relative_to(ROOT).as_posix(),p.read_bytes())
with zipfile.ZipFile(OUT/NAME) as tar:
    assert tar.testzip() is None
    for p in files:assert hashlib.sha256(tar.read(p.relative_to(ROOT).as_posix())).digest()==hashlib.sha256(p.read_bytes()).digest()
value={'file':NAME,'bytes':(OUT/NAME).stat().st_size,'sha256':hashlib.sha256((OUT/NAME).read_bytes()).hexdigest(),
       'files':len(files)+1,'slides':70,'gifs':14,'studies':['20261015 calibration','20261016 fault-window main','20261016 Qwen3.5-9B training and inference'],
       'verified_each_member':True,'private_inputs_included':False,'model_weights_included':False}
(OUT/'模型微调动图与数据包校验_20261016.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value,ensure_ascii=False,indent=2))
