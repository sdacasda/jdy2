# Web 与 DAED 恢复指南

## 固定入口

```text
主 LuCI：   https://192.168.50.1/
恢复入口：  http://192.168.50.1:8080/
DAED 面板： LuCI → 服务 → Athena 优化 → DAED 面板
```

Nginx 是 80/443 的唯一所有者。uHTTPd 只监听 LAN 地址 `192.168.50.1:8080`。DAED 只监听 `127.0.0.1:2023`，因此从电脑直接访问 `192.168.50.1:2023` 失败是预期行为。

## DAED 三种状态

- **开机启用**：服务是否设置为随系统启动。
- **进程运行**：DAED 进程是否仍然存在。
- **API 可达**：路由器本机能否访问 DAED GraphQL。

“已启用”不等于“已运行”。如果 eBPF verifier、配置或内存检查失败，面板不会加载 DAED iframe，仅显示“后端未连接”；详细分类保留在 `athena-health --verbose` 和 DAED 日志中。

## 只读检查

```sh
nginx -t
athena-health --verbose
uci show uhttpd
uci show daed
```

## 恢复顺序

1. 从 LAN 打开 `http://192.168.50.1:8080/`。
2. 停止异常 DAED：`/etc/init.d/daed stop`。
3. 检查并恢复主 Web：

   ```sh
   nginx -t
   /etc/init.d/uhttpd restart
   /etc/init.d/nginx restart
   ```

4. 如本次配置修改导致故障，先查看备份，再仅恢复 Web：

   ```sh
   athena-backup --list
   athena-rollback --component web BACKUP_ID
   ```

Web-only 回滚不会修改 `/etc/daed/wing.db`。如果恢复后的 Nginx 配置仍无效，命令会返回失败，但 8080 恢复入口会保持运行。

## initramfs 注意事项

内存启动中的修改在重启后消失。必须先在 initramfs 中验证 80/443、8080、DAED 状态和三路 Wi-Fi；没有通过前不要刷写 sysupgrade。
