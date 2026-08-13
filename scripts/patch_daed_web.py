#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path


SOURCE = Path("apps/web/src/constants/default.ts")
SETUP_SOURCE = Path("apps/web/src/pages/Setup.tsx")
OLD = "export const DEFAULT_ENDPOINT_URL = `${location.protocol}//${location.hostname}:2023/graphql`"
NEW = "export const DEFAULT_ENDPOINT_URL = `${location.origin}/athena-daed/graphql`"
RAW_ERROR_TOAST = "toast.error((err as Error).message)"
SAFE_ERROR_TOAST = "toast.error(safeErrorMessage(err))"
FORMATTER_ANCHOR = """const loginSchema = z.object({
  username: z.string().min(4).max(20),
  password: z.string().min(6).max(20),
})"""
SAFE_ERROR_FORMATTER = """function safeErrorMessage(error: unknown): string {
  try {
    if (typeof error !== 'object' || error === null || !('response' in error)) return 'DAED request failed'
    const response = (error as { response?: unknown }).response
    if (typeof response !== 'object' || response === null || !('errors' in response)) return 'DAED request failed'
    const errors = (response as { errors?: unknown }).errors
    if (!Array.isArray(errors)) return 'DAED request failed'
    const messages: string[] = []
    for (const entry of errors) {
      if (typeof entry !== 'object' || entry === null || !('message' in entry)) continue
      const message = (entry as { message?: unknown }).message
      if (typeof message === 'string' && message.length > 0) messages.push(message)
    }
    return messages.length > 0 ? messages.join('\\n') : 'DAED request failed'
  } catch {
    return 'DAED request failed'
  }
}"""
CLEAN_ENDPOINT_SHA256 = "a07daaa2dc9eeb65171d5953c9c9b1020d38513a277232bf26cff05e378dc13c"
CLEAN_SETUP_SHA256 = "8cb53c5ad6ec32be10df3e04661905600d2080e69eeec0f77ab991d4e2231490"
PATCHED_ENDPOINT_SHA256 = "3fa4d1a580808b1e9a7aef93597db854e5dbb5146725c8548f985eeee4d7db11"
PATCHED_SETUP_SHA256 = "c891392c2a91dab4db1377b536b0a47663a7ef8d89776e2f3efbeb3a60964aa6"
TOAST_ERROR_PATTERN = re.compile(r"\btoast\.error\s*\(")
CATCH_PATTERN = re.compile(r"\bcatch\s*\(")
DIRECT_ERROR_TOAST_PATTERN = re.compile(r"toast\.error\s*\(\s*err\.message\s*\)")
JSON_STRINGIFY_PATTERN = re.compile(r"JSON\.stringify\s*\(")
FORBIDDEN_SOURCE_LEAKS = (
    "toast.error(err.message)",
    "JSON.stringify(error)",
    "JSON.stringify(err)",
    "console.",
    "request.variables",
    "request.body",
    "ClientError",
)


def sha256_bytes(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def write_temporary(path: Path, contents: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def replace_both_files(
    endpoint_path: Path,
    original_endpoint: bytes,
    endpoint: bytes,
    setup_path: Path,
    original_setup: bytes,
    setup: bytes,
) -> None:
    endpoint_temporary = write_temporary(endpoint_path, endpoint)
    setup_temporary = write_temporary(setup_path, setup)
    endpoint_replaced = False
    setup_replaced = False
    try:
        os.replace(endpoint_temporary, endpoint_path)
        endpoint_replaced = True
        os.replace(setup_temporary, setup_path)
        setup_replaced = True
    except Exception:
        if setup_replaced:
            restore = write_temporary(setup_path, original_setup)
            os.replace(restore, setup_path)
        if endpoint_replaced:
            restore = write_temporary(endpoint_path, original_endpoint)
            os.replace(restore, endpoint_path)
        raise
    finally:
        endpoint_temporary.unlink(missing_ok=True)
        setup_temporary.unlink(missing_ok=True)


def patch_source(root: Path) -> None:
    endpoint_path = root / SOURCE
    setup_path = root / SETUP_SOURCE
    if not endpoint_path.is_file():
        raise RuntimeError(f"DAED endpoint source is missing: {SOURCE}")
    if not setup_path.is_file():
        raise RuntimeError(f"DAED setup source is missing: {SETUP_SOURCE}")

    original_endpoint = endpoint_path.read_bytes()
    original_setup = setup_path.read_bytes()
    endpoint = original_endpoint.decode("utf-8").replace("\r\n", "\n")
    setup = original_setup.decode("utf-8").replace("\r\n", "\n")
    for leak in FORBIDDEN_SOURCE_LEAKS:
        if leak in setup:
            raise RuntimeError(f"unsafe DAED Web login error content: {leak}")
    endpoint_state = (endpoint.count(OLD), endpoint.count(NEW))
    setup_state = (
        setup.count(RAW_ERROR_TOAST),
        setup.count(SAFE_ERROR_TOAST),
        setup.count(SAFE_ERROR_FORMATTER),
        setup.count(FORMATTER_ANCHOR),
        len(TOAST_ERROR_PATTERN.findall(setup)),
        len(CATCH_PATTERN.findall(setup)),
        len(DIRECT_ERROR_TOAST_PATTERN.findall(setup)),
        len(JSON_STRINGIFY_PATTERN.findall(setup)),
    )

    if endpoint_state == (0, 1) and setup_state == (0, 3, 1, 1, 3, 3, 0, 0):
        if (
            sha256_bytes(original_endpoint) == PATCHED_ENDPOINT_SHA256
            and sha256_bytes(original_setup) == PATCHED_SETUP_SHA256
        ):
            return
    if (
        endpoint_state != (1, 0)
        or setup_state != (3, 0, 0, 1, 3, 3, 0, 0)
        or sha256_bytes(original_endpoint) != CLEAN_ENDPOINT_SHA256
        or sha256_bytes(original_setup) != CLEAN_SETUP_SHA256
    ):
        raise RuntimeError(
            "unexpected DAED Web source state: "
            f"endpoint_old={endpoint_state[0]} endpoint_new={endpoint_state[1]} "
            f"setup_raw={setup_state[0]} setup_safe={setup_state[1]} "
            f"setup_formatter={setup_state[2]} setup_anchor={setup_state[3]} "
            f"setup_toasts={setup_state[4]} setup_catches={setup_state[5]} "
            f"setup_direct={setup_state[6]} setup_json={setup_state[7]}"
        )

    patched_endpoint = endpoint.replace(OLD, NEW, 1)
    patched_setup = setup.replace(
        FORMATTER_ANCHOR,
        f"{FORMATTER_ANCHOR}\n\n{SAFE_ERROR_FORMATTER}",
        1,
    ).replace(RAW_ERROR_TOAST, SAFE_ERROR_TOAST, 3)
    replace_both_files(
        endpoint_path,
        original_endpoint,
        patched_endpoint.encode("utf-8"),
        setup_path,
        original_setup,
        patched_setup.encode("utf-8"),
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} DAED_SOURCE_ROOT", file=sys.stderr)
        return 2

    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"DAED source root not found: {root}", file=sys.stderr)
        return 2

    try:
        patch_source(root)
    except Exception as exc:
        print(f"DAED Web endpoint patch failed: {exc}", file=sys.stderr)
        return 1

    print(f"Patched DAED Web source: {root / SOURCE} and {root / SETUP_SOURCE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
