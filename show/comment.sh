#!/bin/bash

# TODO: auto get launched FE CI runs 
source "$(dirname "$0")/git_common.sh"
init

OUTPUT_FILE="$LOGS_DIR/uc.md"

# Set commit range
if [ $# -eq 0 ]; then
    main_metal=$(get_metal_commit "main")
    uplift_metal=$(get_metal_commit "uplift")
    COMMIT_RANGE="$main_metal..$uplift_metal"
else
    COMMIT_RANGE="$1"
fi

# Generate template output
count=$(get_commit_count "$COMMIT_RANGE")
commits_output=$(get_git_log "$COMMIT_RANGE")
command_used=$(log_cmd "$COMMIT_RANGE")

# Build output components
link_str="https://github.com/tenstorrent/tt-metal/compare/$main_metal...$uplift_metal"
count_str="Brings [$count metal commits]($link_str)"
commits_str="\`\`\`j
> $command_used
$commits_output
\`\`\`"


# Generate formatted comment using conditional wrapping
if [ "$count" -gt 30 ]; then
    # Wrap with <details> tag for multiple commits
    cat > "$OUTPUT_FILE" << EOF
$count_str
<details><summary> Click to expand commits ◀ </summary>

$commits_str

</details>

EOF
else
    # Simple format for no commits
    echo "$count_str" > "$OUTPUT_FILE"
    echo "$commits_str" >> "$OUTPUT_FILE"
fi

echo "Comment generated and saved to $OUTPUT_FILE"