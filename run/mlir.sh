#!/bin/bash

# Repo setup
# Use docker image ghcr.io/tenstorrent/tt-mlir/tt-mlir-ird-ubuntu-22-04:latest
# source env/activate

{ # Script setup
    set -o pipefail # to make sure exit status is propagated even when using tee to capture output logs
    mkdir -p logs/build
    source "$(dirname "$0")/common.sh" # Source common functions
    echo -e "\n\nbisecting commit: $(git log -1 --oneline)\n" >> logs/bisect_log.log
    # echo -e "Currently bisecting commit:\n$(git log -1 --oneline)\n\nWindow remaining:\n$(git bisect visualize --oneline)" > logs/bisect_status.log
}

{ # build steps
    rm -rf build third_party/tt-metal
    ## speedy
    cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang-17 -DCMAKE_CXX_COMPILER=clang++-17 -DTTMLIR_ENABLE_RUNTIME=ON -DTTMLIR_ENABLE_RUNTIME_TESTS=ON -DCMAKE_CXX_COMPILER_LAUNCHER=ccache -DTTMLIR_ENABLE_STABLEHLO=ON -DTTMLIR_ENABLE_OPMODEL=ON |& tee logs/build/cmake_cfg.log
    ## tracy
    #cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang-17 -DCMAKE_CXX_COMPILER=clang++-17 -DTTMLIR_ENABLE_RUNTIME=ON -DTT_RUNTIME_ENABLE_PERF_TRACE=ON -DTTMLIR_ENABLE_RUNTIME_TESTS=ON -DCMAKE_CXX_COMPILER_LAUNCHER=ccache -DTT_RUNTIME_DEBUG=ON -DTTMLIR_ENABLE_STABLEHLO=ON |& tee logs/build/cmake_cfg.log
    log_result $? "cmake-config" $UP_SKIP

    cmake --build build |& tee logs/build/build.log; log_result $? "cmake-build" $UP_SKIP

    rm -rf ttrt-artifacts
    ttrt query --save-artifacts |& tee logs/artifacts.log; log_result $? "ttrt-query" $UP_SKIP
    export SYSTEM_DESC_PATH=`pwd`/ttrt-artifacts/system_desc.ttsys
}

# Exit early
# echo -e "Build passed\n" >> logs/bisect_log.log
# exit 0

# regtest
cmake --build build -- check-ttmlir |& tee logs/check_ttmlir.log
log_result $? "check-ttmlir" $UP_BAD

{ # op model tests
    { # op model lib
        cmake --build ./build --target TestOpModelLib |& tee logs/lit_opmodellib.log
        log_result $? "TestOpModelLib-build"
        ./build/test/unittests/OpModel/TTNN/Lib/TestOpModelLib |& tee logs/opmodellib.log
        log_result $? "TestOpModelLib-test"
    }
    { # op model interface
        cmake --build ./build --target TestOpModelInterface |& tee logs/lit_opmodeliface.log
        log_result $? "TestOpModelInterface-build"
        ./build/test/unittests/OpModel/TTNN/Op/TestOpModelInterface |& tee logs/opmodeliface.log
        log_result $? "TestOpModelInterface-test"
    }
    { # op model conversion
        cmake --build ./build --target TestConversion |& tee logs/lit_opmodelconv.log
        log_result $? "TestConversion-build"
        ./build/test/unittests/OpModel/TTNN/Conversion/TestConversion |& tee logs/opmodelconv.log
        log_result $? "TestConversion-test"
    }
}


echo -e "Test passed\n" >> logs/bisect_log.log
exit 0