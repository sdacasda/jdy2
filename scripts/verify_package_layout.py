#!/usr/bin/env python3
from pathlib import Path
import argparse
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); root=Path(ap.parse_args().root)
    required=[
      "packages/athena-runtime/Makefile","packages/luci-app-athena/Makefile",
      "packages/athena-runtime/files/usr/bin/athena-setup",
      "packages/athena-runtime/files/usr/bin/athena-iot",
      "packages/luci-app-athena/root/etc/nginx/conf.d/athena-daed.conf"]
    missing=[p for p in required if not (root/p).is_file()]
    if missing: raise SystemExit("missing: "+", ".join(missing))
    print("PASS: package layout")
if __name__=="__main__": main()
