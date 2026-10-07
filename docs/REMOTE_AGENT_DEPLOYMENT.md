# 远端 dsh / Qwen 与 SGLang

远端部署目录 `/opt/kernel-insight`；网站为非 root 用户 `kernel-insight` 运行，只监听 `127.0.0.1:8787`。源代码按 SHA256 分成不可混用的 release，数据目录独立，部署包不含账号、私人日志或 SSH 密码。

完整盘点、升级、重复 Supervisor 恢复与回退步骤见 [部署经验流程](DEPLOYMENT_RUNBOOK.md)。本文描述已部署服务器的执行链，不代表本次文档提交包含完整 Agent 功能代码。

## 访问与运维

```bash
ssh -p <SSH_PORT> -L 127.0.0.1:8788:127.0.0.1:8787 root@<SSH_HOST> -N
```

浏览器打开 http://127.0.0.1:8788 。首次账号 `admin / admin`，可在账号页管理用户。不要直接把默认账号网站暴露公网；当前访问经过加密 SSH 隧道。服务器重启后需重新建立隧道。

```bash
/opt/kernel-insight/runtime/venv/bin/supervisorctl -c /opt/kernel-insight/supervisord.conf status
/opt/kernel-insight/runtime/venv/bin/supervisorctl -c /opt/kernel-insight/supervisord.conf restart kernel-insight
```

网站专属 Supervisor 是独立进程；容器原平台使用另一种 Supervisor 实现，不能混用控制配置。容器重启后网站监控进程不会自然保留，需要运行 `scripts/deploy-server.sh` 或按上述配置启动 `supervisord`。部署恢复通过 manage-supervisor.py 核对精确配置对应的进程；只有项目 Supervisor 确实退出后才清理 socket，避免重复实例。维护前必须确认没有活跃任务；不会重启平台所有服务。

## 模型与执行

- `deepseek-harness-sdk==0.1.5rc1` 配套原生 runtime，隔离 `DSH_HOME` 和任务目录，真实工具调用；不读 root 的 dsh 凭据目录。
- Ollama 原有 `qwen3.8:27b-256k` 权重生成 `qwen3.8:27b-kernel-8k` 共享别名，使用 8192 上下文。试过 16k，但与常驻 SGLang 共存时出现 CPU 卸载，未作为最终默认。
- 本机 `11435` 兼容层只转发 `/v1/models` 和 `/v1/chat/completions` 到 Ollama `11434`，添加 `reasoning_effort=none`。这是 Ollama OpenAI 兼容参数；dsh provider 本身不支持 SDK `reasoning_effort=none`，不能直接传该参数。日志读取应有界，不能盲目追求长上下文。
- SGLang `0.5.21` 的 `Qwen3.8-27B-SystemOne` 模型来自已有本地权重，端口 `30000`、上下文 8192、原 bfloat16。仅把 `--mem-fraction-static 0.85` 改为 `0.70`，原启动脚本备份在 `/root/gpufree-data/systemone/scripts/start_systemone.sh.kernel-insight-original`。无需重新下载权重。
- “Jev-like” 的暂定解释是一次回答多个分诊问题：类别、是否需专家、版本与符号是否充分、建议工具。JSON Schema 约束输出；不是 TypeSafe Jev 产品，不输出伪造的概率。若用户补充具体 Jev 项目，应按链接重新确认协议。

真实 Qwen 名称是服务端提供的模型标识，不据此断言上游官方版本或模型能力。用户提供的外部 Ollama HTTPS 地址对应同一服务；网站在远端优先使用回环接口，减少暴露与额外网络延迟。

## 沙箱和证据

`agent-sandbox.sh` 用 bubblewrap 运行非 root 的 dsh；只让任务目录可写，工具/runtime/系统库只读。必须挂载 `/bin`，否则 SDK 的 bash/PTY 无法启动。容器不允许新 proc mount，因此只读挂载现有 `/proc`；网络保留给本机模型 API。它不是允许执行未知漏洞 PoC 的场所，也不是完整网络隔离容器。

目标日志涉及的最多六个源码文件按精确 commit 获取，记录 URL、revision、SHA256。linux-next 旧 commit 若上游不再可访问，会如实记录 404，不能偷偷替换成 mainline 最新代码。完整源码缓存下载仍由原 `kernels.js` 管理。

模型输入包含原始日志、用户选择的 Skill 和相关源码，不包含 Benchmark 标准类别、社区根因摘要或修复答案。网页的社区候选由独立规则检索提供，与模型报告并列展示。模型报告必须通过 JSON 及行号校验；执行失败不回退伪装成模型成功。事件只展示阶段/工具名，不展示内部推理正文。

## 实跑与复现

```bash
python3 scripts/run-agent-benchmark.py --base http://127.0.0.1:8788 --output docs/agent-benchmark.json
```

脚本按顺序提交六个真实社区日志，标准答案只用于外部评分，统计类别正确率与三个 test 案例类别正确率。**类别得分不是根因证明，也不是人工解决率**。Skill PR 原有固定规则无退化门禁仍独立运行；这一模型实跑不应替代它。

资料：[dsh SDK](https://deepseek-harness.github.io/deepseek-harness/en/guide/python-sdk)、[Ollama OpenAI 兼容接口](https://github.com/ollama/ollama/blob/main/docs/openai.md)、[SGLang 显存配置](https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/hyperparameter_tuning.mdx)。密码只能交互输入，不要写入 README、环境示例、Git 或日志。
