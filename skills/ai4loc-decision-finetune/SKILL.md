---
name: ai4loc-decision-finetune
description: Fine-tune Qwen3.5-9B for reviewed AI4Loc choice decisions with LoRA and CE or CE plus RLCD; produce a reproducible training plan, merged checkpoint, evaluation records and SGLang deployment instructions. Use after a validated dataset is available.
---

# LoRA决策微调与服务验收

读取[完整复现步骤](references/reproduce.md)。默认先生成训练计划；实际GPU训练仅在用户要求训练时执行，不将创建skill理解为授权停止生产或下载几十GB权重。

输入：已验收的全新run目录（含private/frozen/validation）、固定Qwen3.5-9B基座目录、全新模型输出目录。需要项目源码根目录以定位已执行训练参考；不猜测服务器路径。

1. 检查数据审核、机制隔离和类别支持，明确训练目标是首诊断choice，不能称为根因提交训练。
2. 运行`scripts/train.py --project-root <repo> --run-dir <run> --base <base> --output <new-model>`，保存计划、输入哈希、超参数和资源条件；同时生成并编译校验对应worker源码、记录其SHA。默认不加载模型、不访问网络、不占GPU。
3. 用户要求实际微调时，加`--execute`。选择`--objective ce-rlcd`复用项目日程，或`--objective ce`做相同更新预算的CE-only。旧run有训练日志/适配器时不续写，另建目录。
4. 保存每步loss/耗时/显存、每轮dev、适配器、开发选择与合并模型哈希。CE/RLCD梯度输入是可微logits与target；HTTP概率JSON不是反传入口。
5. 按复现文档启动隔离SGLang实例，验证choice完整概率及单字母Chat，固定输入和缓存状态测时间；训练与推理分别记录显存和配置。生产切换是单独动作。

rank8/alpha16、48处投影、3epoch/每例4排列/梯度累计4是项目参考设置，可作为相同预算对照；用户更换基座架构时需要改读出和LoRA目标，不能直接声称兼容。

温度仅在独立dev上选择并验证；部署先保留T=1基线。test不能反复用于调参。训练参数少不免除完整骨干、激活、KV/状态与workspace显存需求。
