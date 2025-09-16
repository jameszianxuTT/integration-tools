#!/bin/bash

# setup
# Use docker image ghcr.io/tenstorrent/tt-mlir/tt-mlir-ird-ubuntu-22-04:latest
# source env/activate

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
rm -rf build third_party/tt-metal

## speedy 
cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang-17 -DCMAKE_CXX_COMPILER=clang++-17 -DTTMLIR_ENABLE_RUNTIME=ON -DTTMLIR_ENABLE_RUNTIME_TESTS=ON -DCMAKE_CXX_COMPILER_LAUNCHER=ccache -DTTMLIR_ENABLE_STABLEHLO=ON -DTTMLIR_ENABLE_OPMODEL=ON |& tee logs/build/cmake_cfg.log
## tracy 
#cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang-17 -DCMAKE_CXX_COMPILER=clang++-17 -DTTMLIR_ENABLE_RUNTIME=ON -DTT_RUNTIME_ENABLE_PERF_TRACE=ON -DTTMLIR_ENABLE_RUNTIME_TESTS=ON -DCMAKE_CXX_COMPILER_LAUNCHER=ccache -DTT_RUNTIME_DEBUG=ON -DTTMLIR_ENABLE_STABLEHLO=ON |& tee logs/build/cmake_cfg.log
if [ $? -ne 0 ]; then
    echo -e "Build conf failed\n" >> logs/bisect_log.log
    exit 125
fi

cmake --build build |& tee logs/build/build.log
if [ $? -ne 0 ]; then
    echo -e "Build failed\n" >> logs/bisect_log.log
    exit 125
fi
cmake --build build -- ttrt |& tee logs/build/build_ttrt.log
if [ $? -ne 0 ]; then
    echo -e "ttrt Build failed\n" >> logs/bisect_log.log
    exit 125
fi
rm -rf ttrt-artifacts && ttrt query --save-artifacts |& tee logs/artifacts.log && export SYSTEM_DESC_PATH=`pwd`/ttrt-artifacts/system_desc.ttsys
if [ $? -ne 0 ]; then
    echo -e "ttrt query failed\n" >> logs/bisect_log.log
    exit 125
fi


# regtest
cmake --build build -- check-ttmlir |& tee logs/check_ttmlir.log
if [ $? -ne 0 ]; then
    echo -e "Test failed\n" >> logs/bisect_log.log
    exit 1
fi

# lit
## op model lib
### lib
cmake --build ./build --target TestOpModelLib |& tee logs/lit_opmodellib.log
if [ $? -ne 0 ]; then
    echo -e "OpModelLib build failed\n" >> logs/bisect_log.log
    exit 1
fi
./build/test/unittests/OpModel/TTNN/Lib/TestOpModelLib |& tee logs/opmodellib.log
if [ $? -ne 0 ]; then
    echo -e "OpModelLib test failed\n" >> logs/bisect_log.log
    exit 1
fi
### interface
cmake --build ./build --target TestOpModelInterface |& tee logs/lit_opmodeliface.log 
if [ $? -ne 0 ]; then
    echo -e "OpModelInterface build failed\n" >> logs/bisect_log.log
    exit 1
fi
./build/test/unittests/OpModel/TTNN/Op/TestOpModelInterface |& tee logs/opmodeliface.log
if [ $? -ne 0 ]; then
    echo -e "OpModelInterface test failed\n" >> logs/bisect_log.log
    exit 1
fi
### conversion
cmake --build ./build --target TestConversion |& tee logs/lit_opmodelconv.log 
if [ $? -ne 0 ]; then
    echo -e "Conversion build failed\n" >> logs/bisect_log.log
    exit 1
fi
./build/test/unittests/OpModel/TTNN/Conversion/TestConversion |& tee logs/opmodelconv.log
if [ $? -ne 0 ]; then
    echo -e "Conversion test failed\n" >> logs/bisect_log.log
    exit 1
fi


echo -e "Test passed\n" >> logs/bisect_log.log
exit 0