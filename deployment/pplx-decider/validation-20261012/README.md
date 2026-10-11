# PPLX新版常驻部署与验收（2026-10-12）

2026-10-12新版常驻部署已通过在线验收（北京时间2026-10-12 07:29:02）：五个部署脚本与仓库521b29c对应字节SHA256一致，30个权重文件重新核验通过；两轮choice/noul/score、项目DecisionClient、422/404负例和推理后停止→启动→再次推理均通过，共4次合成推理，不计入benchmark。PPLX PID1114，通用PID66启动身份未变，两个模型端点健康。当前常驻为CPU卸载并存配置；全GPU121次实验与此次部署验收分别保存。

| 证据 | 文件 |
| --- | --- |
| 最终服务、运行时及五个脚本哈希 | [部署清单](deployment-manifest.json) |
| 30个权重文件校验 | [校验结果](checkpoint-verification.json) |
| 重启前真实接口与客户端 | [首次验收](validation-before-restart.json) |
| 推理后停止、启动、状态检查 | [生命周期验收](lifecycle-validation.json) |
| 重启后真实接口与客户端 | [最终验收](validation.json) |

私有归档16678字节，27个文件，SHA256 `018c2ed719fd6332b3ccdcb9d7cdcfa6f6f9737a05d75aa046b543dcfc2598d6`；归档及逐文件哈希在本地核对一致。服务器 `/opt/kernel-insight/experiments/pplx-deployment-update-20261012/`；本地 `data/local-archive/pplx-deployment-update-20261012/`。Git仅含合成验收与派生清单，不含账号或业务日志。

[完整部署命令与权重链接](../../../docs/PPLX专用模型下载部署与验收手册.md)。服务脱离SSH保持运行，但不负责容器重启后的自动拉起；本次重启服务器后确实需要重新启动sidecar。网站功能未在本次验证。
