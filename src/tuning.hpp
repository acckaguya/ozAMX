#pragma once

#ifndef OZAMX_STRICT_PATH
#define OZAMX_STRICT_PATH 1
#endif
#ifndef OZAMX_STRICT_LOCAL_STAGING
#define OZAMX_STRICT_LOCAL_STAGING 1
#endif
#ifndef OZAMX_RESEARCH_STAGING_PIPELINE
#define OZAMX_RESEARCH_STAGING_PIPELINE 0
#endif
#ifndef OZAMX_PREP_SINGLE_REGION
#define OZAMX_PREP_SINGLE_REGION 0
#endif
#ifndef OZAMX_COMMIT_IN_COMPUTE
#define OZAMX_COMMIT_IN_COMPUTE 0
#endif
#ifndef OZAMX_SINGLE_TASK_SERIAL
#define OZAMX_SINGLE_TASK_SERIAL 0
#endif
#ifndef OZAMX_RESEARCH_TASK_TEAMS
#define OZAMX_RESEARCH_TASK_TEAMS 0
#endif
#ifndef OZAMX_RESEARCH_PACK_USED_SLICES
#define OZAMX_RESEARCH_PACK_USED_SLICES 0
#endif
#ifndef OZAMX_PREP_FUSED_MAX
#define OZAMX_PREP_FUSED_MAX 0
#endif
#ifndef OZAMX_PACK_NT_STORE
#define OZAMX_PACK_NT_STORE 0
#endif
#ifndef OZAMX_STRICT_PREP_FUSED_DIRECT
#define OZAMX_STRICT_PREP_FUSED_DIRECT 0
#endif

// Numerically equivalent tuning space. BK and each output's product order stay
// fixed; these parameters only change independent work scheduling and locality.
// CACHE_BLOCK controls M/N cache tiles; PREP_GRAIN is preprocessing work per
// scheduling chunk; MIN_COMPUTE_WORK sets the threshold for parallel compute.
// LOOP_ORDER and MN_ORDER select loop traversal variants (0 or 1).
#ifndef OZAMX_CACHE_BLOCK
#define OZAMX_CACHE_BLOCK 128
#endif
#ifndef OZAMX_STRICT_FP64_ROW_PAD_BYTES
#define OZAMX_STRICT_FP64_ROW_PAD_BYTES 0
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
namespace ozamx::tuning {
inline constexpr bool research_task_teams = OZAMX_RESEARCH_TASK_TEAMS;
inline constexpr bool research_staging_pipeline = OZAMX_RESEARCH_STAGING_PIPELINE;
inline constexpr bool prep_single_region = OZAMX_PREP_SINGLE_REGION;
inline constexpr bool commit_in_compute = OZAMX_COMMIT_IN_COMPUTE;
inline constexpr bool single_task_serial = OZAMX_SINGLE_TASK_SERIAL;
inline constexpr bool research_pack_used_slices = OZAMX_RESEARCH_PACK_USED_SLICES;
inline constexpr bool prep_fused_max = OZAMX_PREP_FUSED_MAX;
inline constexpr bool pack_nt_store = OZAMX_PACK_NT_STORE;
inline constexpr bool strict_prep_fused_direct = OZAMX_STRICT_PREP_FUSED_DIRECT;
inline constexpr unsigned cache_block = OZAMX_CACHE_BLOCK;
inline constexpr unsigned strict_fp64_row_pad_bytes = OZAMX_STRICT_FP64_ROW_PAD_BYTES;
inline constexpr unsigned prep_grain = OZAMX_PREP_GRAIN;
inline constexpr unsigned min_compute_work = OZAMX_MIN_COMPUTE_WORK;
inline constexpr unsigned loop_order = OZAMX_LOOP_ORDER;
inline constexpr unsigned mn_order = OZAMX_MN_ORDER;
static_assert(cache_block >= 32 && cache_block <= 256 && 256 % cache_block == 0);
static_assert(strict_fp64_row_pad_bytes % 64 == 0);
static_assert(prep_grain > 0 && min_compute_work > 0);
static_assert(loop_order <= 1 && mn_order <= 1);
} // namespace ozamx::tuning
