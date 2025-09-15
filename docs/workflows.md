To bisect ongoing metal uplift PRs, we can use the following workflow:

1. Start with an mlir commit that does not contain any metal uplift commits. (`origin/main` or older)
2. Use `./map/metal_to_mlir.sh` to map the mlir commit to a metal commit.
   1. e.g. If we are uplifting metal commits `1a2b3c4..5d6e7f8`, we can use `./map/metal_to_mlir.sh 1a2b3c4..5d6e7f8` to map the mlir commit to a metal commit.
   2. (Optional) If some of these commits need changes in tt-mlir to work correctly, we can use `-p` to specify the patch range.
      1. e.g. If patch commits exist in `111aaa..999fff`, we can use `./map/metal_to_mlir.sh -p 111aaa..999fff 1a2b3c4..5d6e7f8` to map the mlir commit to a metal commit.
      2. Note that the patch commit message should end with the metal commit hash that it is fixing.
3. (Optional) If failure is in frontends, not mlir, repeat mapping step to the frontend repo 
   1. e.g. if metal commits mapped to mlir commits are `2b3c4d5..6e7f8g9`, we can use the appropriate alias to map to frontend, e.g. `mlir_submodule_map 2b3c4d5..6e7f8g9`
4. Modify bash script that reproduces the issue/test to bisect
   1. e.g. if the issue is in `test/test_foo.py`, we can modify `up/check_commit.sh` to run `pytest test/test_foo.py`
5. Run `git bisect start <new_commit_hash> <current_commit_hash> && git bisect run bash up/check_commit.sh` to start bisecting.