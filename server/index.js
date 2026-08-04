const express = require('express');
const multer = require('multer');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 8787;
const root = path.join(__dirname, '..');
const dataRoot = path.join(root, 'data');
const uploadRoot = path.join(dataRoot, 'uploads');
const reportRoot = path.join(dataRoot, 'reports');
[dataRoot, uploadRoot, reportRoot].forEach((folder) => fs.mkdirSync(folder, { recursive: true }));
app.use(express.json());
app.use(express.static(path.join(root, 'public')));

const upload = multer({
  dest: uploadRoot,
  limits: { fileSize: 1024 * 1024 * 1024 },
  fileFilter: (_, file, done) => done(null, /\.(zip|tar|gz|tgz)$/i.test(file.originalname))
});

const dashboardSeed = {
  kpis: { open: 38, medianMinutes: 46, accuracy: 91.4, coverage: 73.8 },
  locations: [
    { name: 'Nanchang', android: 64, ohos: 36, total: 100, trend: 12 },
    { name: 'Guangzhou', android: 51, ohos: 29, total: 80, trend: 8 },
    { name: 'Chengdu', android: 43, ohos: 22, total: 65, trend: 5 },
    { name: 'Wuhan', android: 36, ohos: 18, total: 54, trend: -3 }
  ],
  statuses: [
    { label: '未解决', value: 38, color: '#ef5b68' },
    { label: '定位中', value: 26, color: '#f5b94c' },
    { label: '实施修改', value: 19, color: '#5b8def' },
    { label: '结论审核', value: 11, color: '#47c7a5' }
  ],
  types: [
    { name: 'Crash / ANR', android: 31, ohos: 14 },
    { name: '启动稳定性', android: 22, ohos: 16 },
    { name: '内存泄漏', android: 18, ohos: 9 },
    { name: '卡顿 / 丢帧', android: 15, ohos: 12 },
    { name: '功耗异常', android: 9, ohos: 6 }
  ],
  timeline: [54, 61, 58, 70, 76, 73, 82, 88, 91, 96, 103, 112],
  radar: [86, 78, 92, 71, 88]
};
const benchmarkCases = [
  { id: 'BM-ANR-001', platform: 'Android', version: 'Nanchang R12', category: 'Crash / ANR', occurredAt: '2026-07-21 18:42:11', probability: 0.92, resetCause: 'watchdog timeout after RenderThread lock contention', falseLogs: ['normal GC pause', 'surface reconnect'], rootCause: 'BufferQueue lock contention', status: 'verified' },
  { id: 'BM-OHOS-002', platform: 'OHOS', version: 'Guangzhou 4.1', category: '启动稳定性', occurredAt: '2026-07-22 09:14:03', probability: 0.87, resetCause: 'Ability restart after cold-start timeout', falseLogs: ['network retry', 'bundle cache miss'], rootCause: 'UIAbility initialization race', status: 'verified' },
  { id: 'BM-MEM-003', platform: 'Android', version: 'Chengdu R11', category: '内存泄漏', occurredAt: '2026-07-23 13:08:55', probability: 0.89, resetCause: 'LMK reclaim after native heap growth', falseLogs: ['background trim', 'image cache eviction'], rootCause: 'Retained Activity context in observer', status: 'verified' },
  { id: 'BM-FPS-004', platform: 'OHOS', version: 'Nanchang 4.0', category: '卡顿 / 丢帧', occurredAt: '2026-07-24 20:31:40', probability: 0.81, resetCause: 'Frame scheduler missed 3 consecutive vsyncs', falseLogs: ['low battery warning', 'thermal hint'], rootCause: 'Main thread synchronous asset decode', status: 'verified' },
  { id: 'BM-POWER-005', platform: 'Android', version: 'Guangzhou R12', category: '功耗异常', occurredAt: '2026-07-25 02:16:27', probability: 0.78, resetCause: 'Doze exit caused by repeating alarm', falseLogs: ['radio wakeup', 'health check'], rootCause: 'Unbounded retry alarm in sync worker', status: 'verified' },
  { id: 'BM-ANR-006', platform: 'Android', version: 'Wuhan R10', category: 'Crash / ANR', occurredAt: '2026-07-26 11:03:19', probability: 0.74, resetCause: 'Input dispatch timeout', falseLogs: ['binder buffer warning', 'low memory'], rootCause: 'Binder call on main thread', status: 'verified' },
  { id: 'BM-OHOS-007', platform: 'OHOS', version: 'Chengdu 4.1', category: '启动稳定性', occurredAt: '2026-07-27 07:48:01', probability: 0.84, resetCause: 'Rosen render service restart', falseLogs: ['permission prompt', 'asset prewarm'], rootCause: 'Invalid surface lifecycle transition', status: 'verified' },
  { id: 'BM-MEM-008', platform: 'OHOS', version: 'Guangzhou 3.9', category: '内存泄漏', occurredAt: '2026-07-28 16:52:34', probability: 0.76, resetCause: 'Memory pressure callback triggered process kill', falseLogs: ['large bitmap allocation', 'JS heap warning'], rootCause: 'Listener not released on page destroy', status: 'verified' }
];
let jobs = [];
let skills = [
  { id: 'builtin-crash-v3', name: 'crash-root-cause', version: '3.2.1', score: 94.2, coverage: 81, status: 'baseline', updated: '2026-07-28', gates: { benchmark: true, ci: true, ablation: true, admin: true } },
  { id: 'builtin-anr-v2', name: 'anr-trace', version: '2.8.0', score: 91.6, coverage: 76, status: 'baseline', updated: '2026-07-25', gates: { benchmark: true, ci: true, ablation: true, admin: true } },
  { id: 'builtin-ohos-v1', name: 'ohos-ability', version: '1.4.2', score: 89.8, coverage: 67, status: 'baseline', updated: '2026-07-20', gates: { benchmark: true, ci: true, ablation: true, admin: true } }
];

