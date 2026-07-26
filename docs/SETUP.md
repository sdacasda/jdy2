# 首次设置

固件首次启动时 DAED 关闭，普通直连网络可用。先在 LuCI/DAED 面板导入私人节点，再执行：

```sh
athena-setup --check
athena-setup
athena-health --verbose
```

向导先备份，再生成 `/etc/athena/generated/{global,dns,routing}.dae`，不会修改 `wing.db`。按 `IMPORT.md` 在 DAED 页面依次导入并选择代理组。
