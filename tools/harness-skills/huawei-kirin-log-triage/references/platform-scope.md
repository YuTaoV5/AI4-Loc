# 平台范围与来源

研究参考目标：HUAWEI Pura 90 Pro Max / 麒麟 9030S / HarmonyOS 6.1。此字段不是对用户设备的识别结果。2026-10-26 查询官方规格页，CPU 和系统分别列为麒麟9030S、HarmonyOS 6.1：
https://consumer.huawei.com/cn/phones/pura90-pro-max/specs/

官方营销规格不能证明启动固件、内核体系、ELF build ID、具体系统构建、抓取命令或加密维测格式。相关字段必须从实际材料或配套可信构建产物确认。

ABRLog 已有 HUAWEI L29 示例是另一个实际采集对象，不得改写成 Pura 90 的日志；其 Android release 属性也不能用来推断新目标机型。来源：
https://zenodo.org/records/21892365

Android bugreport 的内容与读取方法可参考 AOSP，但仅在实际材料证明属于 Android 日志体系时使用：
https://source.android.com/docs/core/tests/debug/read-bug-reports

TF-A 的公开参考平台展示 BL2 / BL31 / BL33 的职责和一种启动链，不是麒麟 9030S 的官方实现证明：
https://trustedfirmware-a.readthedocs.io/en/latest/plat/qti/rb3gen2.html

不得把 xloader → BL2 → BL31 → UEFI → kernel → Android 当成所有麒麟机型固定且均可见的序列。新鸿蒙机型用户态名称和可用日志格式以材料为准，保留 unknown。
