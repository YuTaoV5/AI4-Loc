// Describe observed actions only; never synthesize model reasoning or causal proof.
const toolNames={incident:'检查输入与第一现场',log_read:'读取日志片段',log_search:'搜索日志线索',source_search:'搜索候选源码',source_read:'阅读候选代码',symbolize:'将故障指令映射到源码',git_history:'查看代码提交历史',git_show:'检查候选提交补丁'};
function toolView(name,args={},result={}){
 if(result.error)return {title:toolNames[name]||'执行调查工具',detail:'本次未获得新的工具证据。',evidence:[]};
 const lines=Array.isArray(result.lines)?result.lines:[],evidence=lines.slice(0,12).map(x=>({line:x.line,text:x.text}));
 let detail='历史记录未保留可解释的返回内容。';
 if(name==='incident'){
  if(!result.available)return {title:toolNames[name],detail,evidence:[]};
  const a=result.available||{};
  detail=`可用材料：日志${a.log?'已提供':'未提供'}，源码${a.source?'已提供':'未提供'}，编译产物${a.artifacts?'已提供':'未提供'}。`;
  detail+=result.firstDiagnosticLine?`第一条显式异常出现在日志第 ${result.firstDiagnosticLine} 行。`:'未发现支持的显式异常；这不能证明系统健康。';
  const first=lines.find(x=>x.line===result.firstDiagnosticLine);return {title:toolNames[name],detail,evidence:first?[first]:[]};
 }
 if(name==='log_read')detail=`读取日志第 ${args.start??'?'} 行起的 ${lines.length} 行。`;
 if(name==='log_search')detail=`在日志中搜索“${args.text??''}”，返回 ${lines.length} 条匹配记录（有数量上限）。`;
 if(name==='source_read')detail=`阅读 ${result.path||args.path||'候选文件'}，第 ${lines[0]?.line??args.start??'?'}–${lines.at(-1)?.line??'?'} 行；代码片段是证据，尚不代表已证明根因。`;
 if(name==='source_search'){
  const matches=String(result.output||'').split('\n').filter(x=>/^.*?:\d+:/.test(x));
  detail=`在源码中搜索“${args.text??''}”，返回 ${matches.length} 条文本匹配（有数量上限）。`;
  return {title:toolNames[name],detail,evidence:matches.slice(0,8).map(text=>({text})),outcome:result.exitCode===1?'没有文本匹配':undefined};
 }
 if(name==='symbolize')detail=`查询 ${args.symbol||'符号'} + ${args.offset||'偏移'} 的源码位置；工具仅在运行时 Build ID 与 ELF 一致时允许映射。`;
 if(name==='git_history')detail=`查看 ${args.path||'候选文件'} 的最近提交；历史记录仅用于寻找候选。`;
 if(name==='git_show')detail=`检查 ${args.path||'候选文件'} 的候选提交 ${String(args.commit||'').slice(0,12)}；检查补丁不能单独证明引入原因。`;
 if(['symbolize','git_history','git_show'].includes(name))evidence.push(...String(result.output||'').split('\n').slice(0,12).map(text=>({text})));
 return {title:toolNames[name]||'执行调查工具',detail,evidence};
}
function present(row){
 const errors={'Identical call already executed; reuse its evidence':'相同调用已执行，本次未重复执行；继续使用已有证据。','Tool budget exhausted; deliver bounded report':'已达到工具调用预算，本次未执行；需要基于已有证据输出报告。','Tool arguments must be valid JSON':'模型返回的工具参数格式不正确，本次未执行。'};
 if(row.error)row={...row,error:errors[row.error]||row.error};
 if(row.kind==='tool')return {...row,...toolView(row.name,row.arguments,row.result),originLabel:row.origin==='chat'?`Chat 第 ${row.modelRequestIndex} 次请求选择`:row.origin==='preflight'?'Agent 自动预检':'历史工具记录（未保留发起者）'};
 if(row.kind==='decision')return {...row,title:'Decision：快速判断并选择',detail:'以已观察到的日志或候选源码为输入，回答以下有限问题。选择仅作为后续调查线索。'};
 if(row.kind==='api'){
  const s=row.selection;
  const detail=s?.action==='tools'?`选择调用：${(s.tools||[]).map(x=>toolNames[x]||x).join('、')}。执行结果见后续工具步骤。`:s?.action==='report'?(row.reportAccepted?'已输出并通过证据引用检查的定位报告。':'尝试输出报告；尚未通过格式与证据引用检查。'):'历史记录仅保留接口用量，未保留本次模型的动作选择。';
  return {...row,title:'Chat：分析证据并选择下一步',detail,evidence:row.reportAccepted?[{text:row.reportSummary},...(row.reportLocations||[]).map(x=>({text:`候选位置：${x.path}:${x.startLine}–${x.endLine} ${x.symbol||''}（尚需因果验证）`}))]:[]};
 }
 if(row.kind==='dsh'&&toolNames[row.name])return {...row,...toolView(row.name,row.arguments||{},row.result||{}),originLabel:'DSH 工具事件'};
 return {...row,title:row.eventType==='harness/start'?'启动 DSH 调查':row.eventType==='harness/result'?'DSH 调查结束':'DSH 工具活动',detail:row.eventType==='tool/call'?`DSH 选择调用 ${row.name}；历史记录没有受支持的结构化摘要。`:'历史 DSH 事件；未保留的问题与选择无法恢复。',evidence:[]};
}
module.exports={present};
