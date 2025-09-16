# aliases.sh

## Overview

If an error in a downstream repo is caused by a change in an upstream repo, we can find the breaking upstream commit using these aliases. e.g. if an error in `tt-forge-fe` is caused by a change in `tt-mlir`, we can find the breaking `tt-mlir` commit using `mlir_submodule_map`.

We take the range of upstream commits we know to contain the breaking change, and use these aliases to create a sequence of commits in the downstream repo that map 1-1 with the upstream commits. This helps us run `git bisect` in the downstream repo directly, without having to left-shift the failing test.


- metal_version_map: updates `TT_METAL_VERSION` in tt-mlir for each tt-metal commit in a range. Creates 1 tt-mlir commit for each of these tt-metal commits.
- mlir_version_map: updates `TT_MLIR_VERSION` in `third_party/CMakeLists.txt` for each tt-mlir commit in a frontend repo. 
- mlir_submodule_map: checks out each tt-mlir commit in the `third_party/tt-mlir` submodule and commits the submodule change.

## Usage

1) Make the aliases available in your shell:
```bash
source ./map/aliases.sh
```

2) Run `git rev-parse HEAD` to get the `before_commit_hash`.

3) Run one of the aliases from repo root with a commit range in `abc..def` form (left must be an ancestor of right):
```bash
metal_version_map <tt-metal-range>
mlir_version_map <tt-mlir-range>
mlir_submodule_map <tt-mlir-range>
```

4) Run `git rev-parse HEAD` to get the `after_commit_hash`.

5) New commit range is `before_commit_hash..after_commit_hash`. Run `git bisect start <after_commit_hash> <before_commit_hash> && git bisect run bash up/run/mlir.sh` to start bisecting.

## Examples
- Map tt-mlir commits to `TT_MLIR_VERSION` and create commits:
```bash
source ./map/aliases.sh
before_commit_hash=$(git rev-parse HEAD)
mlir_version_map 111aaa..999fff
after_commit_hash=$(git rev-parse HEAD)
git bisect start $after_commit_hash $before_commit_hash && git bisect run bash up/run/mlir.sh
```