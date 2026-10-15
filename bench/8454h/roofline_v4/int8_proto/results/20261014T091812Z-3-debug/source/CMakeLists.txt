cmake_minimum_required(VERSION 3.18)
project(ozamx_int8_36_prototype LANGUAGES CXX ASM)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

get_filename_component(_repo_root "${CMAKE_CURRENT_SOURCE_DIR}/../../../../" ABSOLUTE)
set(OZAMX_V3_ROOT "${_repo_root}" CACHE PATH "Frozen V3 repository root")
set(OZAMX_V3_LIBRARY
    "${OZAMX_V3_ROOT}/bench/8454h/versions/v3_release/artifacts/libozamx_v3.a"
    CACHE FILEPATH "Frozen V3 static library used for Linux AMX permission")

if(NOT EXISTS "${OZAMX_V3_ROOT}/include/ozamx/gemm.hpp")
    message(FATAL_ERROR "OZAMX_V3_ROOT must name the frozen V3 source tree")
endif()
if(NOT EXISTS "${OZAMX_V3_LIBRARY}")
    message(FATAL_ERROR "Set OZAMX_V3_LIBRARY to the frozen V3 libozamx.a")
endif()

set(OZAMX_I8_BM 128 CACHE STRING "INT8 output row macroblock: 64, 128, or 256")
set(OZAMX_I8_BN 128 CACHE STRING "INT8 output column macroblock: 64, 128, or 256")
set(OZAMX_I8_BK 256 CACHE STRING "INT8 K macroblock: 64, 128, 256, or 512")
option(OZAMX_I8_TILELOAD_HINT "Use TILELOADDT1 for packed A/B tiles" ON)

find_package(OpenMP REQUIRED)
add_library(ozamx_v3_runtime STATIC IMPORTED GLOBAL)
set_target_properties(ozamx_v3_runtime PROPERTIES
    IMPORTED_LOCATION "${OZAMX_V3_LIBRARY}")
add_library(ozamx_int8_36 STATIC int8.cpp kernels.S)
target_include_directories(ozamx_int8_36
    PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}" "${OZAMX_V3_ROOT}/include")
target_compile_options(ozamx_int8_36 PRIVATE
    "$<$<COMPILE_LANGUAGE:CXX>:-O3;-Wall;-Wextra;-Wpedantic;-ffp-contract=off>"
    "$<$<COMPILE_LANGUAGE:ASM>:-mamx-tile;-mamx-int8>")
target_compile_definitions(ozamx_int8_36 PRIVATE
    OZAMX_I8_BM=${OZAMX_I8_BM}
    OZAMX_I8_BN=${OZAMX_I8_BN}
    OZAMX_I8_BK=${OZAMX_I8_BK}
    OZAMX_I8_TILELOAD_HINT=$<BOOL:${OZAMX_I8_TILELOAD_HINT}>)
target_link_libraries(ozamx_int8_36 PUBLIC OpenMP::OpenMP_CXX)
target_link_libraries(ozamx_int8_36 PUBLIC ozamx_v3_runtime)

add_executable(int8_quality_gate quality_gate.cpp)
target_compile_options(int8_quality_gate PRIVATE -O3 -Wall -Wextra -Wpedantic -ffp-contract=off)
target_link_libraries(int8_quality_gate PRIVATE ozamx_int8_36 quadmath)

set(OZAMX_MKL_ROOT "${_repo_root}/third_party/code/mkl-current" CACHE PATH "Local oneMKL installation")
if(NOT EXISTS "${OZAMX_MKL_ROOT}/include/mkl.h" OR NOT EXISTS "${OZAMX_MKL_ROOT}/lib/libmkl_rt.so.3")
    message(FATAL_ERROR "oneMKL is required for the matched INT8/V3/MKL benchmark (set OZAMX_MKL_ROOT)")
endif()
add_library(ozamx_mkl_rt SHARED IMPORTED GLOBAL)
set_target_properties(ozamx_mkl_rt PROPERTIES
    IMPORTED_LOCATION "${OZAMX_MKL_ROOT}/lib/libmkl_rt.so.3")
add_executable(int8_benchmark_driver benchmark_driver.cpp)
target_include_directories(int8_benchmark_driver PRIVATE "${OZAMX_MKL_ROOT}/include")
target_compile_options(int8_benchmark_driver PRIVATE -O3 -Wall -Wextra -Wpedantic -ffp-contract=off)
target_link_libraries(int8_benchmark_driver PRIVATE ozamx_int8_36 ozamx_mkl_rt dl)
set_target_properties(int8_benchmark_driver PROPERTIES
    BUILD_RPATH "${OZAMX_MKL_ROOT}/lib")
