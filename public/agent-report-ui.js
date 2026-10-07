'use strict';
const AgentReportUI={render(job,agent){
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const evidence=agent.evidence||{},commands=evidence.commands||[],scene=agent.firstScene,loc=agent.localization,metrics=agent.metrics;
 const stage={boot:'启动',runtime:'运行',shutdown:'关机',build:'编译',unknown:'未知'};
 return `<div class="panel report-section"><h3>03 / 问题定位 Agent</h3><p class="caption">${esc(agent.model)} · ${esc(agent.elapsedSeconds)} 秒${metrics?` · ${esc(metrics.modelRequests)} 次模型请求 · ${esc(metrics.toolCalls)} 次工具检查`:''}</p><p>${esc(agent.summary)}</p>
 ${scene?`<div class="candidate"><h3>第一现场</h3><p>阶段：${esc(stage[scene.stage]||scene.stage)} · 报错组件：${esc(scene.reportingComponent)} · 涉及组件：${esc(scene.affectedComponent)}</p><p>${esc(scene.description)}</p><small>证据：${(scene.evidenceRefs||[]).map(esc).join(' · ')}</small></div>`:''}
 ${loc?`<div class="candidate"><h3>代码位置候选</h3><p>${esc(loc.mechanism)}</p>${(loc.locations||[]).map(p=>`<p class="mono">${esc(p.path)}:${esc(p.startLine)}–${esc(p.endLine)} · ${esc(p.symbol)}<br><small>证据：${(p.evidenceRefs||[]).map(esc).join(' · ')}</small></p>`).join('')||'<p>尚无源码支持的代码位置。</p>'}<p>引入提交：${loc.introducingCommit?esc(loc.introducingCommit.hash)+'（待验证）':'未确定'}</p><small>候选位置不等于根因已验证；需要因果复核或受控复现。</small></div>`:''}
 <details class="candidate"><summary>工具证据 · ${commands.length} 次检查</summary>${commands.map(c=>`<details><summary>${esc(c.id)} / ${esc(c.tool)} / ${c.result?.error||c.exitCode&&c.exitCode!==0?'检查未完成':'已记录'}</summary><pre>${esc(c.output||JSON.stringify(c.result??c,null,2).slice(0,12000))}</pre></details>`).join('')}
 ${(evidence.logEvidence||[]).slice(0,8).map(e=>`<pre>L${esc(e.line)} ${esc(e.text)}</pre>`).join('')}<p>${(evidence.gaps||[]).map(esc).join('<br>')}</p><a class="btn link" href="/api/jobs/${encodeURIComponent(job.id)}/evidence" target="_blank" rel="noopener">查看完整工具证据 ↗</a></details>
 ${(agent.hypotheses||[]).map(h=>`<div class="candidate"><b>${esc(h.cause)}</b><p>日志行号 ${(h.evidenceLines||[]).map(n=>'L'+esc(n)).join(' · ')} · ${esc(h.confidence)}</p><small>验证：${esc(h.verification)}</small></div>`).join('')}<h3>后续步骤</h3><ul>${(agent.nextSteps||[]).map(s=>`<li>${esc(s)}</li>`).join('')}</ul>${(agent.limitations||[]).length?`<div class="notice">${agent.limitations.map(esc).join('；')}</div>`:''}</div>`;
}};
if(typeof module!=='undefined')module.exports=AgentReportUI;
