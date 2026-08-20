#!/usr/bin/env python3
"""Backward-compatible entry point for the authoritative Athena v19 check."""

from __future__ import annotations

import sys

from verify_project import main


if __name__ == "__main__":
    sys.exit(main())
