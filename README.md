# integration-tools

A toolkit for tt-metal / tt-forge integration with automation scripts and uplift process documentation.

## Quickstart

```bash
# Show metal commits between two refs (exportable CSV format)
./show/metal_commit_range.py BASE_METAL_COMMIT^ HEAD

# Show FE base commits (tt-torch, tt-xla, tt-forge-fe)
python show/fe_base_commits.py

# Trigger tt-xla and tt-forge-onnx workflows with a tt-mlir uplift branch
python run/shotgun.py uplift-metal-20250128

```

## Tools Documentation
- bisect
  - [init.sh](docs/tools/init.md)
- map
  - [metal_to_mlir.sh](docs/tools/metal_to_mlir.md)
  - [aliases.sh](docs/tools/aliases.md)
- run
  - [shotgun.py](docs/tools/shotgun.md) - Trigger tt-xla and tt-forge-onnx workflows with a tt-mlir override
- show
  - [comment.sh](docs/tools/comment.md)
  - [fe_base_commits.py](docs/tools/fe_base_commits.md)
  - [git_common.sh](docs/tools/git_common.md)
  - [metal_commit_range.py](docs/tools/metal_commit_range.md)
  - [uplift_history.py](docs/tools/uplift_history.md)