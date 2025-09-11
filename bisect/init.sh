mkdir up && \
curl -L https://gist.github.com/6d17ff8f2a60ed883b9f08f394eb64cf/download -o gist.zip && \
tdir=$(mktemp -d) && \
unzip gist.zip -d $tdir > /dev/null && \
rm gist.zip && \
mv $tdir/*/* up && \
rm -r $tdir && \
chmod +x up/* && \
find up
