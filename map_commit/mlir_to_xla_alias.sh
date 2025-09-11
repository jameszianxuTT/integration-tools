alias mlir_bisect_apply='f(){ for h in $(git -C third_party/tt-mlir/src/tt-mlir log --reverse --format="%h" "$1"); do sed -i -E "s/set\\(TT_MLIR_VERSION \\\"[a-zA-Z0-9]+\\\"\\)/set(TT_MLIR_VERSION \\\"$h\\\")/" third_party/CMakeLists.txt; git add third_party/CMakeLists.txt; git commit --no-verify -m "Set TT_MLIR_VERSION to $h"; done; }; f'
# Usage: mlir_bisect_apply <tt-mlir-log-range>
# Example: mlir_bisect_apply abc..def
