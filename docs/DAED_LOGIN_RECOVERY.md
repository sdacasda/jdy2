# DAED 登录与密码恢复

仅适用于 RC2 或更新版本的 Athena AX6600 DAED 固件。本版本修复了首次创建账户
时的 SQLite 并发初始化问题，并且 DAED 登录和设置界面只显示经过脱敏的错误信息；
不会再把提交的账户密码或 GraphQL 请求变量显示在浏览器中。RC1 不包含此命令；
本项目交付不要求在线部署，请使用已构建并刷入的 RC2+ 固件。

## 访问方式与安全边界

DAED 仍默认关闭。启用后，服务只监听路由器回环地址
`127.0.0.1:2023`，因此 `192.168.50.1:2023` 从 LAN 无法连接是预期的
安全行为，不能通过修改监听地址来绕过它。

请从 LuCI 的“服务 → Athena 优化 → DAED 面板”打开 DAED。该面板通过同源
`/athena-daed/` 和 `/athena-daed/graphql` 访问后端，浏览器不会直接连接
端口 2023。

截图中曾显示过的旧密码必须视为**已泄露**：立即停止使用并更换它。不要把旧
密码、生成的新密码、节点链接或订阅凭据写入工单、聊天记录、截图或仓库；本仓库
不得包含任何真实账户密码或节点凭据。

## v19 固件中的恢复流程

已认证的 LuCI 管理员可在 DAED 面板选择“Reset DAED password”。界面会要求精确
输入 `RESET DAED PASSWORD`，并仅在完成后一次性显示生成的账户与密码。此操作会
重置 `wing.db` 中所有现有 DAED 账户：每个账户生成新的随机密码，旧密码和旧会话都会失效。
关闭结果窗口后，面板会清除显示内容；请在关闭前把凭据保存在受保护的位置，
并在成功登录后再次从 DAED 账户设置中更换密码。

恢复会在任何数据库写入前创建并校验数据库备份，包含 `wing.db` 及存在的 SQLite
sidecar 文件。备份目录形如：

```text
/root/athena-backups/daed-recovery-YYYYMMDDTHHMMSS-N/
```

如果重置、停止或重启失败，恢复命令会保留该备份。当前 CLI 失败时只恢复原服务启停/enable 状态，不读取备份恢复数据库；失败不会自动覆盖或删除 `wing.db`。

## 已运行镜像的 SSH/CLI 恢复

无法使用 LuCI 时，以受信任的管理员 SSH 会话运行：

```sh
athena-daed-reset-password
```

阅读警告后，按提示输入精确确认语句 `RESET DAED PASSWORD`。也可只在受保护的
交互式终端中把该确认语句作为唯一参数传入；命令从不接受用户选择的新密码参数。
成功时标准输出只有一行 JSON，其中含新账户名、生成密码和备份目录。不要把这行
输出重定向到日志、终端录屏或不受保护的文件。

完成后可执行以下命令确认备份完整并检查服务状态。校验必须在备份目录内进行，
否则 `checksums.sha256` 中的相对文件名无法得到正确验证：

```sh
BACKUP_DIR=/root/athena-backups/daed-recovery-YYYYMMDDTHHMMSS-N
(cd "$BACKUP_DIR" && sha256sum -c checksums.sha256)
/etc/init.d/daed status
athena-health --verbose
```

请将 `BACKUP_DIR` 替换为恢复结果返回的实际路径。若 DAED 原先运行，成功恢复后应
再次运行；若原先未运行，恢复不会擅自启用或启动它。

## 回滚和注意事项

不要删除、重建或手工清空 `wing.db`。这样会丢失节点、订阅、路由、DNS 和账户
数据，也不是密码恢复的必要步骤。恢复失败时先保留返回的备份目录和服务状态，再
排查错误。

`/root/athena-backups/daed-recovery-*` 是恢复命令生成的专用松散备份目录，不可传给 `athena-rollback` 或 `athena-backup`。它仅保留供审计、诊断与未来受支持恢复工具；不提供用户手工恢复或标准 rollback 路径。

标准 Athena 回滚只会提取完整备份目录中的 `daed-database.tar.gz`。专用恢复目录只有
数据库文件和 `checksums.sha256`，没有该 tar 归档。因而当前 `athena-backup` 可能显示为 verified，`athena-rollback` 可能报告 restored 但不会恢复任何文件：这是静默 NO-OP，不是成功恢复，也不能把它当作失败提示。

不要把专用目录交给这两个命令，也不要手工复制、移动、删除、重建或清空 `wing.db`。
需要恢复时，请重新运行受支持的恢复命令，等待后续提供受支持的恢复工具，或保留专用
备份目录并联系维护支持。配置模板和规则文件仍作为固件内部参考保留在
`/usr/share/athena/`，但模板导入工作流已经退役：用户不需要导入模板，`athena-setup`
也不会生成或等待导入它们。
