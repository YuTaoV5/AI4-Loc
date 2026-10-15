"""Flatten all final Agent counters without replacing missing timings by zero."""
import pathlib,json,csv,collections,statistics
E=pathlib.Path(__file__).resolve().parent
rows=[]
for checkpoint in ['base','trained']:
    for r in json.loads((E/'agent32k'/checkpoint/'agent-summary.json').read_text(encoding='utf-8')):
        m=r['metrics'];rows.append({'checkpoint':checkpoint,'variant':r['variant'],'case':r['case'],'status':r['status'],
          'code_location_hit':r['scores']['codeLocationHit'],'function_hit':r['scores']['functionHit'],
          'model_http_calls':m['modelRequests'],'chat_http_calls':m.get('generationModelRequests',m['modelRequests']),
          'decision_http_calls':m.get('decisionModelRequests',0),'decision_questions':m.get('decisionQuestions',0),
          **{k:m.get(k) for k in ['toolCalls','preflightToolCalls','modelToolCalls','inputTokens','outputTokens','totalTokens',
          'tokensComplete','observedTokensLowerBound','firstSceneSeconds','boundarySeconds','rootLocationSeconds','reportOutputSeconds','localizationSeconds']}})
with (E/'tables/agent32k-full-metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
groups=collections.defaultdict(list)
for r in rows:groups[r['checkpoint'],r['variant']].append(r)
out=[]
for (checkpoint,variant),rs in groups.items():
    out.append({'checkpoint':checkpoint,'variant':variant,'cases':len(rs),'completed':sum(r['status']=='completed' for r in rs),
       'code_location_hits':sum(r['code_location_hit'] for r in rs),'model_http_calls':sum(r['model_http_calls'] for r in rs),
       'tool_calls':sum(r['toolCalls'] for r in rs),'total_localization_seconds':sum(r['localizationSeconds'] for r in rs),
       'mean_localization_seconds':statistics.mean(r['localizationSeconds'] for r in rs),
       'reported_input_tokens':sum(r['inputTokens'] or 0 for r in rs),'reported_output_tokens':sum(r['outputTokens'] or 0 for r in rs),
       'all_token_counts_complete':all(r['tokensComplete'] for r in rs)})
with (E/'tables/agent32k-aggregate.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,list(out[0]));w.writeheader();w.writerows(out)
print('AGENT32K_TABLES',len(rows))
