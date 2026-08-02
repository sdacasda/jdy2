# 首次设置

固件首次启动时 DAED 默认关闭，普通直连网络和 LuCI 应保持可用。

1. 进入 LuCI 的“服务 → Athena 优化 → DAED 面板”，导入自己的节点。
2. SSH 执行：

   ```sh
   athena-setup --check
   athena-setup
   ```

3. 向导会先创建校验备份，再生成 `/etc/athena/generated/` 下的 `global.dae`、`dns.dae`、`routing.dae` 和 `IMPORT.md`。
4. 按 `IMPORT.md` 将模板导入 DAED 并选择自己的代理组。工具不会直接修改 `wing.db`。
5. 启动 DAED 后执行：

   ```sh
   athena-health --verbose
   ```

必须同时确认“开机启用、进程运行、API 可达”。若出现 eBPF 错误，停止 DAED，保持普通网络可用，并检查构建中的 DAED 来源报告。
