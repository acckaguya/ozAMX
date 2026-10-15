#pragma once

// Numerically equivalent tuning space. BK and each output's product order stay
// fixed; these parameters only change independent work scheduling and locality.
#ifndef OZAMX_CACHE_BLOCK
#define OZAMX_CACHE_BLOCK 128
#endif
#ifndef OZAMX_PREP_GRAIN
#define OZAMX_PREP_GRAIN 16384
#endif
#ifndef OZAMX_MIN_COMPUTE_WORK
#define OZAMX_MIN_COMPUTE_WORK 8
#endif
#ifndef OZAMX_LOOP_ORDER
#define OZAMX_LOOP_ORDER 0
#endif
#ifndef OZAMX_MN_ORDER
#define OZAMX_MN_ORDER 0
#endif
#ifndef OZAMX_NUMA_REPLICATE_B
#define OZAMX_NUMA_REPLICATE_B 0
#endif
#ifndef OZAMX_NUMA_PARTIAL_B
#define OZAMX_NUMA_PARTIAL_B 0
#endif
namespace ozamx::tuning {
inline constexpr unsigned cache_block=OZAMX_CACHE_BLOCK;
inline constexpr unsigned prep_grain=OZAMX_PREP_GRAIN;
inline constexpr unsigned min_compute_work=OZAMX_MIN_COMPUTE_WORK;
inline constexpr unsigned loop_order=OZAMX_LOOP_ORDER;
inline constexpr unsigned mn_order=OZAMX_MN_ORDER;
inline constexpr unsigned numa_replicate_b=OZAMX_NUMA_REPLICATE_B;
inline constexpr unsigned numa_partial_b=OZAMX_NUMA_PARTIAL_B;
static_assert(cache_block>=32 && cache_block<=256 && 256%cache_block==0);
static_assert(prep_grain>0 && min_compute_work>0);
static_assert(loop_order<=1 && mn_order<=1);
static_assert(numa_replicate_b<=1);
static_assert(numa_partial_b<=1);
}
