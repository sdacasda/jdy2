# 恢复与回滚

正常入口：`http://192.168.50.1/`

恢复入口：`http://192.168.50.1:8080/`

配置回滚：

```sh
athena-backup --list
athena-rollback BACKUP_ID
```

DAED 故障时先停止 DAED，客户端恢复普通直连；Nginx/Argon 故障时使用 8080 的 Bootstrap LuCI。系统无法启动时，回到 U-Boot 重新加载经过验证的 initramfs。
