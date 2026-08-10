# DAED 后端连接状态修复验证报告

日期：2026-08-10

## 已通过

| 验证项 | 结果 |
|---|---:|
| Python 全量单元测试 | 111 项通过，0 失败 |
| 新增 GraphQL `errors` 可达性回归测试 | 通过 |
| 新增 LuCI 后端门控与简短断开提示测试 | 通过 |
| `verify_project.py` | 通过 |
| `security_check.py` | 通过 |
| `verify_web_config.py` | 通过 |
| `verify_templates.py` | 通过 |
| `verify_package_layout.py` | 通过 |
| `node --check daed-panel.js` | 通过 |
| 修改的 POSIX shell 文件 `sh -n` | 通过 |
| `git diff --check` | 通过 |

## 本地环境限制

完整运行时脚本套件在该 Windows 沙箱中执行了 9 组，其中本次修改覆盖的 `test_rpcd_status.sh`、`test_health.sh` 等相关用例通过；3 组与备份/仪表盘测试有关的既有用例因精简 Git shell 缺少 `sha256sum`、`chmod`，以及 Windows `tar` 行为差异而失败。这些失败没有指向本次 DAED 探针或 LuCI 门控修改。

本地没有执行完整 LiBwrt/OpenWrt 固件编译，也没有在 RE-CS-02 真机上启动新 initramfs。上传源码后仍须运行 GitHub Actions `stable / test`，并只通过 U-Boot RAM 启动新 initramfs 进行验收；在真机门槛全部通过前不要写入 sysupgrade。

