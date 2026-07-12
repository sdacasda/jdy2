# Athena AX6600 Minimal DAED — LiBwrt v14

这是给京东云雅典娜 AX6600（JDCloud RE-CS-02）准备的极简固件编译项目。

## 核心原则

- 使用已经在用户设备上验证可启动的 LiBwrt 6.12 基线。
- 源码固定到 `cf9444c1b20458687898489b36e1aebf56d9baf2`。
- 只重点内置 DAED、LuCI 管理和雅典娜点阵屏。
- 保留设备所需 NSS、无线、网络基础能力。
- 不集成 OpenClash、PassWall、HomeProxy、Docker、Samba 等大型插件。
- BTF 使用 rootfs 中的 `vmlinux-btf`，不把调试 BTF 塞入 6 MiB HLOS。
- 同时生成 initramfs RAM 测试镜像与 sysupgrade 固件。

## 第一次运行

上传整个项目到新的 GitHub 仓库。

先运行：

`Actions → Validate Athena Minimal Project → Run workflow`

然后运行主工作流，第一次选择：

- `build_mode`: `validate`
- `compile_jobs`: `2`

验证成功后再新建一次运行：

- `build_mode`: `build`
- `compile_jobs`: `2`

## 强制安全顺序

上一次其他源码线固件曾出现循环重启，所以本项目禁止直接把第一次产物刷入 eMMC。

1. 下载 Artifact 并解压。
2. 进入已安装的自定义 U-Boot Web。
3. 在“启动 uImage / initramfs”页面上传 `*initramfs-uImage.itb`。
4. 该镜像只在内存中启动，不应先覆盖当前稳定固件。
5. 检查 LAN、Wi‑Fi、LuCI、显示屏和 BTF。
6. 重启后应回到原有稳定 LibWrt。
7. RAM 测试完全稳定后，才使用 `*sysupgrade.bin`，并且不保留设置。

详细步骤见 `docs/FLASH.md`。


## v14 detached-BTF compatibility fix

LiBwrt removes the optional `CONFIG_DAED_USE_VMLINUX_BTF` package-choice
symbol during `make defconfig`. The project now patches the copied DAED package
definition so `vmlinux-btf` is a direct dependency. The final firmware still
uses detached BTF; only the unreliable package-choice symbol is removed.
