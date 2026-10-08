# Kernel Decision plugin for dsh

Native Cordis tool plugin `index.mjs` exports `name`, `inject=['tools']`, and `apply(ctx, config)`. It registers `kernel_decide` through `ctx.tools.register`; registrations follow dsh lifecycle cleanup. No separate Node dependency download is needed. Trusted deployment configuration supplies Python, the shared bridge, a single task workspace and the model URL; model tool arguments cannot change paths, endpoints, or select scripts.

The Python backend `scripts/decision_plugin.py` supports SGLang `/v1/decisions` choice / yes_no / score. It pins prompt format v1, requests prompt and label token IDs, validates finite normalized probabilities and label mass, and stores request/response/usage/timing in `decision-trace.json`. Thinking is disabled by the server; zero completion tokens is checked. Probabilities rank evidence and are not calibrated root-cause probabilities. No arbitrary confidence threshold grants access or establishes correctness.

The same backend is used by the production bounded localization loop via `request.decisionPlugin`. Its default adaptive policy first performs existing read-only preflight, and asks Decision to rank source candidates when an observed instruction pointer is missing from inspected definitions. Symbol selection uses actual RIP/PC and non-speculative module frames, without dataset case IDs, family truth, reference locations or fix labels. Citation validation, missing-material restrictions and Build ID checks remain authoritative. An `adaptive-rule` variant omits Decision inference for ablation; an always-on `decision` policy is experimental and costs more requests.

## Native dsh overlay

Create a per-task JSON patch with absolute trusted paths:

```json
[{"insert":[{"id":"kernel-decision","name":"/srv/ai4loc/plugins/kernel-decision/index.mjs","config":{"python":"/srv/ai4loc/data/linux-runtime/venv/bin/python","bridge":"/srv/ai4loc/scripts/decision_plugin.py","workspace":"/srv/ai4loc/data/linux-local/agent-runs/<task-id>","baseUrl":"http://127.0.0.1:30000"}}]}]
```

Pass that filename to `DeepSeekHarness(..., patches=(patch_path,))`, or `dsh --patch`. `agent-runner.py` creates the per-task overlay automatically for the legacy dsh engine when the request has `decisionPlugin`. The SDK chat provider remains configured separately: a Decision endpoint is not a text/chat provider. This server's initial direct SGLang SDK chat attempt returned HTTP 400; the successful native SDK smoke used the existing project Ollama compatibility adapter for generation and SGLang for decisions. All attempts are retained.

For the closed-loop web engine set `KERNEL_DECISION_BASE_URL=http://127.0.0.1:30000`; server forwards it as trusted request configuration, using adaptive policy. This requires the plugin Python code and native plugin directory in the deployed release. Sandbox mounts the release's plugin directory read-only. Use a new release and retain rollback; do not modify external model services or dataset labels to increase a score.

## Evaluation

`scripts/run-decision-experiment.py` executes adaptive, deterministic-rule ablation and warm-baseline variants sequentially, refuses to overwrite output directories, and preserves run logs, analyses, actual tool records and model HTTP counts. Decision HTTP calls count toward the same total request budget as generation; their independent question/prefill count is recorded separately. The original always-on and initial cold baseline remain separate artifacts. This experiment measures the application's bounded localization loop; native dsh load/tool execution is verified separately and is not falsely presented as a full dsh benchmark.

Reference: [SGLang Decision models](https://docs.sglang.io/docs/supported-models/decision_models), [dsh tool plugin contract](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/tool).

## Fast boundary + Chat causal analysis (2026-10-09)

Set `KERNEL_BOUNDARY_ROUTER=decision` together with `KERNEL_DECISION_BASE_URL` to use the split pipeline. It batches first-diagnostic family, execution stage and reporting detector questions. A boundary event is emitted before source retrieval and Chat analysis. Classification is a fallible hint; root-cause tools and citation validation remain available. Healthy/unknown is not proof of health, and a reporting detector is not necessarily the faulty owner.

The native overlay accepts trusted `mode:"boundary"` and registers `kernel_boundary`; omitted mode retains `kernel_decide`. `agent-runner.py` creates that overlay for `request.boundaryRouter`. `KERNEL_DECISION_API=systemone` explicitly enables the dedicated-checkpoint request shape, with `KERNEL_DECISION_MODEL` as its model alias. Raw responses are preserved; missing full-vocabulary label mass is not fabricated. A specialized readout model needs a separate Chat provider. See `docs/SGLANG_JEV_LIKE_DEPLOYMENT.md`.

New offline evaluations use anonymous UUID workspaces and a bubblewrap namespace without evaluator/dataset-parent mounts or a mounted proc filesystem. Labels are loaded after worker exit. `source_read` excludes collector scripts and metadata. Use `scripts/benchmark-boundary-router.py` for repeated randomized same-checkpoint triage comparisons, and `scripts/run-hybrid-experiment.py` for isolated causal-analysis control/hybrid runs. Never describe the previously inspected test split as unseen.
