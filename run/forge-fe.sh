#!/bin/bash

# setup
# Use docker image ghcr.io/tenstorrent/tt-forge-fe/tt-forge-fe-ird-ubuntu-22-04:latest
# source env/activate
# git submodule update --init --recursive -f 
# pip install cmake pytest
# sudo apt install -y libgl1 libglx-mesa0
# cmake -B env/build env -DTTFORGE_SKIP_BUILD_TTMLIR_ENV=ON |& tee logs/build/env_build_conf.log
# cmake --build env/build |& tee logs/build/env_build.log



# to make sure exit status is propagated even when using tee to capture output logs
set -o pipefail
mkdir -p logs/build

# before checking every commit, show the current window of commits left to bisect
echo -e "Currently bisecting commit:\n$(git log -1 --oneline)\n\nWindow remaining:\n$(git bisect visualize --oneline)" > logs/bisect_status.log
# install tt-smi if not installed. uncomment if tt-smi used
# which tt-smi || pip install git+https://github.com/tenstorrent/tt-smi |& tee logs/tt_smi_install.log
# tt-smi -r

echo -e "\n\nbisecting commit: $(git log -1 --oneline)\n" >> logs/bisect_log.log

# update tt-mlir submodule
git submodule update --init --recursive --force third_party/tt-mlir
echo "submodule tt-mlir updated to $(git -C third_party/tt-mlir log -1 --oneline)" >> logs/bisect_log.log

# build 
rm -rf build && rm -rf tt_build/ 

cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=Debug -DTTMLIR_RUNTIME_DEBUG=ON -DCMAKE_CXX_COMPILER=clang++-17 -DCMAKE_C_COMPILER=clang-17 |& tee logs/build/build_ninja.log 
if [ $? -ne 0 ]; then
    echo -e "Build conf failed\n" >> logs/bisect_log.log
    exit 125
fi

cmake --build build |& tee logs/build/build.log 
if [ $? -ne 0 ]; then
    echo -e "Build failed\n" >> logs/bisect_log.log
    exit 125
fi

cmake --build build -- build_unit_tests |& tee logs/build/build_unit_tests.log
if [ $? -ne 0 ]; then
    echo -e "Build unit tests failed\n" >> logs/bisect_log.log
    exit 125
fi



# run all tests from On PR
pytest -m push -ssv |& tee logs/all_tests.log
if [ $? -ne 0 ]; then
    echo -e "Test failed\n" >> logs/bisect_log.log
    exit 1
fi

echo -e "Test passed\n" >> logs/bisect_log.log
exit 0