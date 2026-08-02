# DAED eBPF 兼容修复

## 症状

旧固件中的 DAED 会反复启动并退出：

```text
load eBPF objects: field LocalTcpSockops:
program local_tcp_sockops: load program: invalid argument:
program of this type cannot use helper bpf_get_current_task#35
```

这不是内存不足，也不是 `127.0.0.1:2023` 反向代理故障。端口可能短暂监听，但内核拒绝 eBPF 程序后进程会退出，因此页面也无法正常提供 API。

## 根因与构建修复

旧构建实际选择了 LiBwrt packages Feed 中的 `daed 1.27.0-r1`，覆盖了项目导入的锁定版本。v19 现在：

- 删除 `feeds/packages/net/daed` 和残留的 Feed 链接；
- 只导入 `package/custom/daed`；
- 在 `SOURCES.lock.json` 中锁定 commit 与期望版本 `2026.07.26-r1`；
- 编译前验证 `tmp/.packageinfo` 中的真实注册版本；
- 编译后验证日志确实来自 `package/custom/daed`；
- 生成 `diagnostics/daed-provenance/prebuild.txt` 与 `postbuild.txt`。

两份来源报告都应包含：

```text
PASS: immutable DAED 2026.07.26-r1 is registered and selected
```

## 真机验证

来源检查只能证明构建选中了预期包，不能代替硬件验证。必须先运行 initramfs，再启用 DAED 并检查：

```sh
/etc/init.d/daed running
echo "running=$?"
logread -e daed | tail -n 100
```

预期 `running=0`，且日志不再出现 `LocalTcpSockops` 或 `bpf_get_current_task#35`。通过前不要刷写 sysupgrade，也不要单独替换 DAED 二进制、eBPF 对象、BTF 或内核。

Web 修复会在 eBPF 失败时保留 LuCI 和 8080 恢复入口，并在 DAED 面板显示“进程/API 不可用”；它不会把 eBPF 加载失败伪装成“正在运行”。
