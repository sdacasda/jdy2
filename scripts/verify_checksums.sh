#!/bin/sh
set -eu
ROOT="${1:?usage: verify_checksums.sh ARTIFACT_ROOT}"
(cd "$ROOT" && sha256sum -c SHA256SUMS.txt)
(cd "$ROOT/firmware" && sha256sum -c SHA256SUMS)
echo "PASS: artifact checksums"
