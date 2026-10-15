#include "ozamx/gemm.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <limits>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>
#include <sys/resource.h>
#ifdef _OPENMP
#include <omp.h>
#endif

static std::vector<int> parse_sizes(const std::string& text) {
    if (text.empty()) throw std::runtime_error("--sizes cannot be empty");
    std::vector<int> values;
    std::stringstream stream(text);
    std::string token;
    while (std::getline(stream, token, ',')) {
        if (token.empty()) throw std::runtime_error("--sizes contains an empty item");
        std::size_t used = 0;
        const unsigned long long value = std::stoull(token, &used);
        if (used != token.size() || value == 0 || value > static_cast<unsigned long long>(std::numeric_limits<int>::max()))
            throw std::runtime_error("--sizes values must be positive integers");
        values.push_back(static_cast<int>(value));
    }
    if (values.empty() || text.back() == ',') throw std::runtime_error("--sizes must contain at least one positive size");
    return values;
}

static std::vector<int> parse_budgets(const std::string& text) {
    if (text.empty()) throw std::runtime_error("--budgets cannot be empty");
    std::vector<int> budgets;
    std::stringstream stream(text);
    std::string token;
    while (std::getline(stream, token, ',')) {
        if (token.empty()) throw std::runtime_error("--budgets contains an empty item");
        std::size_t used = 0;
        const int value = std::stoi(token, &used);
        if (used != token.size() || (value != 6 && value != 10 && value != 15 && value != 21))
            throw std::runtime_error("budgets must be selected from 6,10,15,21");
        if (std::find(budgets.begin(), budgets.end(), value) != budgets.end())
            throw std::runtime_error("--budgets contains a duplicate");
        budgets.push_back(value);
    }
    if (budgets.empty() || text.back() == ',') throw std::runtime_error("--budgets must contain at least one value");
    return budgets;
}

static int parse_positive_int(const std::string& text, const char* option) {
    std::size_t used = 0;
    const long value = std::stol(text, &used);
    if (used != text.size() || value < 1 || value > std::numeric_limits<int>::max())
        throw std::runtime_error(std::string(option) + " must be a positive integer");
    return static_cast<int>(value);
}

static std::size_t checked_count(int n) {
    const auto d = static_cast<std::size_t>(n);
    if (d > std::numeric_limits<std::size_t>::max() / d)
        throw std::runtime_error("matrix element count overflows size_t");
    return d * d;
}

struct TimingRow {
    std::string record;
    int rep;
    ozamx::GemmTimings timing;
    double checksum;
    double wall_seconds=0;
    long minor_faults=0,major_faults=0,voluntary_switches=0,involuntary_switches=0,max_rss_kib=0;
    double user_seconds=0,system_seconds=0;
};

static void emit_row(std::ostream& out, const std::string& precision, int n, int budget,
                     std::uint64_t seed, const TimingRow& row) {
    out << row.record << ',' << precision << ',' << n << ',' << budget << ',' << row.rep << ',' << seed << ','
        << row.timing.split_seconds << ',' << row.timing.pack_seconds << ','
        << row.timing.replicate_b_seconds << ',' << row.timing.replicate_node0_workers << ','
        << row.timing.replicate_node1_workers << ',' << row.timing.replicate_fallback_workers << ','
        << row.timing.compute_and_reconstruct_seconds << ',' << row.timing.total_seconds << ','
        << row.checksum << ",,,,," << row.wall_seconds << ',' << row.minor_faults << ',' << row.major_faults << ','
        << row.voluntary_switches << ',' << row.involuntary_switches << ',' << row.user_seconds << ','
        << row.system_seconds << ',' << row.max_rss_kib << '\n';
}

static void summarize(std::ostream& out, const std::string& precision, int n, int budget,
                      const std::vector<TimingRow>& rows) {
    const char* names[] = {"split", "pack", "copy", "compute", "total", "wall"};
    for (int field = 0; field < 6; ++field) {
        std::vector<double> values;
        values.reserve(rows.size());
        for (const auto& row : rows) {
            const auto& t = row.timing;
            values.push_back(field == 0 ? t.split_seconds : field == 1 ? t.pack_seconds :
                             field == 2 ? t.replicate_b_seconds : field == 3 ? t.compute_and_reconstruct_seconds :
                             field == 4 ? t.total_seconds : row.wall_seconds);
        }
        const double mean = std::accumulate(values.begin(), values.end(), 0.0) / values.size();
        double variance = 0;
        for (double value : values) variance += (value - mean) * (value - mean);
        const double sd = std::sqrt(variance / values.size());
        const auto [lo, hi] = std::minmax_element(values.begin(), values.end());
        out << "summary_" << names[field] << ',' << precision << ',' << n << ',' << budget
            << ",-1,0,,,,,,,,,," << mean << ',' << sd << ',' << *lo << ',' << *hi << ",,,,,,,,\n";
    }
}

