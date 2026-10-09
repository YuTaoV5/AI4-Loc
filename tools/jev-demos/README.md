# Jev 实战 Demo

两个使用 TypeSafe Jev 1.13 的可运行示例，使用官方 HTTP API 和 Python 标准库，不需要额外依赖。

1. `support`：将客服工单分到团队，同时评估紧急程度与是否必须人工核验；三类问题在一次 API 请求中并行返回，示例代码再根据 confidence 和业务策略路由。
2. `tool-risk`：评估只读命令和“用日常维护话术包装的危险命令”。程序最终会用确定性规则拦截生产环境危险命令。示例只输出判断，绝不执行命令。

## 运行

需要 TypeSafe API key。请从 TypeSafe 控制台获取，并通过本机的环境变量或密钥管理器提供给进程；不要把密钥贴到聊天、写进源码或提交到仓库。

推荐通过你已有的密码管理器/安全启动器把密钥临时注入 `TYPESAFE_API_KEY`。例如若已配置 PowerShell SecretManagement：

```powershell
$env:TYPESAFE_API_KEY = Get-Secret -Name TypeSafeApiKey -AsPlainText
python tools/jev-demos/demo_jev.py both
Remove-Item Env:TYPESAFE_API_KEY
```

如果使用其他密钥管理器，请用其安全启动方式运行脚本；避免把密钥直接写进命令历史、源码或聊天记录。

也可以分开运行：

```powershell
python tools/jev-demos/demo_jev.py support
python tools/jev-demos/demo_jev.py tool-risk
```

脚本默认固定 `jev-1.13.0`，可用 `TYPESAFE_MODEL` 覆盖版本。使用代理时，Python 会遵循当前进程的标准 `HTTPS_PROXY` / `HTTP_PROXY` 环境变量。若要测试网关，可设 `TYPESAFE_BASE_URL`；默认 API 地址为 `https://api.typesafe.ai`。

## 安全边界

工单、命令和路由都是合成样例。风险 demo 中展示的 shell 命令只作为文字发送给模型和本地策略检查，代码不会运行它们。confidence 阈值仅为演示值，实际业务应使用独立标注数据选择阈值，低置信或高影响动作转人工，并保留确定性权限检查。
