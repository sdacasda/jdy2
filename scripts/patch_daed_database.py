#!/usr/bin/env python3
"""Apply the pinned dae-wing SQLite concurrency and transaction-safety patch."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


DB_PATH = Path("wing/db/db.go")
MUTATION_PATH = Path("wing/graphql/mutation.go")

DB_ANCHOR = """\
\tdb, err = gorm.Open(sqlite.Open(path), &gorm.Config{
\t\t// Logger: logger.Default.LogMode(logger.Info),
\t})
\tif err != nil {
\t\treturn fmt.Errorf("%w: %v", err, path)
\t}
\tif err = db.AutoMigrate(
"""

DB_PATCH = """\
\tdb, err = gorm.Open(sqlite.Open(path), &gorm.Config{
\t\t// Logger: logger.Default.LogMode(logger.Info),
\t})
\tif err != nil {
\t\treturn fmt.Errorf("%w: %v", err, path)
\t}
\tsqlDB, err := db.DB()
\tif err != nil {
\t\treturn err
\t}
\tsqlDB.SetMaxOpenConns(1)
\tsqlDB.SetMaxIdleConns(1)
\tif _, err = sqlDB.Exec("PRAGMA busy_timeout = 10000"); err != nil {
\t\treturn err
\t}
\tif err = db.AutoMigrate(
"""

MUTATION_ANCHOR = """\
\ttx := db.BeginTx(context.TODO())
\tdefer func() {
\t\tif err == nil {
\t\t\ttx.Commit()
\t\t} else {
\t\t\ttx.Rollback()
\t\t}
\t}()
"""

MUTATION_PATCH = """\
\ttx := db.BeginTx(context.TODO())
\tif err = tx.Error; err != nil {
\t\treturn "", err
\t}
\tdefer func() {
\t\tif err == nil {
\t\t\terr = tx.Commit().Error
\t\t} else {
\t\t\ttx.Rollback()
\t\t}
\t}()
"""


def read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"unable to read pinned source file {path}: {exc}") from exc


def patch_state(source: str, anchor: str, patch: str, path: Path) -> bool:
    """Return whether *source* is already patched, rejecting unknown layouts."""
    anchor_count = source.count(anchor)
    patch_count = source.count(patch)
    if anchor_count == 1 and patch_count == 0:
        return False
    if anchor_count == 0 and patch_count == 1:
        return True
    raise RuntimeError(
        f"pinned source anchor mismatch in {path}: "
        f"expected exactly one unpatched or patched anchor"
    )


def stage_source(path: Path, source: str) -> Path:
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(source)
        return Path(temporary_name)
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"unable to stage patched source file {path}: {exc}") from exc


def replace_sources_atomically(
    db_path: Path,
    mutation_path: Path,
    db_source: str,
    patched_db: str,
    patched_mutation: str,
) -> None:
    """Stage both files before replacing either, restoring on a later failure."""
    temporary_paths: list[Path] = []
    db_replaced = False
    try:
        patched_db_path = stage_source(db_path, patched_db)
        temporary_paths.append(patched_db_path)
        patched_mutation_path = stage_source(mutation_path, patched_mutation)
        temporary_paths.append(patched_mutation_path)
        db_backup_path = stage_source(db_path, db_source)
        temporary_paths.append(db_backup_path)

        os.replace(patched_db_path, db_path)
        temporary_paths.remove(patched_db_path)
        db_replaced = True
        os.replace(patched_mutation_path, mutation_path)
        temporary_paths.remove(patched_mutation_path)
    except OSError as exc:
        if db_replaced:
            try:
                os.replace(db_backup_path, db_path)
                temporary_paths.remove(db_backup_path)
            except (OSError, ValueError) as rollback_exc:
                raise RuntimeError(
                    f"unable to replace both patched source files and restore {db_path}: "
                    f"{rollback_exc}"
                ) from exc
        raise RuntimeError(f"unable to replace both patched source files: {exc}") from exc
    finally:
        for temporary_path in temporary_paths:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def patch_source(source_root: Path) -> None:
    db_path = source_root / DB_PATH
    mutation_path = source_root / MUTATION_PATH
    db_source = read_source(db_path)
    mutation_source = read_source(mutation_path)

    db_patched = patch_state(db_source, DB_ANCHOR, DB_PATCH, db_path)
    mutation_patched = patch_state(
        mutation_source, MUTATION_ANCHOR, MUTATION_PATCH, mutation_path
    )
    if db_patched != mutation_patched:
        raise RuntimeError("pinned source is only partially database-patched")
    if db_patched:
        return

    patched_db = db_source.replace(DB_ANCHOR, DB_PATCH, 1)
    patched_mutation = mutation_source.replace(MUTATION_ANCHOR, MUTATION_PATCH, 1)
    replace_sources_atomically(
        db_path,
        mutation_path,
        db_source,
        patched_db,
        patched_mutation,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path, help="assembled DAED source root")
    args = parser.parse_args()
    try:
        patch_source(args.source_root)
    except RuntimeError as exc:
        print(f"DAED database patch failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
