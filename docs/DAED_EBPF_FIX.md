# DAED eBPF 兼容问题修复

## 症状

错误固件中的 DAED 会反复启动并退出：

```text
load eBPF objects: field LocalTcpSockops:
program local_tcp_sockops: load program: invalid argument:
program of this type cannot use helper bpf_get_current_task#35
```

这不是内存不足，也不是 `127.0.0.1:2023` 反向代理故障。端口已经成功监听，
真正失败点是内核拒绝加载 eBPF 程序。

## 根因

第 9 次构建的包注册信息和详细日志证明，OpenWrt 实际选择的是 LiBwrt
`packages` Feed 中的：

```text
daed 1.27.0-r1
feeds/packages/net/daed
```

项目虽然把不可变的 `openwrt-daede` 源码复制到了
`package/custom/daed`，但 Feed 中存在同名包。生成包元数据时，Feed 版本
覆盖了锁定版本。

`daed 1.27.0` 会无条件加载包含 `bpf_get_current_task` 的
`local_tcp_sockops` 程序；即使全局配置关闭本地 TCP 快速重定向，也无法
绕过加载阶段的 verifier 错误。

项目锁定的 `2026.07.26-r1` 已包含 helper 能力探测：不支持时改用
`bpf_get_current_comm`，适配当前 LiBwrt 6.12 内核。

## 构建修复

- Feeds 更新后、安装前，删除精确冲突路径 `feeds/packages/net/daed`。
- 清理可能残留的 `package/feeds/packages/daed`。
- 再导入不可变的 `package/custom/daed` 并生成 Feed 链接。
- `SOURCES.lock.json` 同时锁定 commit 和期望包版本
  `2026.07.26-r1`。
- 编译前检查 `tmp/.packageinfo` 的实际注册版本。
- 编译后检查 `build.log` 必须进入 `package/custom/daed`，且不得出现
  `feeds/packages/net/daed`。
- 所有带 `tee` 的关键流水线启用 `set -euo pipefail`，避免真实失败被
  `tee` 的成功退出码掩盖。

## 验证

新的工作流会生成：

```text
diagnostics/daed-provenance/prebuild.txt
diagnostics/daed-provenance/postbuild.txt
```

两份文件都必须包含：

```text
PASS: immutable DAED 2026.07.26-r1 is registered and selected
```

真机测试仍必须先使用 initramfs。启动 DAED 后检查：

```sh
/etc/init.d/daed running
echo "running=$?"
logread -e daed | tail -n 100
```

预期 `running=0`，且不再出现 `LocalTcpSockops` 和
`bpf_get_current_task#35` 的 FATAL。

## 旧固件处理

包含 `daed 1.27.0-r1` 的第 9 次固件不能通过修改 DAED 页面配置修复。
在新固件构建完成前，可停止重启循环：

```sh
/etc/init.d/daed stop
```

不要仅替换不匹配的单个二进制。DAED、eBPF 对象、BTF、内核和包依赖需要
由同一次受控构建产生。