function filteredDashboard(platform, location) {
  const result = JSON.parse(JSON.stringify(dashboardSeed));
  if (location && location !== '全部版本') result.locations = result.locations.filter((item) => item.name === location);
  if (platform === 'Android') result.locations = result.locations.map((item) => ({ ...item, ohos: 0, total: item.android }));
  if (platform === 'OHOS') result.locations = result.locations.map((item) => ({ ...item, android: 0, total: item.ohos }));
  if (platform === 'Android') result.types = result.types.map((item) => ({ ...item, ohos: 0 }));
  if (platform === 'OHOS') result.types = result.types.map((item) => ({ ...item, android: 0 }));
  return result;
}

app.get('/api/dashboard', (req, res) => res.json({ ...filteredDashboard(req.query.platform, req.query.location), refreshedAt: new Date().toISOString() }));
app.get('/api/benchmark', (_, res) => res.json({ version: 'benchmark-2026.08', total: benchmarkCases.length, cases: benchmarkCases }));
app.get('/api/skills', (_, res) => res.json(skills));
app.get('/api/jobs', (_, res) => res.json(jobs));
app.get('/api/reports/:id', (req, res) => {
  const reportPath = path.join(reportRoot, `${req.params.id}.md`);
  if (!fs.existsSync(reportPath)) return res.status(404).json({ error: 'report not found' });
  res.type('text/markdown').send(fs.readFileSync(reportPath, 'utf8'));
});

app.post('/api/analyze', upload.fields([{ name: 'logArchive', maxCount: 1 }, { name: 'symbolArchive', maxCount: 1 }]), (req, res) => {
  if (!req.files?.logArchive?.[0]) return res.status(400).json({ error: 'log archive is required' });
  const id = crypto.randomUUID();
  const job = { id, name: req.files.logArchive[0].originalname, location: req.body.location || 'Nanchang', framework: req.body.framework || 'Android', mode: req.body.skillMode || 'auto', status: 'queued', progress: 8, createdAt: new Date().toISOString(), reportReady: false };
  jobs.unshift(job); setTimeout(() => runMockAnalysis(job), 600); res.status(202).json(job);
});

