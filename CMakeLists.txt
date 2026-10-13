cmake_minimum_required(VERSION 3.16)
project(ozamx VERSION 0.1.0 LANGUAGES C CXX)

option(OZAMX_ENABLE_OPENMP "Enable OpenMP parallel execution" ON)
option(OZAMX_BUILD_PROBE "Build the standalone AMX instruction probe" ON)

add_library(ozamx STATIC src/runtime.cpp src/gemm.cpp)
target_include_directories(ozamx PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_features(ozamx PUBLIC cxx_std_17)
target_compile_options(ozamx PRIVATE -Wall -Wextra -Wpedantic -mamx-tile -mamx-bf16)
target_compile_options(ozamx PRIVATE $<$<CONFIG:Release>:-O3>)

if(OZAMX_ENABLE_OPENMP)
  find_package(OpenMP REQUIRED COMPONENTS CXX)
  target_link_libraries(ozamx PUBLIC OpenMP::OpenMP_CXX)
endif()

add_executable(ozamx_cli src/main.cpp)
target_link_libraries(ozamx_cli PRIVATE ozamx)

if(OZAMX_BUILD_PROBE)
  add_executable(ozamx_amx_probe tools/amx_probe.c)
  target_compile_options(ozamx_amx_probe PRIVATE -Wall -Wextra -mamx-tile -mamx-bf16)
endif()

# Optional link interface for local Intel oneMKL reference programs/benchmarks.
set(OZAMX_ONEMKL_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/third_party/code/mkl-2026/venv" CACHE PATH "Local oneMKL files")
find_file(OZAMX_ONEMKL_RUNTIME NAMES libmkl_rt.so.3 libmkl_rt.so.2 libmkl_rt.so
  PATHS "${OZAMX_ONEMKL_ROOT}/lib" NO_DEFAULT_PATH)
if(OZAMX_ONEMKL_RUNTIME)
  add_library(ozamx_onemkl_runtime SHARED IMPORTED GLOBAL)
  set_target_properties(ozamx_onemkl_runtime PROPERTIES IMPORTED_LOCATION "${OZAMX_ONEMKL_RUNTIME}")
  add_library(ozamx_onemkl INTERFACE)
  target_include_directories(ozamx_onemkl INTERFACE "${OZAMX_ONEMKL_ROOT}/include")
  target_link_libraries(ozamx_onemkl INTERFACE ozamx_onemkl_runtime)
endif()

if(OZAMX_ONEMKL_RUNTIME AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/bench/benchmark.cpp")
  add_executable(ozamx_benchmark bench/benchmark.cpp)
  target_link_libraries(ozamx_benchmark PRIVATE ozamx ozamx_onemkl)
  target_compile_options(ozamx_benchmark PRIVATE -mamx-tile -mamx-bf16)
endif()

include(CTest)
if(BUILD_TESTING AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/validation.cpp")
  add_executable(ozamx_validation tests/validation.cpp)
  target_link_libraries(ozamx_validation PRIVATE ozamx)
  target_compile_options(ozamx_validation PRIVATE -mamx-tile -mamx-bf16)
  add_test(NAME ozamx_validation COMMAND ozamx_validation)
endif()
