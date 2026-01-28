# shotgun.py

## Overview

The Uplift Shotgun tool triggers remote GitHub Actions workflows in **tt-xla** and **tt-forge-onnx** using the HEAD SHA of a specified tt-mlir branch as `mlir_override`. This is useful for testing uplift changes across downstream projects before merging.

## Usage

```
python run/shotgun.py <mlir-uplift-branch> [--tt-xla] [--tt-forge-onnx] [--dry-run]
# or
python run/shotgun.py --mlir-uplift-branch <branch> [--tt-xla] [--tt-forge-onnx] [--dry-run]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `<branch>` | tt-mlir branch to checkout and read HEAD SHA from (positional) |
| `--mlir-uplift-branch` | tt-mlir branch to checkout (flag alternative to positional) |
| `--tt-xla` | Trigger tt-xla `manual-test.yml` with `mlir-uplift-qualification.json` |
| `--tt-forge-onnx` | Trigger tt-forge-onnx `on-pr.yml` |
| `--dry-run` | Print gh commands but do not execute them |

**Note:** If neither `--tt-xla` nor `--tt-forge-onnx` is specified, both workflows are triggered (with a warning).

## Behavior

1. Clones or checks out tt-mlir via SSH, switches to the provided branch, and resolves HEAD SHA
2. Triggers the selected workflow(s) with the resolved SHA as `mlir_override`
3. Prints the constructed `gh` command for each workflow
4. After triggering, prints the URL of the most recent workflow run (best effort)

## Workflows Triggered

| Target | Workflow | Parameters |
|--------|----------|------------|
| tt-xla | `.github/workflows/manual-test.yml` | `test_suite=mlir-uplift-qualification.json`, `mlir_override=<sha>` |
| tt-forge-onnx | `.github/workflows/on-pr.yml` | `mlir_override=<sha>` |

## Requirements

- **GitHub CLI (gh)**: Must be installed and authenticated for the tenstorrent org
- **SSH access**: Requires SSH access to `git@github.com:tenstorrent/tt-mlir.git`

## Examples

### Trigger both workflows for an uplift branch

```
python run/shotgun.py jzxu/uplift-metal-20250128
```

### Trigger only tt-xla workflow

```
python run/shotgun.py jzxu/uplift-metal-20250128 --tt-xla
```

### Dry run to preview commands

```
python run/shotgun.py jzxu/uplift-metal-20250128 --dry-run
```

Example output:
```
==> Checking out tt-mlir branch 'jzx/uplift_jan27_mod'...

Resolved tt-mlir HEAD on 'jzx/uplift_jan27_mod': 60817a98a5b914065ca27f8d1369e80ea179cb60

==> Triggering tt-xla (manual-test.yml) with mlir_override=60817a98a5b914065ca27f8d1369e80ea179cb60...
   GH command: gh workflow run manual-test.yml -R tenstorrent/tt-xla -f test_suite=mlir-uplift-qualification.json -f mlir_override=60817a98a5b914065ca27f8d1369e80ea179cb60
Workflow run URL: https://github.com/tenstorrent/tt-xla/actions/runs/21413201050

==> Triggering tt-forge-onnx (on-pr.yml) with mlir_override=60817a98a5b914065ca27f8d1369e80ea179cb60...
   GH command: gh workflow run on-pr.yml -R tenstorrent/tt-forge-onnx -f mlir_override=60817a98a5b914065ca27f8d1369e80ea179cb60
Workflow run URL: https://github.com/tenstorrent/tt-forge-onnx/actions/runs/21413202423

Done.

(base) jameszianxu@James-Zian's-Mac integration-tools % 
(base) jameszianxu@James-Zian's-Mac integration-tools % python run/shotgun.py jzx/uplift_jan27_mod_safe_base --tt-xla

==> Checking out tt-mlir branch 'jzx/uplift_jan27_mod_safe_base'...

Resolved tt-mlir HEAD on 'jzx/uplift_jan27_mod_safe_base': fc30d8e077a6dd7de0aadd137f2948e66a7ed846

==> Triggering tt-xla (manual-test.yml) with mlir_override=fc30d8e077a6dd7de0aadd137f2948e66a7ed846...
   GH command: gh workflow run manual-test.yml -R tenstorrent/tt-xla -f test_suite=mlir-uplift-qualification.json -f mlir_override=fc30d8e077a6dd7de0aadd137f2948e66a7ed846
Workflow run URL: https://github.com/tenstorrent/tt-xla/actions/runs/21415345947

Done.
```
