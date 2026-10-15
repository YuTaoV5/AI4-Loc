"""Opt-in, isolated scheduler observation. Never installed into production.

The import hook is inherited by spawned SGLang processes through PYTHONPATH.
No CUDA synchronization is inserted: timestamps are host-side observations.
"""
import os
if os.environ.get('AI4LOC_KV_TRACE'):
    import sys, importlib.abc, importlib.machinery, time, json, dataclasses
    class Loader(importlib.abc.Loader):
        def __init__(self, original): self.original = original
        def create_module(self, spec):
            return self.original.create_module(spec) if hasattr(self.original, 'create_module') else None
        def exec_module(self, module):
            self.original.exec_module(module)
            cls = module.Scheduler
            def snapshot(self, batch, event):
                start = time.perf_counter_ns()
                try:
                    import torch
                    pool = dataclasses.asdict(self.pool_stats_observer.get_pool_stats())
                    requests = []
                    for r in getattr(batch, 'reqs', []):
                        requests.append({'rid': r.rid, 'input_tokens': len(r.origin_input_ids),
                                         'output_tokens': len(r.output_ids),
                                         'prefix_tokens': len(r.prefix_indices),
                                         'extend_input_len': getattr(r, 'extend_input_len', None),
                                         'cached_tokens': getattr(r, 'cached_tokens', None)})
                    row = {'event': event, 'wall_ns': time.time_ns(), 'mono_ns': time.monotonic_ns(),
                           'pid': os.getpid(), 'forward_mode': str(getattr(batch, 'forward_mode', '')),
                           'pool': pool, 'requests': requests, 'queued': len(self.waiting_queue),
                           'kv_capacity': self.max_total_num_tokens,
                           'torch_allocated_bytes': torch.cuda.memory_allocated(),
                           'torch_reserved_bytes': torch.cuda.memory_reserved(),
                           'torch_peak_allocated_bytes': torch.cuda.max_memory_allocated()}
                    row['observation_us'] = (time.perf_counter_ns() - start) / 1000
                    with open(os.environ['AI4LOC_KV_TRACE'] + '.' + str(os.getpid()) + '.jsonl', 'a') as f:
                        f.write(json.dumps(row) + '\n')
                except Exception as e:
                    with open(os.environ['AI4LOC_KV_TRACE'] + '.errors', 'a') as f: f.write(repr(e) + '\n')
            for name in ['run_batch', 'process_batch_result']:
                original = getattr(cls, name)
                def wrap(original, name):
                    def traced(self, batch, *args, **kwargs):
                        if os.environ.get('AI4LOC_KV_TRACE_DISABLE_FILE') and os.path.exists(os.environ['AI4LOC_KV_TRACE_DISABLE_FILE']):
                            return original(self, batch, *args, **kwargs)
                        snapshot(self, batch, name + '.before')
                        value = original(self, batch, *args, **kwargs)
                        snapshot(self, batch, name + '.after')
                        return value
                    return traced
                setattr(cls, name, wrap(original, name))
    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname != 'sglang.srt.managers.scheduler': return None
            spec = importlib.machinery.PathFinder.find_spec(fullname, path)
            spec.loader = Loader(spec.loader)
            return spec
    sys.meta_path.insert(0, Finder())
