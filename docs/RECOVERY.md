# 恢复与回滚

正常入口：`https://192.168.50.1/`

恢复入口：`http://192.168.50.1:8080/`

## 配置回滚

```sh
athena-backup --list
athena-rollback BACKUP_ID
athena-rollback --component daed BACKUP_ID
athena-rollback --component web BACKUP_ID
```

- `all`：恢复完整 Athena 配置。
- `daed`：只恢复 DAED 数据库目录。
- `web`：只恢复 Nginx、uHTTPd 和 DAED 服务监听配置，不修改节点数据库。

DAED 异常时先执行 `/etc/init.d/daed stop`，让客户端恢复普通直连。Nginx 或 Argon 故障时使用 8080 的 Bootstrap 恢复入口。

系统无法正常启动时，回到 U-Boot，重新加载已经验证过的 initramfs。initramfs 内的所有临时修改会在重启后消失。
