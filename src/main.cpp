#include "ozamx/gemm.hpp"

#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <string>
#include <vector>

static std::string json_escape(const std::string& s) {
    std::string out;
    for (char c : s) {
        if (c == '"' || c == '\\')
            out.push_back('\\');
        if (c == '\n') {
            out += "\\n";
            continue;
        }
        out.push_back(c);
    }
    return out;
}

static void print_probe() {
    const auto s = ozamx::request_amx_permission_for_current_thread();
    std::cout << "{\"status\":\"" << (s.permission_available ? "ready" : "unsupported")
              << "\",\"cpu_amx_tile\":" << (s.cpu_amx_tile ? "true" : "false")
              << ",\"cpu_amx_bf16\":" << (s.cpu_amx_bf16 ? "true" : "false")
              << ",\"permission_requested\":" << (s.permission_requested ? "true" : "false")
              << ",\"permission_scope\":\"process\",\"permission_available_for_process\":"
              << (s.permission_available ? "true" : "false") << ",\"message\":\""
              << json_escape(s.message) << "\"}\n";
}

static int arg_value(int& i, int argc, char** argv, const char* option) {
    if (i + 1 >= argc)
        throw ozamx::Error(std::string("missing value for ") + option);
    return ++i;
}

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "probe") {
            print_probe();
            return 0;
        }
        if (argc < 2 || std::string(argv[1]) != "gemm")
            throw ozamx::Error("usage: ozamx_cli probe | gemm --precision fp32|fp64 --m M --n N "
                               "--k K [--budget 6|10|15|21] [--seed S]");

        std::string precision;
        std::size_t m = 0, n = 0, k = 0;
        int budget_n = 6;
        std::uint64_t seed = 1;
        bool have_m = false, have_n = false, have_k = false;
        for (int i = 2; i < argc; ++i) {
            const std::string key(argv[i]);
            const int vi = arg_value(i, argc, argv, argv[i]);
            const std::string value(argv[vi]);
            if (key == "--precision")
                precision = value;
            else if (key == "--m") {
                m = std::stoull(value);
                have_m = true;
            } else if (key == "--n") {
                n = std::stoull(value);
                have_n = true;
            } else if (key == "--k") {
                k = std::stoull(value);
                have_k = true;
            } else if (key == "--budget")
                budget_n = std::stoi(value);
            else if (key == "--seed")
                seed = std::stoull(value);
            else
                throw ozamx::Error("unknown option: " + key);
        }
        if (precision != "fp32" && precision != "fp64")
            throw ozamx::Error("--precision must be fp32 or fp64");
        if (!have_m || !have_n || !have_k)
            throw ozamx::Error("--m, --n, and --k are required");
        if (budget_n != 6 && budget_n != 10 && budget_n != 15 && budget_n != 21)
            throw ozamx::Error("--budget must be 6, 10, 15, or 21");
        const auto budget = static_cast<ozamx::ProductBudget>(budget_n);
        std::mt19937_64 rng(seed);
        std::uniform_real_distribution<double> dist(-1.0, 1.0);
        const auto product = [](std::size_t x, std::size_t y) {
            if (y && x > std::numeric_limits<std::size_t>::max() / y)
                throw ozamx::Error("matrix size overflow");
            return x * y;
        };
        const std::size_t asz = product(m, k), bsz = product(k, n), csz = product(m, n);

        double seconds = 0.0, split = 0.0, pack = 0.0, compute = 0.0, checksum = 0.0;
        std::string order;
        if (precision == "fp32") {
            std::vector<float> a(asz), b(bsz), c(csz);
            for (auto& x : a)
                x = static_cast<float>(dist(rng));
            for (auto& x : b)
                x = static_cast<float>(dist(rng));
            const auto t =
                ozamx::gemm_fp32_profiled(m, n, k, a.data(), k, b.data(), n, c.data(), n);
            seconds = t.total_seconds;
            split = t.split_seconds;
            pack = t.pack_seconds;
            compute = t.compute_and_reconstruct_seconds;
            for (float x : c)
                checksum += x;
            order = ozamx::product_order_fp32();
        } else {
            std::vector<double> a(asz), b(bsz), c(csz);
            for (auto& x : a)
                x = dist(rng);
            for (auto& x : b)
                x = dist(rng);
            const auto t =
                ozamx::gemm_fp64_profiled(m, n, k, a.data(), k, b.data(), n, c.data(), n, budget);
            seconds = t.total_seconds;
            split = t.split_seconds;
            pack = t.pack_seconds;
            compute = t.compute_and_reconstruct_seconds;
            for (double x : c)
                checksum += x;
            order = ozamx::product_order_fp64(budget);
        }
        std::cout << std::setprecision(17) << "{\"status\":\"ok\",\"precision\":\"" << precision
                  << "\",\"budget\":" << (precision == "fp32" ? 6 : budget_n) << ",\"m\":" << m
                  << ",\"n\":" << n << ",\"k\":" << k << ",\"seed\":" << seed
                  << ",\"rng\":\"mt19937_64_uniform[-1,1]\",\"seconds\":" << seconds
                  << ",\"split_seconds\":" << split << ",\"pack_seconds\":" << pack
                  << ",\"compute_and_reconstruct_seconds\":" << compute
                  << ",\"timing_scope\":\"end_to_end_split_pack_compute_reconstruction\","
                     "\"checksum_sum_c\":"
                  << checksum << ",\"product_order\":\"" << order << "\"}\n";
        return 0;
    } catch (const std::exception& e) {
        std::cout << "{\"status\":\"error\",\"message\":\"" << json_escape(e.what()) << "\"}\n";
        return 2;
    }
}