template<class T>
static TimingRow run_gemm(int n, int budget, const std::vector<T>& a,
                          const std::vector<T>& b, std::vector<T>& c) {
    const auto d = static_cast<std::size_t>(n);
    ozamx::GemmTimings timing;
    rusage before{},after{};
    if(getrusage(RUSAGE_SELF,&before)!=0)throw std::runtime_error("getrusage failed");
    const auto begin=std::chrono::steady_clock::now();
    if constexpr (std::is_same_v<T, float>) {
        timing = ozamx::gemm_fp32_profiled(d, d, d, a.data(), d, b.data(), d, c.data(), d);
    } else {
        timing = ozamx::gemm_fp64_profiled(d, d, d, a.data(), d, b.data(), d, c.data(), d,
                                           static_cast<ozamx::ProductBudget>(budget));
    }
    const double wall=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
    if(getrusage(RUSAGE_SELF,&after)!=0)throw std::runtime_error("getrusage failed");
    double checksum = 0;
    for (T value : c) checksum += static_cast<double>(value);
    TimingRow row{"rep",0,timing,checksum};row.wall_seconds=wall;
    row.minor_faults=after.ru_minflt-before.ru_minflt;row.major_faults=after.ru_majflt-before.ru_majflt;
    row.voluntary_switches=after.ru_nvcsw-before.ru_nvcsw;row.involuntary_switches=after.ru_nivcsw-before.ru_nivcsw;
    row.max_rss_kib=after.ru_maxrss;
    const auto seconds=[](timeval t){return double(t.tv_sec)+double(t.tv_usec)*1e-6;};
    row.user_seconds=seconds(after.ru_utime)-seconds(before.ru_utime);
    row.system_seconds=seconds(after.ru_stime)-seconds(before.ru_stime);
    return row;
}

template<class T>
static void run_configuration(std::ostream& out, const std::string& precision, int n,
                              int budget, int reps, std::uint64_t seed) {
    const std::size_t count = checked_count(n);
    std::vector<T> a(count), b(count), c(count);
    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<T> distribution(T(-1), T(1));
    for (auto& value : a) value = distribution(rng);
    for (auto& value : b) value = distribution(rng);

    // Input generation and allocation are outside timing. Warmup and recorded
    // repetitions all use these exact same A and B arrays.
    TimingRow warmup = run_gemm(n, budget, a, b, c);
    warmup.record = "warmup";
    warmup.rep = -1;
    emit_row(out, precision, n, budget, seed, warmup);

    std::vector<TimingRow> rows;
    rows.reserve(static_cast<std::size_t>(reps));
    for (int rep = 0; rep < reps; ++rep) {
        TimingRow row = run_gemm(n, budget, a, b, c);
        row.rep = rep;
        emit_row(out, precision, n, budget, seed, row);
        rows.push_back(row);
    }
    summarize(out, precision, n, budget, rows);
    out.flush();
}

int main(int argc, char** argv) try {
    std::string sizes = "256,1024,4096";
    std::string output = "optimization_benchmark.csv";
    std::string precision = "all";
    int threads = 64, reps = 5, budget = 0;
    bool explicit_budgets = false;
    bool budget_option = false;
    std::vector<int> budgets{6, 21};
    for (int i = 1; i < argc; ++i) {
        const std::string option(argv[i]);
        if (option == "--help" || option == "-h") {
            std::cout << "Usage: optimization_benchmark [--sizes N[,N...]] [--precision all|fp32|fp64] "
                         "[--threads N] [--reps N] [--budget 0|all|6|10|15|21] "
                         "[--budgets 6,10,15,21] [--output PATH]\n";
            return 0;
        }
        if (i + 1 >= argc) throw std::runtime_error("missing value for " + option);
        const std::string value(argv[++i]);
        if (option == "--sizes") sizes = value;
        else if (option == "--precision") precision = value;
        else if (option == "--threads") threads = parse_positive_int(value, "--threads");
        else if (option == "--reps") reps = parse_positive_int(value, "--reps");
        else if (option == "--output") output = value;
        else if (option == "--budget") {
            if (explicit_budgets || budget_option) throw std::runtime_error("use either --budget or --budgets, not both");
            budget_option = true;
            if (value == "all" || value == "0") { budget = 0; budgets = {6, 21}; }
            else {
                std::size_t used = 0;
                budget = std::stoi(value, &used);
                if (used != value.size() || (budget != 6 && budget != 10 && budget != 15 && budget != 21))
                    throw std::runtime_error("--budget must be all, 0, 6, 10, 15, or 21");
                budgets = {budget};
            }
        } else if (option == "--budgets") {
            if (budget_option || explicit_budgets) throw std::runtime_error("use either --budget or --budgets, not both");
            budgets = parse_budgets(value);
            explicit_budgets = true;
        } else throw std::runtime_error("unknown option: " + option);
    }
    if (precision != "all" && precision != "fp32" && precision != "fp64")
        throw std::runtime_error("--precision must be all, fp32, or fp64");
    const std::vector<int> dimensions = parse_sizes(sizes);
    for (int n : dimensions) {
        const std::size_t count = checked_count(n);
        if (count > std::vector<float>().max_size() || count > std::vector<double>().max_size())
            throw std::runtime_error("matrix element count exceeds vector max_size");
    }
#ifdef _OPENMP
    omp_set_dynamic(0);
    omp_set_num_threads(threads);
#endif
    std::ofstream out(output);
    if (!out) throw std::runtime_error("cannot open output: " + output);
    out << "record,precision,size,budget,rep,seed,split_s,pack_s,replicate_b_s,replica_node0_workers,replica_node1_workers,replica_fallback_workers,compute_s,total_s,checksum,mean_s,std_s,min_s,max_s,wall_s,minor_faults,major_faults,voluntary_switches,involuntary_switches,user_s,system_s,max_rss_kib\n"
        << std::setprecision(17);
    for (int n : dimensions) {
        if (precision != "fp64") {
            const std::uint64_t seed = 0x8454ULL + static_cast<std::uint64_t>(n) * 17;
            run_configuration<float>(out, "fp32", n, 6, reps, seed);
        }
        if (precision != "fp32") {
            const std::uint64_t seed = 0x8454ULL + static_cast<std::uint64_t>(n) * 17 + 1;
            for (int current_budget : budgets)
                run_configuration<double>(out, "fp64", n, current_budget, reps, seed);
        }
    }
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 2;
}
