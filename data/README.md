# 项目数据入口

完整目录说明、恢复方法和质量边界见 [本地数据指南](../docs/LOCAL_DATA_GUIDE.md)。

- `benchmark/`：Git 内公开社区日志夹具。
- `datasets/`：本地四个数据集版本，含完整稳定性材料集。
- `experiments/kernel-lab/`：启动阶段、旧采集和评测原始记录。
- `server-snapshots/`：Linux 完整恢复归档及 SHA256 清单，含获授权的私有业务数据。
- `source-repositories/`：本地保留的内核 Git 历史。
- `dataset-audit/`：历史审计与失败证据。
- `toolchains/`、`kernels/`：运行依赖和源码缓存。

除公开夹具及本说明外，大型/私有数据均排除在 Git 外。不要用服务器账号数据库覆盖本地账号文件，也不要将数据集标签提供给 Agent。
