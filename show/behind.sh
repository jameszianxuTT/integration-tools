#!/bin/bash

source "$(dirname "$0")/git_common.sh"
init

mlir_main_metal=$(get_metal_commit "main")
main_branch="origin/main"

# Set commit range
if [ $# -eq 0 ]; then
    COMMIT_RANGE="$mlir_main_metal..$main_branch"
else
    COMMIT_RANGE="$1..$main_branch"
fi

# Generate simple output
count=$(get_commit_count "$COMMIT_RANGE")
commits_output=$(get_git_log "$COMMIT_RANGE")

# Save to file
echo "Count: $count" > $LOGS_DIR/git.log
echo "" >> $LOGS_DIR/git.log
echo "$commits_output" >> $LOGS_DIR/git.log