function runMockAnalysis(job) {
  const steps = ['unpack and validate logs', 'extract crash scene and traces', 'call Codex Agent', 'run evidence evaluator', 'write report'];
  let index = 0;
  const timer = setInterval(() => {
    job.status = index < steps.length - 1 ? 'running' : 'completed'; job.step = steps[index]; job.progress = Math.min(100, 18 + index * 18); index += 1;
    if (job.status === 'completed') {
      job.progress = 100; job.reportReady = true; job.score = 92.4;
      const markdown = [`# ${job.location} ${job.framework} Stability Analysis`, '', `> Task: ${job.id} | Generated: ${new Date().toISOString()}`, '', '## Conclusion', '', 'Detected **RenderThread watchdog timeout** with confidence **0.92**.', '', '## Evidence chain', '', '1. `system_server` emitted ANR at 18:42:11.284.', '2. Main thread waited on `BufferQueueProducer::dequeueBuffer` for over 5 seconds.', '3. RenderThread held `mMutex` in the same window as the latest change.', '', '## Decision tree path', '', '`Stability > ANR > Native wait > Graphics pipeline > BufferQueue lock contention`', '', '## PlantUML investigation sequence', '', '```plantuml', '@startuml', 'App -> RenderThread: dequeueBuffer', 'RenderThread -> SurfaceFlinger: request buffer', 'SurfaceFlinger --> RenderThread: lock contention', 'RenderThread --> App: watchdog timeout', '@enduml', '```', '', '## Fix suggestions', '', '- Add lock contention sampling and timeout logs before submit.', '- Regress cold start, rotation and background resume.', '- After evidence review, move the issue to implementation.'].join('\n');
      fs.writeFileSync(path.join(reportRoot, `${job.id}.md`), markdown); fs.writeFileSync(path.join(reportRoot, `${job.id}.json`), JSON.stringify({ algorithm: 'evidence-v1', score: 92.4, evidence: { completeness: 0.95, consistency: 0.91, reproducibility: 0.9 }, baselineDelta: 1.8 }, null, 2)); clearInterval(timer);
    }
  }, 900);
}

app.post('/api/skills', upload.single('skillArchive'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'skill archive is required' });
  const item = { id: crypto.randomUUID(), name: req.body.name || req.file.originalname.replace(/\.(zip|tar|gz|tgz)$/i, ''), version: req.body.version || '0.1.0', score: null, coverage: null, status: 'benchmark_pending', updated: new Date().toISOString().slice(0, 10), gates: { benchmark: false, ci: false, ablation: false, admin: false } };
  skills.unshift(item); res.status(202).json(item);
});

app.post('/api/skills/:id/gate', (req, res) => {
  const skill = skills.find((item) => item.id === req.params.id);
  if (!skill) return res.status(404).json({ error: 'skill not found' });
  const action = req.body.action;
  const transitions = { run_benchmark: 'benchmark', run_ci: 'ci', run_ablation: 'ablation', approve: 'admin' };
  const gate = transitions[action];
  if (!gate) return res.status(400).json({ error: 'unsupported gate action' });
  const prerequisites = { ci: 'benchmark', ablation: 'ci', admin: 'ablation' };
  if (prerequisites[gate] && !skill.gates[prerequisites[gate]]) return res.status(409).json({ error: `complete ${prerequisites[gate]} first` });
  skill.gates[gate] = true;
  if (gate === 'benchmark') { skill.score = 93.1; skill.coverage = 74; skill.benchmark = { dataset: 'benchmark-2026.08', cases: benchmarkCases.length, baselineDelta: 0.7 }; }
  if (gate === 'ci') skill.ci = { passed: 24, total: 24, completedAt: new Date().toISOString() };
  if (gate === 'ablation') skill.ablation = { passed: true, delta: 0.4, completedAt: new Date().toISOString() };
  if (gate === 'admin') skill.status = 'baseline'; else skill.status = gate === 'benchmark' ? 'benchmark_passed' : `${gate}_passed`;
  skill.updated = new Date().toISOString().slice(0, 10);
  res.json(skill);
});

app.get('*', (_, res) => res.sendFile(path.join(root, 'public', 'index.html')));
app.listen(PORT, () => console.log(`Stability Insight running at http://localhost:${PORT}`));
