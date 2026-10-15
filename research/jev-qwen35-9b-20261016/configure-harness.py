"""Prepare independent model arms from a frozen concurrency harness."""
import pathlib
E=pathlib.Path(__file__).resolve().parent
p=E/'benchmark.py';s=p.read_text()
if "MODEL = 'AI4Loc-Qwen9B'" in s:
    print('Harness already configured; no mutation')
    raise SystemExit(0)
s=s.replace('itertools, sys, subprocess, re','itertools, sys, subprocess, re, os')
s=s.replace("E = pathlib.Path(__file__).resolve().parent","E = pathlib.Path(os.environ.get('AI4LOC_RUN_DIR', pathlib.Path(__file__).resolve().parent))")
s=s.replace("MODEL = 'Qwen3.8-27B-SystemOne'","MODEL = 'AI4Loc-Qwen9B'")
s=s.replace("/root/gpufree-data/systemone/models/Qwen3.8-27B","/root/gpufree-data/systemone/models/Qwen3.5-9B")
s=s.replace("'mem_fraction_static':0.78","'mem_fraction_static':0.55")
s=s.replace("'reason':'production 0.70/auto9 state slots silently capped effective concurrency to one; production restored unchanged'","'reason':'identical isolated Qwen3.5-9B runtime in both checkpoint arms; production restored unchanged'")
s=s.replace("'seed':20261015","'seed':20261015,'checkpoint_arm':os.environ.get('AI4LOC_CHECKPOINT_ARM')")
assert "Qwen3.8-27B" not in s
p.write_text(s)
