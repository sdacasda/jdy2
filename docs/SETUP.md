# 首次设置

固件首次启动时 DAED 默认关闭，普通直连网络和 LuCI 应保持可用。

1. SSH 执行：

   ```sh
   athena-setup --check
   athena-setup
   ```

2. 向导会在需要时创建校验备份、应用运行时策略并执行健康检查。只有
   所有关键检查通过时才会完成；失败时请按输出使用相应备份回滚。
3. `athena-setup` 不生成或导入 DAED 配置，不启动 DAED，也不编辑或删除
   `wing.db`。备份过程会读取现有配置和数据库，以便必要时恢复。
4. 如需使用 DAED，请先在 LuCI 的“服务 → Athena 优化 → DAED 面板”完成
   自己的配置验证，再明确启用服务。启用后执行：

   ```sh
   athena-health --verbose
   ```

DAED 保持关闭时，健康检查会报告安全默认状态。已启用的 DAED 必须同时满足
开机启用、进程运行和 loopback API 可达；若出现 eBPF 或配置错误，请停止
DAED 并保持普通网络可用后再排查。
