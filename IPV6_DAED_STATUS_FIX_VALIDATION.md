# IPv6 与 DAED 状态修复验证

日期：2026-08-11

## TDD 证据

- `tests/runtime/test_dashboard.sh`：先把 IPv6 从 `wan` 移至 `wan6`，旧实现不能产生 `"ipv6":true`。
- `tests/runtime/test_rpcd_status.sh`：先模拟 `wget` 不支持 POST、`nc` 返回 HTTP 401/GraphQL errors，旧实现错误地提前返回不可达。
- `tests/test_luci_app.py` 与 `tests/test_web_config.py`：先要求完整 UI 只按进程状态控制，旧实现仍要求 API 同时可达。

上述用例均在生产代码修改前观察到预期失败，最小修复后通过。

## 尚需外部验证

- 本地未执行完整 LiBwrt/OpenWrt 固件编译。
- 未在 RE-CS-02 上启动本次修改生成的 initramfs。
- 新固件启动后应确认首页 IPv6 显示已连接、DAED 进程运行时完整 UI 可见、进程停止时只显示“后端未连接”。
