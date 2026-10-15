cmake_minimum_required(VERSION 3.16)
project(ozamx_roofline_v4_search LANGUAGES C CXX ASM)

set(OZV4_MODE 0 CACHE STRING "0=control, 1=FP32 plain NF diagnostic, 2=no-reconstruction diagnostic, 3=late FP32 candidate")
if(NOT OZV4_MODE MATCHES "^[0-3]$")
  message(FATAL_ERROR "OZV4_MODE must be 0, 1, 2, or 3")
endif()
option(OZAMX_ENABLE_OPENMP "Enable OpenMP" ON)
set(OZAMX_ONEMKL_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../third_party/code/mkl-current" CACHE PATH "oneMKL root")

# Search-space controls. Defaults reproduce V3's existing wide geometry and
# batch-2 FP64 reconstruction. BK=256 and the product ordering are fixed.
set(OZV4_FP64_BATCH 2 CACHE STRING "Wide FP64 reconstruction batch: 2, 4, 8, 12, or 21")
set_property(CACHE OZV4_FP64_BATCH PROPERTY STRINGS 2 4 8 12 21)
set(OZV4_WIDE_CBM 128 CACHE STRING "Wide output M blocking: 64, 128, or 256")
set_property(CACHE OZV4_WIDE_CBM PROPERTY STRINGS 64 128 256)
set(OZV4_WIDE_CBN 0 CACHE STRING "Wide output N blocking: 0=V3 automatic, or 128, 256, 512, 1024")
set_property(CACHE OZV4_WIDE_CBN PROPERTY STRINGS 0 128 256 512 1024)
set(OZV4_WIDE_PAD_BYTES 64 CACHE STRING "Wide C-row padding in bytes: 0, 64, or 128")
set_property(CACHE OZV4_WIDE_PAD_BYTES PROPERTY STRINGS 0 64 128)
set(OZV4_FP32_LATE32 1 CACHE STRING "Mode 3 late FP32 non-finite scan: 0=off, 1=on")
set_property(CACHE OZV4_FP32_LATE32 PROPERTY STRINGS 0 1)
set(OZAMX_TILELOAD_HINT 1 CACHE STRING "AMX input tile load hint: 0=tileloadd, 1=tileloaddt1")
set_property(CACHE OZAMX_TILELOAD_HINT PROPERTY STRINGS 0 1)

if(NOT OZV4_FP64_BATCH MATCHES "^(2|4|8|12|21)$")
  message(FATAL_ERROR "OZV4_FP64_BATCH must be 2, 4, 8, 12, or 21")
endif()
if(NOT OZV4_WIDE_CBM MATCHES "^(64|128|256)$")
  message(FATAL_ERROR "OZV4_WIDE_CBM must be 64, 128, or 256")
endif()
if(NOT OZV4_WIDE_CBN MATCHES "^(0|128|256|512|1024)$")
  message(FATAL_ERROR "OZV4_WIDE_CBN must be 0 (V3 automatic), 128, 256, 512, or 1024")
endif()
if(NOT OZV4_WIDE_PAD_BYTES MATCHES "^(0|64|128)$")
  message(FATAL_ERROR "OZV4_WIDE_PAD_BYTES must be 0, 64, or 128")
endif()
if(NOT OZV4_FP32_LATE32 MATCHES "^[01]$" OR NOT OZAMX_TILELOAD_HINT MATCHES "^[01]$")
  message(FATAL_ERROR "OZV4_FP32_LATE32 and OZAMX_TILELOAD_HINT must be 0 or 1")
endif()

option(OZV4_RECON_ILP4 "Interleave eight FP64 reconstruction chains in GAS" ON)
add_library(ozamx STATIC src/runtime.cpp src/gemm.cpp src/kernels.S src/reconstruct_ilp4.S)
target_compile_definitions(ozamx PRIVATE OZV4_RECON_ILP4=$<BOOL:${OZV4_RECON_ILP4}>)
target_include_directories(ozamx PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_features(ozamx PUBLIC cxx_std_17)
target_compile_definitions(ozamx PRIVATE
  OZV4_MODE=${OZV4_MODE}
  OZV4_FP64_BATCH=${OZV4_FP64_BATCH}
  OZV4_WIDE_CBM=${OZV4_WIDE_CBM}
  OZV4_WIDE_CBN=${OZV4_WIDE_CBN}
  OZV4_WIDE_PAD_BYTES=${OZV4_WIDE_PAD_BYTES}
  OZV4_FP32_LATE32=${OZV4_FP32_LATE32}
  OZAMX_TILELOAD_HINT=${OZAMX_TILELOAD_HINT}
  OZAMX_LOAD_SCHEDULE=0)
target_compile_options(ozamx PRIVATE -O3 -Wall -Wextra -Wpedantic -mamx-tile -mamx-bf16)
set_source_files_properties(src/gemm.cpp PROPERTIES COMPILE_OPTIONS "-march=sapphirerapids;-ffp-contract=off;-fno-fast-math")
if(OZAMX_ENABLE_OPENMP)
  find_package(OpenMP REQUIRED COMPONENTS CXX)
  target_link_libraries(ozamx PUBLIC OpenMP::OpenMP_CXX)
endif()

find_file(OZAMX_ONEMKL_RUNTIME NAMES libmkl_rt.so.3 libmkl_rt.so.2 libmkl_rt.so PATHS "${OZAMX_ONEMKL_ROOT}/lib" NO_DEFAULT_PATH REQUIRED)
add_library(ozamx_onemkl_runtime SHARED IMPORTED GLOBAL)
set_target_properties(ozamx_onemkl_runtime PROPERTIES IMPORTED_LOCATION "${OZAMX_ONEMKL_RUNTIME}")
add_library(ozamx_onemkl INTERFACE)
target_include_directories(ozamx_onemkl INTERFACE "${OZAMX_ONEMKL_ROOT}/include")
target_link_libraries(ozamx_onemkl INTERFACE ozamx_onemkl_runtime)

add_executable(ozamx_benchmark bench/benchmark.cpp)
target_compile_definitions(ozamx_benchmark PRIVATE
  OZV4_MODE=${OZV4_MODE}
  OZV4_FP64_BATCH=${OZV4_FP64_BATCH}
  OZV4_WIDE_CBM=${OZV4_WIDE_CBM}
  OZV4_WIDE_CBN=${OZV4_WIDE_CBN}
  OZV4_WIDE_PAD_BYTES=${OZV4_WIDE_PAD_BYTES}
  OZV4_FP32_LATE32=${OZV4_FP32_LATE32}
  OZAMX_TILELOAD_HINT=${OZAMX_TILELOAD_HINT})
target_compile_options(ozamx_benchmark PRIVATE -O3 -march=sapphirerapids -ffp-contract=off -fno-fast-math -mamx-tile -mamx-bf16)
target_link_libraries(ozamx_benchmark PRIVATE ozamx ozamx_onemkl ${CMAKE_DL_LIBS})
add_executable(ozamx_optimization_benchmark bench/optimization_benchmark.cpp)
target_compile_options(ozamx_optimization_benchmark PRIVATE -O3 -march=sapphirerapids -ffp-contract=off -fno-fast-math)
target_link_libraries(ozamx_optimization_benchmark PRIVATE ozamx)
add_executable(ozamx_roofline_binary_gate_v4 tools/roofline_binary_gate_v4.cpp)
target_compile_options(ozamx_roofline_binary_gate_v4 PRIVATE -O3 -march=sapphirerapids -ffp-contract=off -fno-fast-math)
target_link_libraries(ozamx_roofline_binary_gate_v4 PRIVATE ozamx)

include(CTest)
if(BUILD_TESTING)
  add_executable(ozamx_validation tests/validation.cpp)
  target_compile_options(ozamx_validation PRIVATE -O3 -march=sapphirerapids -ffp-contract=off -fno-fast-math -mamx-tile -mamx-bf16)
  target_link_libraries(ozamx_validation PRIVATE ozamx)
  add_test(NAME ozamx_validation COMMAND ozamx_validation)
  add_executable(ozamx_late_path_probe tests/final_late_path_probe.cpp)
  target_compile_options(ozamx_late_path_probe PRIVATE -O3 -march=sapphirerapids -ffp-contract=off -fno-fast-math)
  target_link_libraries(ozamx_late_path_probe PRIVATE ozamx)
  add_test(NAME ozamx_late_path_probe COMMAND ozamx_late_path_probe)
  add_executable(ozamx_alias_output_probe tests/bounded_commit_alias_probe.cpp)
  target_compile_options(ozamx_alias_output_probe PRIVATE -O3 -march=sapphirerapids -ffp-contract=off -fno-fast-math)
  target_link_libraries(ozamx_alias_output_probe PRIVATE ozamx)
  add_test(NAME ozamx_alias_output_probe COMMAND ozamx_alias_output_probe)
  add_executable(ozamx_reconstruct_ilp4_probe tests/reconstruct_ilp4_probe.cpp tests/reconstruct_ilp4_abi_probe.S)
  target_compile_options(ozamx_reconstruct_ilp4_probe PRIVATE -O2 -march=sapphirerapids -ffp-contract=off -fno-fast-math)
  target_link_libraries(ozamx_reconstruct_ilp4_probe PRIVATE ozamx)
  add_test(NAME ozamx_reconstruct_ilp4_probe COMMAND ozamx_reconstruct_ilp4_probe)
endif()

# Persist enough configuration and source identity beside every isolated build.
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/src/gemm.cpp" OZV4_GEMM_SHA256)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/src/kernels.S" OZV4_KERNELS_SHA256)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/src/reconstruct_ilp4.S" OZV4_RECON_SOURCE_SHA256)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/include/ozamx/gemm.hpp" OZV4_HEADER_SHA256)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/bench/benchmark.cpp" OZV4_DRIVER_SHA256)
file(SHA256 "${OZAMX_ONEMKL_RUNTIME}" OZV4_MKL_RUNTIME_SHA256)
file(WRITE "${CMAKE_BINARY_DIR}/build_identity.json"
  "{\n"
  "  \"mode\": ${OZV4_MODE},\n"
  "  \"build_type\": \"${CMAKE_BUILD_TYPE}\",\n"
  "  \"compiler_id\": \"${CMAKE_CXX_COMPILER_ID}\",\n"
  "  \"compiler_version\": \"${CMAKE_CXX_COMPILER_VERSION}\",\n"
  "  \"fp64_batch\": ${OZV4_FP64_BATCH},\n"
  "  \"wide_cbm\": ${OZV4_WIDE_CBM},\n"
  "  \"wide_cbn\": ${OZV4_WIDE_CBN},\n"
  "  \"wide_pad_bytes\": ${OZV4_WIDE_PAD_BYTES},\n"
  "  \"fp32_late32\": ${OZV4_FP32_LATE32},\n"
  "  \"tileload_hint\": ${OZAMX_TILELOAD_HINT},\n"
  "  \"bk\": 256,\n"
  "  \"reconstruction_ilp4\": \"${OZV4_RECON_ILP4}\",\n"
  "  \"reconstruction_source_sha256\": \"${OZV4_RECON_SOURCE_SHA256}\",\n"
  "  \"gemm_source_sha256\": \"${OZV4_GEMM_SHA256}\",\n"
  "  \"kernels_source_sha256\": \"${OZV4_KERNELS_SHA256}\",\n"
  "  \"public_header_sha256\": \"${OZV4_HEADER_SHA256}\",\n"
  "  \"benchmark_driver_sha256\": \"${OZV4_DRIVER_SHA256}\",\n"
  "  \"mkl_runtime_sha256\": \"${OZV4_MKL_RUNTIME_SHA256}\"\n"
  "}\n")
