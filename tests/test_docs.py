import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
PRODUCTION_VERSION_FILES = (
    "PROJECT.json",
    "README.md",
    "packages/athena-runtime/files/usr/bin/athena-info",
    "packages/athena-runtime/files/usr/libexec/rpcd/athena",
    "scripts/inject_runtime.sh",
    "scripts/collect_output.sh",
)


class DocsTests(unittest.TestCase):
    def test_daed_login_recovery_guide_is_safe_and_actionable(self):
        guide = ROOT / "docs" / "DAED_LOGIN_RECOVERY.md"
        self.assertTrue(guide.is_file(), "missing DAED login recovery guide")
        text = guide.read_text(encoding="utf-8")

        for required in (
            "athena-daed-reset-password",
            "RESET DAED PASSWORD",
            "/root/athena-backups/daed-recovery-",
            "127.0.0.1:2023",
            "/athena-daed/",
            "LuCI",
            "旧密码",
            "已泄露",
            "wing.db",
            "仅适用于 RC2 或更新版本",
            "RC1 不包含此命令",
            "所有现有 DAED 账户",
            "每个账户生成新的随机密码",
            "旧密码和旧会话都会失效",
            "不可传给 `athena-rollback` 或 `athena-backup`",
            "可能显示为 verified",
            "可能报告 restored 但不会恢复任何文件",
            "在任何数据库写入前创建并校验",
            "仅保留供审计、诊断与未来受支持恢复工具",
            "当前 CLI 失败时只恢复原服务启停/enable 状态",
            "不读取备份恢复数据库",
            "不提供用户手工恢复或标准 rollback 路径",
            "(cd \"$BACKUP_DIR\" && sha256sum -c checksums.sha256)",
        ):
            self.assertIn(required, text)

        self.assertNotRegex(text, r"(?im)^\s*(?:rm|unlink)\b.*\bwing\.db\b")
        self.assertNotRegex(text, r"(?im)^\s*(?:password|passwd)\s*[:=]\s*\S+")
        self.assertNotIn("athena-rollback --component daed BACKUP_ID", text)
        self.assertNotIn("CURRENT_DB_DIR=", text)
        self.assertNotIn("自动恢复 CLI 内部失败回滚", text)
        self.assertNotIn("internal CLI failure recovery", text)
        self.assertNotRegex(text, r"(?im)^\s*(?:cp|mv)\b.*\bwing\.db\b")

    def test_recovery_release_notes_and_metadata_use_rc2(self):
        project = json.loads((ROOT / "PROJECT.json").read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertEqual(project["version"], "v19.0.0-rc2")
        self.assertIn("v19.0.0-rc2", readme)
        self.assertIn("## v19.0.0-rc2", changelog)
        self.assertIn("DAED_LOGIN_RECOVERY.md", readme)
        self.assertNotIn("导入节点和模板后", readme)
        expected_sequence = (
            "DAED 默认关闭；请从 LuCI 的“服务 → Athena 优化 → DAED 面板”临时启动 DAED，"
            "再在原生 UI 中导入或添加节点并完成配置，验证可用后如需开机启动，请通过 SSH 执行 "
            "`/etc/init.d/daed enable`；如需取消开机启动，执行 `/etc/init.d/daed disable`。不需要导入模板。"
        )
        self.assertIn(expected_sequence, readme)

    def test_production_version_metadata_has_no_rc1(self):
        for relative in PRODUCTION_VERSION_FILES:
            with self.subTest(relative=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertNotIn("19.0.0-rc1", text)
                self.assertIn("19.0.0-rc2", text)

    def test_consistency(self):
        files = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
        text = "\n".join(path.read_text(encoding="utf-8") for path in files)

        self.assertIn("192.168.50.1", text)
        self.assertIn("192.168.50.1:8080", text)
        self.assertIn("initramfs", text.lower())
        self.assertIn("sysupgrade -n", text)
        self.assertIn("athena-iot setup", text)
        self.assertIn("DAED 默认关闭", text)
        self.assertNotIn("http://192.168.50.1:2023", text)

    def test_no_common_mojibake_in_user_docs(self):
        files = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
        text = "\n".join(path.read_text(encoding="utf-8") for path in files)

        for marker in ("榛樿", "鐜颁唬", "鏋舵瀯", "鍥藉唴", "鍏煎"):
            self.assertNotIn(marker, text, marker)


if __name__ == "__main__":
    unittest.main()
