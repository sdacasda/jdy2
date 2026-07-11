# Audit of the previous public repository

Repository inspected: `sdacasda/jdy`, branch `main`.

## Confirmed inconsistencies

1. The repository contains `config/athena-dae.config`, while the workflow expects
   `config/athena-daed.config`.
2. `PROJECT.json` identifies the backend as `dae`, while the active workflow and
   README identify it as `DAED`.
3. `docs/刷机与验收说明.md` instructs the user to run lightweight `dae`, while
   the root DAED document describes `daed`.
4. Old helper scripts remain alongside a newer workflow that duplicates their
   responsibilities.
5. Historical fixes were repeatedly layered onto the same repository, leaving no
   single clean source of truth.
6. The active workflow did not contain the conservative swap and `-j2` resource
   profile needed after a GitHub-hosted runner lost communication.

## Replacement policy

This clean replacement uses one DAED config, one metadata identity, one build
workflow, one validation workflow and explicit pre/post-build checks.
