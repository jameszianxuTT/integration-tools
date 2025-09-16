folders_to_move=(run map show)
mkdir -p up && \
tdir=$(mktemp -d) && \
curl -L ${REPO_ZIP_URL:-https://github.com/jameszianxuTT/integration-tools/archive/refs/heads/main.zip} -o "$tdir/repo.zip" && \
unzip "$tdir/repo.zip" -d "$tdir" > /dev/null && \
rm "$tdir/repo.zip" && \
srcdir=$(find "$tdir" -maxdepth 1 -type d -name "integration-tools-*" | head -n 1) && \
for folder in "${folders_to_move[@]}"; do [ -d "$srcdir/$folder" ] && mv "$srcdir/$folder" up/; done && \
rm -r "$srcdir" && \
find up -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod +x {} + && \
find up
