#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
errors=[]
required=[
'.github/workflows/build-athena-final-candidate.yml',
'config/athena-final-candidate.config',
'scripts/prepare_packages.sh','scripts/patch_daed_btf.py','scripts/inject_runtime.sh',
'scripts/verify_config.sh','scripts/collect_output.sh','scripts/verify_after_flash.sh',
'README.md','PROJECT.json']
for rel in required:
    if not (ROOT/rel).is_file(): errors.append(f'missing: {rel}')
project=json.loads((ROOT/'PROJECT.json').read_text(encoding='utf-8'))
if project.get('source_commit')!='cf9444c1b20458687898489b36e1aebf56d9baf2': errors.append('stable source commit not pinned')
if project.get('daede_ref')!='v2026.07.09': errors.append('DAED release not pinned')
cfg=(ROOT/'config/athena-final-candidate.config').read_text(encoding='utf-8')
for token in [
'CONFIG_TARGET_ROOTFS_INITRAMFS=y','CONFIG_TARGET_ROOTFS_SQUASHFS=y',
'CONFIG_PACKAGE_ath11k-firmware-qcn9074=y','# CONFIG_PACKAGE_ath11k-firmware-qcn9074-ddwrt is not set',
'CONFIG_PACKAGE_daed=y','CONFIG_PACKAGE_luci-app-daede=y','CONFIG_PACKAGE_vmlinux-btf=y',
'CONFIG_PACKAGE_luci-app-athena-led=y','CONFIG_PACKAGE_kmod-sched-bpf=y','CONFIG_KERNEL_XDP_SOCKETS=y',
'CONFIG_PACKAGE_luci-app-wol=y','CONFIG_PACKAGE_luci-i18n-wol-zh-cn=y','CONFIG_PACKAGE_etherwake=y']:
    if token not in cfg: errors.append(f'config safeguard missing: {token}')
workflow=(ROOT/'.github/workflows/build-athena-final-candidate.yml').read_text(encoding='utf-8')
for token in ['cf9444c1b20458687898489b36e1aebf56d9baf2','v2026.07.09','KERNEL_SIZE_VALUE','6291456','initramfs','squashfs-sysupgrade.bin','inject_runtime.sh','ERROR_CONTEXT.txt']:
    if token not in workflow: errors.append(f'workflow safeguard missing: {token}')
runtime=(ROOT/'scripts/inject_runtime.sh').read_text(encoding='utf-8')
for token in ['is_ram_boot','192.168.1.1/24','athena-feature-check','daed disable','athena_led disable','diag.html','etherwake -i br-lan','luci-app-wol']:
    if token not in runtime: errors.append(f'runtime safeguard missing: {token}')
prepare=(ROOT/'scripts/prepare_packages.sh').read_text(encoding='utf-8')
for token in ['v2026.07.09','patch_daed_btf.py',"grep -Fq '+vmlinux-btf'"]:
    if token not in prepare: errors.append(f'package safeguard missing: {token}')
for path in ROOT.rglob('*'):
    if not path.is_file() or '__pycache__' in path.parts: continue
    data=path.read_bytes()
    if b'\r\n' in data: errors.append(f'CRLF: {path.relative_to(ROOT)}')
    text=data.decode('utf-8',errors='ignore')
    if re.search(r'^(<<<<<<< |=======\s*$|>>>>>>> )',text,re.M): errors.append(f'merge marker: {path.relative_to(ROOT)}')
if errors:
    print('PROJECT CHECK FAILED',file=sys.stderr)
    for e in errors: print(f'- {e}',file=sys.stderr)
    raise SystemExit(1)
print('PROJECT CHECK PASSED')
