#!/bin/bash

# setup
# Use docker image ghcr.io/tenstorrent/tt-mlir/tt-mlir-ird-ubuntu-22-04:latest
# mkdir -p logs/build
# source env/activate |& tee logs/env_activate.log
# export HF_TOKEN=your_hf_token # for running some gated models like llama3b
# sudo apt-get install protobuf-compiler

# to make sure exit status is propagated even when using tee to capture output logs
set -o pipefail
mkdir -p logs/build

# before checking every commit, show the current window of commits left to bisect
echo -e "Currently bisecting commit:\n$(git log -1 --oneline)\n\nWindow remaining:\n$(git bisect visualize --oneline)" > logs/bisect_status.log
# install tt-smi if not installed. uncomment if tt-smi used
# which tt-smi || pip install git+https://github.com/tenstorrent/tt-smi |& tee logs/tt_smi_install.log
# tt-smi -r


echo -e "\n\nbisecting commit: $(git log -1 --oneline)\n" >> logs/bisect_log.log

# build 
rm -rf build install third_party/tt-xla
cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=DEBUG |& tee logs/build/conf.log 
if [ $? -ne 0 ]; then
    echo -e "Build conf failed\n" >> logs/bisect_log.log
    exit 125
fi
cmake --build build |& tee logs/build/build.log 
if [ $? -ne 0 ]; then
    echo -e "Build failed\n" >> logs/bisect_log.log
    exit 125
fi
cmake --install build |& tee logs/build/install.log
if [ $? -ne 0 ]; then
    echo -e "Install failed\n" >> logs/bisect_log.log
    exit 125
fi

pytest -svv tests/torch/test_basic.py |& tee logs/basic.log
if [ $? -ne 0 ]; then
    echo -e "Basic test failed\n" >> logs/bisect_log.log
    exit 1
fi


echo -e "Test passed\n" >> logs/bisect_log.log
exit 0