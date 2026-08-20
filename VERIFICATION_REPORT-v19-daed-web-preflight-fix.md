# Athena v19 DAED Web 源码预检修复验证报告

## 输入证据

- GitHub Artifact：`Athena-AX6600-v19-24-test.zip`
- Artifact 大小约 248 字节，仅包含失败阶段诊断，没有固件镜像。
- GitHub 步骤状态：
  - `validate=success`
  - `defconfig=success`
  - `configcheck=success`
  - `daedsource=failure`
  - `compile=skipped`
  - `daedbuild=skipped`
  - `inspect=skipped`
- 失败发生在 DAED 前端 5/5 构建任务成功之后、OpenWrt 四小时编译之前。

## TDD 回归证据

修复前新增的两个正常依赖用例均失败，能复现第 24 次构建的误报：

- 静态 Web 安装器拒绝包含合法 GraphQL 运行时标识符的 bundle。
- DAED 源码缓存验证器拒绝包含相同合法标识符的 gzip 嵌入 Web。

修复后：

- 合法 GraphQL 客户端运行时用例通过。
- 静态资源中的直接异常 toast 和错误序列化仍被拒绝。
- gzip 嵌入资源中的凭据哨兵仍被拒绝。
- 失败诊断包含安全规则名称，但不包含凭据哨兵原文。

## 完整验证结果

在提交 `f71626f` 的源码上执行：

| 验证项 | 结果 |
|---|---:|
| Python 单元/集成测试 | 151/151 通过，0 跳过 |
| OpenWrt 运行时脚本矩阵 | 11/11 通过 |
| DAED 数据库补丁测试 | 5/5 通过 |
| 生产 Shell/Dash 语法 | 通过 |
| Dashboard JavaScript 图表测试 | 通过 |
| 项目结构验证 | 通过 |
| OpenWrt 包布局验证 | 通过 |
| Web/同源代理配置验证 | 通过 |
| 敏感信息扫描 | 通过 |
| Python 语法编译 | 通过 |
| `git diff --check` | 通过 |

## 未在本地完成的验证

本地 Windows 环境没有执行完整的 LiBwrt/OpenWrt 固件编译，也没有连接真机刷写。因此本报告不声称固件编译或真机运行已经通过。下一项必要验证是将本源码上传 GitHub，重新运行 `stable / test / 2 jobs` 工作流；成功后仍应先启动 initramfs 验证，再考虑 sysupgrade。

## 结论

已修复第 24 次构建中可复现的 DAED Web 依赖误报，同时保留登录源码和编译产物的分层安全检查。当前本地可执行验证没有失败项；完整固件编译和真机验收仍待 GitHub 与设备侧完成。
