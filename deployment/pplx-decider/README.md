# PPLX-Decider 独立服务

完整下载、环境、命令、参数、验收、Agent 接入及故障处理见 [部署手册](../../docs/PPLX_DECIDER_DEPLOYMENT.md)。

- `serve.py`：固定 v1 checkpoint，官方参考 BF16 推理、CPU 卸载，loopback `/v1/systemone`；支持文本 choice/noul/score，每次最多三个问题。
- `serve.py --placement full-gpu`：分时释放GPU后使用的完整GPU模式，逐参数核验cuda:0；详细复测入口见 [全GPU研究目录](../../research/pplx-timeshare-20261012/README.md)。管理器service.py默认CPU卸载配置保持不变。
- `service.py`：Linux 容器内独立后台进程的 start/status/stop，核对 PID 启动时间及命令身份，不操作其他模型。
- `verify-checkpoint.py`：依据固定官方元数据重新校验全部 30 个文件。
- `verify-service.py`：真实权重接口、三种问题类型、概率、负例及项目 DecisionClient 验收；仅合成输入。
- `verify-lifecycle.py`：显式停止/重新启动本服务，核验各步骤与PID变化，保存失败现场；验收后再次运行接口验证。
- `official-model-metadata.json`：固定 revision 的公开 Hugging Face API 元数据，包含文件大小和 LFS/Git 哈希，不含权重或认证信息。

`service.py` 不提供系统重启后自动启动或崩溃自动重启。部署完成默认保持服务运行；需要自动恢复时将前台 `serve.py` 命令交给所在平台的服务管理器。当前不是原生 SGLang PPLX，也不是 Chat 服务。模型权重及服务的 `state/`、`venv/` 不提交 Git。
