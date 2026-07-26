#!/usr/bin/env python3
import argparse, json
from pathlib import Path

REQUIRED={"daed","luci-app-daede","athena-runtime","luci-app-athena","luci-theme-argon","luci-app-argon-config","nginx","uhttpd"}
FORBIDDEN={"smartdns","luci-app-smartdns","luci-app-openclash","luci-app-passwall","luci-app-homeproxy"}
def main():
 p=argparse.ArgumentParser(); p.add_argument("--openwrt",required=True); p.add_argument("--output",required=True); p.add_argument("--kernel-limit",type=int,default=6291456)
 a=p.parse_args(); root=Path(a.openwrt); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
 target=root/"bin/targets/qualcommax/ipq60xx"
 init=list(target.glob("*jdcloud_re-cs-02*initramfs*uImage.itb"))
 sysup=list(target.glob("*jdcloud_re-cs-02*squashfs-sysupgrade.bin"))
 manifests=list(target.glob("*manifest"))
 packages=set()
 for f in manifests:
  packages.update(line.split()[0] for line in f.read_text(errors="ignore").splitlines() if line.strip())
 persistent=list((root/"build_dir").rglob("jdcloud_re-cs-02-uImage.itb"))
 size=max((f.stat().st_size for f in persistent),default=0)
 report={"initramfs":[str(x) for x in init],"sysupgrade":[str(x) for x in sysup],"kernel_bytes":size,"kernel_limit":a.kernel_limit,"kernel_margin":a.kernel_limit-size,"missing_packages":sorted(REQUIRED-packages) if packages else [],"forbidden_packages":sorted(FORBIDDEN&packages)}
 (out/"firmware-inspection.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
 (out/"kernel-size.txt").write_text(f"kernel_bytes={size}\nlimit={a.kernel_limit}\nmargin={a.kernel_limit-size}\n",encoding="utf-8")
 if len(init)!=1 or len(sysup)!=1 or size>a.kernel_limit or report["missing_packages"] or report["forbidden_packages"]: raise SystemExit(1)
 print("PASS: firmware inspection")
if __name__=="__main__": main()
