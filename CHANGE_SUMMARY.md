# v19.0.0-rc1 变更摘要

新增 Athena 运行时包、LuCI 管理应用、Argon/DAED 同源面板、恢复入口、配置模板、独立 IoT 2.4G SSID、备份回滚、健康检查、不可变源码锁和严格产物验证。

DAED 上游原计划版本 `v2026.07.09` 已不存在，因此源码锁使用当前可验证的 `v2026.07.26` 提交 `b16dbbd3f94558c30d9a875c7e8daf91d4718747`。

上传整个源码目录到 GitHub 后运行 v19 工作流。先下载 test Artifact、校验、测试 initramfs，再考虑 sysupgrade。真机验证通过后可发布 `v19.0.0-rc1`，稳定后再发布 `v19.0.0`。

工作流已兼容 Windows/GitHub 上传导致的可执行位丢失，并升级到 Node 24 兼容的 `actions/checkout@v5` 与 `actions/upload-artifact@v6`。重新上传修订版时应覆盖整个源码目录。

第二次云端验证已确认源码锁和包准备阶段通过。OpenWrt Web 栈改为只选择 `nginx-ssl`，有效配置校验接受正确的 SSL 变体；defconfig 和配置核验现已分成两个步骤，失败 Artifact 会保存 seed、effective config 和 diffconfig。
