const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const catalog = require('../server/catalog');
const dir = path.join(__dirname, '../data/benchmark');
fs.mkdirSync(dir, {recursive:true});
const decode = s => s.replace(/<[^>]*>/g, '').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&').replace(/&#34;|&quot;/g,'"').replace(/&#39;/g,"'");
async function get(url) { const r = await fetch(url, {signal:AbortSignal.timeout(45000)}); if(!r.ok) throw Error(`HTTP ${r.status}`); return r.text(); }
async function collect() {
  const cases=[];let failures=0;
  for(const seed of catalog) {
    const sourceUrl=`https://syzbot.org/bug?extid=${seed.extid}`;
    try {
      const html=await get(sourceUrl);
      const crashSection=html.slice(html.indexOf('Crashes ('));
      const row=[...crashSection.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/g)].map(m=>m[1]).find(t=>/href="[^"]+"[^>]*>\s*report\s*<\/a>/.test(t));
      const reportLink=row?.match(/href="([^"]+)"[^>]*>\s*report\s*<\/a>/);
      const reportUrl=reportLink ? new URL(decode(reportLink[1]),sourceUrl).href : null;
      const embedded=html.match(/<pre[^>]*>([\s\S]*?)<\/pre>/i);
      const log=reportUrl ? await get(reportUrl) : embedded ? decode(embedded[1]) : '';
      if(!/BUG:|WARNING:|INFO:/.test(log)) throw Error('No crash report found');
      const version=log.match(/(?:Not tainted|Tainted:[^\n]*?)\s+(\d+\.\d+(?:\.\d+)?[^\s]*)/)?.[1] || log.match(/\b(\d+\.\d+\.\d+(?:-[\w.-]+)?)\s+#\d/)?.[1] || null;
      const commit=log.match(/-g([a-f0-9]{12,40})\b/)?.[1] || null;
      const codeLink=[...(row||'').matchAll(/href="([^"]+)"/g)].map(m=>decode(m[1])).find(u=>u.includes('git.kernel.org') && /[?;&]id=[a-f0-9]+/.test(u));
      const revision=codeLink?.match(/[?;&]id=([a-f0-9]{12,40})/)?.[1] || commit || null;
      const repository=codeLink?.includes('/next/') || version?.includes('-next-') ? 'next' : codeLink?.includes('/stable/') ? 'stable' : 'mainline';
      const fixUrl=`https://git.kernel.org/pub/scm/linux/kernel/git/${seed.fixRepository==='stable'?'stable/linux':'torvalds/linux'}.git/commit/?id=${seed.fix}`;
      fs.writeFileSync(path.join(dir,`${seed.id}.txt`),log);
      const item={...seed,sourceUrl,reportUrl,fixUrl,kernelVersion:version,kernelCommit:revision,repository,collectedAt:new Date().toISOString(),sha256:crypto.createHash('sha256').update(log).digest('hex'),bytes:Buffer.byteLength(log),logCompleteness:reportUrl?'full-report':'excerpt',labelStatus:'community-fix / curated-summary',rootCauseBasis:'社区修复标题与日志的人工摘要；未在本地复现',logPath:`${seed.id}.txt`};
      cases.push(item); console.log(`${seed.id}: ${version} ${revision} (${item.bytes} bytes)`);
    } catch(e) { failures++;console.error(`${seed.id}: ${e.message} ${e.cause?.code||''}`); const old=fs.existsSync(path.join(dir,'manifest.json'))?JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'))).cases.find(c=>c.id===seed.id):null; if(old) cases.push(old); }
  }
  const fingerprint=crypto.createHash('sha256').update(cases.map(c=>c.id+':'+c.sha256).join('\n')).digest('hex');
  fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify({version:'linux-community-v1',fingerprint,collectedAt:new Date().toISOString(),collection:{refreshed:catalog.length-failures,failed:failures},cases},null,2));
  if(failures||cases.length !== catalog.length) process.exitCode=1;
}
collect();
