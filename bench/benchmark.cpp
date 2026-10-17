#include "ozamx/gemm.hpp"
#include <mkl.h>
#include <dlfcn.h>
#include <link.h>
#include <sched.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <random>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif

extern char** environ;

namespace {
struct Opts {
    std::vector<std::size_t> sizes{256, 512, 1024, 2048, 4096, 8192, 16384, 32768};
    std::vector<int> budgets{6, 10, 15, 21};
    int threads = 64, reps = 10;
    std::uint64_t seed = 260904;
    std::string precision = "all", dist = "uniform", output = "-", checkpoint = "";
    bool resume = false;
};
std::vector<std::size_t> parse_sizes(const std::string& s) {
    std::vector<std::size_t> v;
    std::stringstream ss(s);
    std::string x;
    while (std::getline(ss, x, ','))
        v.push_back(static_cast<std::size_t>(std::stoull(x)));
    if (v.empty())
        throw std::runtime_error("empty --sizes");
    return v;
}
std::vector<int> parse_budgets(const std::string& s) {
    std::vector<int> v;
    std::stringstream ss(s);
    std::string x;
    while (std::getline(ss, x, ',')) {
        const int b = std::stoi(x);
        if (b != 6 && b != 10 && b != 15 && b != 21)
            throw std::runtime_error("budgets must be 6,10,15,21");
        v.push_back(b);
    }
    if (v.empty())
        throw std::runtime_error("empty --budgets");
    return v;
}
Opts parse(int argc, char** argv) {
    Opts o;
    for (int i = 1; i < argc; ++i) {
        const std::string k = argv[i];
        if (k == "--resume") {
            o.resume = true;
            continue;
        }
        if (k == "--help") {
            std::cout
                << "usage: ozamx_benchmark [--sizes 256,512] [--threads 64] [--reps 10] [--seed N] "
                   "[--precision all|fp32|fp64] [--budgets 6,10,15,21] [--distribution "
                   "uniform|gaussian|scaled] [--output FILE] [--checkpoint FILE]\n";
            std::exit(0);
        }
        if (i + 1 >= argc)
            throw std::runtime_error("missing value for " + k);
        const std::string v = argv[++i];
        if (k == "--sizes")
            o.sizes = parse_sizes(v);
        else if (k == "--budgets")
            o.budgets = parse_budgets(v);
        else if (k == "--threads")
            o.threads = std::stoi(v);
        else if (k == "--reps")
            o.reps = std::stoi(v);
        else if (k == "--seed")
            o.seed = std::stoull(v);
        else if (k == "--precision")
            o.precision = v;
        else if (k == "--distribution")
            o.dist = v;
        else if (k == "--output")
            o.output = v;
        else if (k == "--checkpoint")
            o.checkpoint = v;
        else
            throw std::runtime_error("unknown option: " + k);
    }
    if (o.threads < 1 || o.reps < 1)
        throw std::runtime_error("threads and reps must be positive");
    if (o.precision != "all" && o.precision != "fp32" && o.precision != "fp64")
        throw std::runtime_error("bad precision");
    if (o.dist != "uniform" && o.dist != "gaussian" && o.dist != "scaled")
        throw std::runtime_error("bad distribution");
    return o;
}
std::string budget_name(ozamx::ProductBudget b) {
    return std::to_string(static_cast<int>(b));
}
void fill(std::vector<float>& a, std::vector<float>& b, std::size_t n, const Opts& o,
          std::uint64_t seed) {
    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<float> u(-1.f, 1.f);
    std::normal_distribution<float> g(0.f, .5f);
    std::uniform_int_distribution<int> e(-40, 40);
    for (std::size_t q = 0; q < n * n; ++q) {
        auto v = [&]() {
            float x = o.dist == "gaussian" ? g(rng) : u(rng);
            if (o.dist == "scaled")
                x = std::ldexp(x, e(rng));
            return x;
        };
        a[q] = v();
        b[q] = v();
    }
}
void fill(std::vector<double>& a, std::vector<double>& b, std::size_t n, const Opts& o,
          std::uint64_t seed) {
    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<double> u(-1., 1.);
    std::normal_distribution<double> g(0., .5);
    std::uniform_int_distribution<int> e(-50, 50);
    for (std::size_t q = 0; q < n * n; ++q) {
        auto v = [&]() {
            double x = o.dist == "gaussian" ? g(rng) : u(rng);
            if (o.dist == "scaled")
                x = std::ldexp(x, e(rng));
            return x;
        };
        a[q] = v();
        b[q] = v();
    }
}
struct ErrorMetrics {
    long double ef = 0, scaled = 0;
};
constexpr const char* kCheckpointSourceId = "strict-emulation-paired-api-v3-20261017";
constexpr const char* kTimingSchema = "api-wall-headline-v2";
constexpr const char* kMeasurementProtocol = "paired-alternating-api-first-even";
std::string mkl_version() {
    char b[512]{};
    mkl_get_version_string(b, sizeof(b));
    return b;
}
std::string mkl_runtime_path() {
    Dl_info info{};
    const auto addr = reinterpret_cast<void*>(reinterpret_cast<std::uintptr_t>(&cblas_sgemm));
    return dladdr(addr, &info) && info.dli_fname ? info.dli_fname : "unavailable";
}
std::string mkl_threading_layer() {
    const char* p = std::getenv("MKL_THREADING_LAYER");
    return p ? p : "unset";
}
template <class T> struct MklResult {
    std::vector<T> c;
    std::vector<double> samples;
    double seconds = 0;
};
template <class T>
void mkl_gemm(const std::vector<T>& a, const std::vector<T>& b, std::size_t n,
              std::vector<T>& c) {
    if constexpr (std::is_same_v<T, float>)
        cblas_sgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, (MKL_INT)n, (MKL_INT)n,
                    (MKL_INT)n, 1.f, a.data(), (MKL_INT)n, b.data(), (MKL_INT)n, 0.f,
                    c.data(), (MKL_INT)n);
    else
        cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, (MKL_INT)n, (MKL_INT)n,
                    (MKL_INT)n, 1., a.data(), (MKL_INT)n, b.data(), (MKL_INT)n, 0., c.data(),
                    (MKL_INT)n);
}
template <class T>
ErrorMetrics compare_mkl(const std::vector<T>& got, const MklResult<T>& ref,
                         const std::vector<T>& a, const std::vector<T>& b, std::size_t n) {
    std::vector<double> ad(n * n), bd(n * n), denom(n * n);
    for (std::size_t q = 0; q < n * n; ++q) {
        ad[q] = std::fabs((double)a[q]);
        bd[q] = std::fabs((double)b[q]);
    }
    cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, (MKL_INT)n, (MKL_INT)n, (MKL_INT)n, 1.,
                ad.data(), (MKL_INT)n, bd.data(), (MKL_INT)n, 0., denom.data(), (MKL_INT)n);
    long double e2 = 0, r2 = 0, sc = 0;
    for (std::size_t q = 0; q < n * n; ++q) {
        const long double d = (long double)got[q] - (long double)ref.c[q],
                          v = (long double)ref.c[q], den = denom[q];
        e2 += d * d;
        r2 += v * v;
        sc = std::max(sc, den == 0 ? std::fabs(d) : std::fabs(d) / den);
    }
    return {r2 == 0 ? std::sqrt(e2) : std::sqrt(e2 / r2), sc};
}
template <class T>
ErrorMetrics high_precision(const std::vector<T>& a, const std::vector<T>& b,
                            const std::vector<T>& c, std::size_t n, std::uint64_t seed,
                            std::string& scope) {
    const bool full = n <= 256;
    const std::size_t count = full ? n * n : std::min<std::size_t>(512, n * n);
    std::mt19937_64 rng(seed ^ 0x9e3779b97f4a7c15ULL);
    std::uniform_int_distribution<std::size_t> pick(0, n * n - 1);
#if defined(__SIZEOF_FLOAT128__)
    __float128 e2 = 0, r2 = 0, sc = 0;
    for (std::size_t s = 0; s < count; ++s) {
        const auto ix = full ? s : pick(rng), i = ix / n, j = ix % n;
        __float128 r = 0, ab = 0;
        for (std::size_t k = 0; k < n; ++k) {
            const __float128 x = (__float128)a[i * n + k], y = (__float128)b[k * n + j], p = x * y;
            r += p;
            ab += p < 0 ? -p : p;
        }
        const __float128 d = (__float128)c[ix] - r, ad = d < 0 ? -d : d;
        e2 += d * d;
        r2 += r * r;
        const __float128 v = ab == 0 ? ad : ad / ab;
        if (v > sc)
            sc = v;
    }
    const long double e = static_cast<long double>(e2), r = static_cast<long double>(r2);
    scope = full ? "full_float128" : "512_sample_float128";
    return {r == 0 ? std::sqrt(e) : std::sqrt(e / r), static_cast<long double>(sc)};
#else
    long double e2 = 0, r2 = 0, sc = 0;
    for (std::size_t s = 0; s < count; ++s) {
        const auto ix = full ? s : pick(rng), i = ix / n, j = ix % n;
        long double r = 0, ab = 0;
        for (std::size_t k = 0; k < n; ++k) {
            const long double x = (long double)a[i * n + k], y = (long double)b[k * n + j];
            r += x * y;
            ab += std::fabs(x * y);
        }
        const long double d = (long double)c[ix] - r;
        e2 += d * d;
        r2 += r * r;
        sc = std::max(sc, ab == 0 ? std::fabs(d) : std::fabs(d) / ab);
    }
    scope = full ? "full_long_double" : "512_sample_long_double";
    return {r2 == 0 ? std::sqrt(e2) : std::sqrt(e2 / r2), sc};
#endif
}
std::string raw(const std::vector<double>& v) {
    std::ostringstream s;
    s << std::setprecision(12);
    for (std::size_t i = 0; i < v.size(); ++i) {
        if (i)
            s << ';';
        s << v[i];
    }
    return s.str();
}
// Hash the running executable as well as runtime-readable source. The executable
// binds the compiled driver and statically linked ozAMX, not merely a source label.
std::string sha256_file(const std::string& path) {
    static std::map<std::string, std::string> cached;
    if (const auto it = cached.find(path); it != cached.end())
        return it->second;
    int pipefd[2];
    if (pipe(pipefd) != 0)
        throw std::runtime_error("cannot create SHA-256 pipe");
    const pid_t child = fork();
    if (child == -1) {
        close(pipefd[0]);
        close(pipefd[1]);
        throw std::runtime_error("cannot start SHA-256 utility");
    }
    if (child == 0) {
        if (dup2(pipefd[1], STDOUT_FILENO) == -1)
            _exit(127);
        close(pipefd[0]);
        close(pipefd[1]);
        execl("/usr/bin/sha256sum", "sha256sum", "--zero", "--", path.c_str(),
              static_cast<char*>(nullptr));
        _exit(127);
    }
    close(pipefd[1]);
    std::string output;
    char buffer[4096];
    bool read_ok = true;
    for (;;) {
        const auto count = read(pipefd[0], buffer, sizeof(buffer));
        if (count > 0)
            output.append(buffer, static_cast<std::size_t>(count));
        else if (count == 0)
            break;
        else if (errno != EINTR) {
            read_ok = false;
            break;
        }
    }
    close(pipefd[0]);
    int status = 0;
    pid_t waited;
    do {
        waited = waitpid(child, &status, 0);
    } while (waited == -1 && errno == EINTR);
    const bool digest_ok = output.size() > 64 && output[64] == ' ' &&
                           std::all_of(output.begin(), output.begin() + 64, [](char c) {
                               return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
                           });
    if (!read_ok || waited != child || !WIFEXITED(status) || WEXITSTATUS(status) != 0 ||
        !digest_ok)
        throw std::runtime_error("cannot fingerprint file with /usr/bin/sha256sum: " + path);
    return cached.emplace(path, output.substr(0, 64)).first->second;
}
std::string hex_string(const std::string& value) {
    constexpr char digits[] = "0123456789abcdef";
    std::string encoded;
    encoded.reserve(value.size() * 2);
    for (unsigned char c : value) {
        encoded += digits[c >> 4];
        encoded += digits[c & 15];
    }
    return encoded;
}
struct RunIdentity {
    std::string source_sha256, executable_sha256, mkl_sha256, key;
};
std::string initial_affinity;
std::string affinity_string() {
    cpu_set_t affinity;
    CPU_ZERO(&affinity);
    if (sched_getaffinity(0, sizeof(affinity), &affinity) != 0)
        throw std::runtime_error("cannot fingerprint CPU affinity");
    std::string cpus;
    for (int cpu = 0; cpu < CPU_SETSIZE; ++cpu)
        if (CPU_ISSET(cpu, &affinity))
            cpus += std::to_string(cpu) + ';';
    return cpus;
}
RunIdentity run_identity() {
    RunIdentity id;
    id.source_sha256 = sha256_file(__FILE__);
    id.executable_sha256 = sha256_file("/proc/" + std::to_string(getpid()) + "/exe");
    id.mkl_sha256 = sha256_file(mkl_runtime_path());
    std::ostringstream description;
    auto add = [&](const std::string& name, const std::string& value) {
        description << name.size() << ':' << name << value.size() << ':' << value;
    };
    add("timing_schema", kTimingSchema);
    add("measurement_protocol", kMeasurementProtocol);
    add("runtime_source_sha256", id.source_sha256);
    add("compiled_executable_sha256", id.executable_sha256);
    add("mkl_runtime_sha256", id.mkl_sha256);
    std::vector<std::string> objects;
    dl_iterate_phdr(
        [](dl_phdr_info* info, std::size_t, void* data) {
            if (info->dlpi_name && *info->dlpi_name &&
                std::string(info->dlpi_name).find("linux-vdso") == std::string::npos)
                static_cast<std::vector<std::string>*>(data)->push_back(info->dlpi_name);
            return 0;
        },
        &objects);
    std::sort(objects.begin(), objects.end());
    for (const auto& object : objects)
        add("loaded_object:" + object, sha256_file(object));
    std::vector<std::string> environment;
    for (char** entry = environ; entry && *entry; ++entry) {
        const std::string value(*entry);
        const auto name = value.substr(0, value.find('='));
        if (name.rfind("OMP_", 0) == 0 || name.rfind("GOMP_", 0) == 0 ||
            name.rfind("KMP_", 0) == 0 || name.rfind("MKL_", 0) == 0 ||
            name.rfind("OZAMX_", 0) == 0 || name.rfind("LD_", 0) == 0 ||
            name.rfind("LC_", 0) == 0 || name == "LANG")
            environment.push_back(value);
    }
    std::sort(environment.begin(), environment.end());
    for (const auto& value : environment)
        add("environment", value);
    add("initial_affinity", initial_affinity);
    add("calling_thread_affinity", affinity_string());
    utsname host{};
    if (uname(&host) != 0)
        throw std::runtime_error("cannot fingerprint host");
    add("host", std::string(host.nodename) + '/' + host.release + '/' + host.machine);
#ifdef _OPENMP
    add("omp_max_threads", std::to_string(omp_get_max_threads()));
    add("omp_dynamic", std::to_string(omp_get_dynamic()));
    add("omp_proc_bind", std::to_string(omp_get_proc_bind()));
    add("omp_num_places", std::to_string(omp_get_num_places()));
#endif
    add("mkl_max_threads", std::to_string(mkl_get_max_threads()));
    add("mkl_dynamic", std::to_string(mkl_get_dynamic()));
    // Hex encodes the complete canonical record, with no hash collision or JSON
    // escaping ambiguity. This is an identity record, not a security credential.
    id.key = hex_string(description.str());
    return id;
}
std::string checkpoint_file(const Opts& o, const std::string& precision, std::size_t n,
                            ozamx::ProductBudget budget) {
    return o.checkpoint + "." + precision + "." + std::to_string(n) + "." +
           (precision == "fp32" ? "6" : budget_name(budget)) + ".json";
}
std::string json_string(const std::string& s, const std::string& key) {
    const auto p = s.find("\"" + key + "\":\"");
    if (p == std::string::npos)
        return {};
    const auto b = p + key.size() + 4, e = s.find('"', b);
    return e == std::string::npos ? std::string{} : s.substr(b, e - b);
}
std::size_t json_size(const std::string& s, const std::string& key) {
    const auto p = s.find("\"" + key + "\":");
    if (p == std::string::npos)
        throw std::runtime_error("checkpoint missing " + key);
    return static_cast<std::size_t>(std::stoull(s.substr(p + key.size() + 3)));
}
bool json_bool(const std::string& s, const std::string& key) {
    const auto p = s.find("\"" + key + "\":");
    return p != std::string::npos && s.compare(p + key.size() + 3, 4, "true") == 0;
}
std::vector<double> json_array(const std::string& s, const std::string& key) {
    const auto p = s.find("\"" + key + "\":[");
    if (p == std::string::npos)
        throw std::runtime_error("checkpoint missing " + key);
    const auto b = p + key.size() + 4, e = s.find(']', b);
    if (e == std::string::npos)
        throw std::runtime_error("invalid checkpoint array " + key);
    std::vector<double> v;
    std::stringstream ss(s.substr(b, e - b));
    std::string x;
    while (std::getline(ss, x, ','))
        if (!x.empty())
            v.push_back(std::stod(x));
    return v;
}
void load_checkpoint(const Opts& o, const std::string& precision, std::size_t n, std::uint64_t seed,
                     ozamx::ProductBudget budget, const RunIdentity& identity,
                     std::vector<double>& sp, std::vector<double>& pp, std::vector<double>& cp,
                     std::vector<double>& tp, std::vector<double>& wall,
                     std::vector<double>& mkl_samples) {
    if (!o.resume || o.checkpoint.empty())
        return;
    std::ifstream f(checkpoint_file(o, precision, n, budget));
    if (!f)
        return;
    std::ostringstream ss;
    ss << f.rdbuf();
    const auto s = ss.str();
    const auto expected_budget = precision == "fp32" ? 6 : static_cast<int>(budget);
    if (json_string(s, "source_id") != kCheckpointSourceId ||
        json_string(s, "timing_schema") != kTimingSchema ||
        json_string(s, "measurement_protocol") != kMeasurementProtocol ||
        json_string(s, "driver_source_sha256") != identity.source_sha256 ||
        json_string(s, "benchmark_executable_sha256") != identity.executable_sha256 ||
        json_string(s, "mkl_runtime_sha256") != identity.mkl_sha256 ||
        json_string(s, "run_identity") != identity.key ||
        json_string(s, "precision") != precision || json_string(s, "distribution") != o.dist ||
        json_size(s, "N") != n || json_size(s, "threads") != static_cast<std::size_t>(o.threads) ||
        json_size(s, "seed") != seed ||
        json_size(s, "budget") != static_cast<std::size_t>(expected_budget) ||
        json_size(s, "requested_repetitions") != static_cast<std::size_t>(o.reps))
        throw std::runtime_error("checkpoint schema, executable, libraries, environment, or "
                                 "parameters do not match; use a fresh checkpoint path");
    sp = json_array(s, "split_seconds");
    pp = json_array(s, "pack_seconds");
    cp = json_array(s, "compute_reconstruction_seconds");
    tp = json_array(s, "total_seconds");
    wall = json_array(s, "call_wall_seconds");
    mkl_samples = json_array(s, "mkl_gemm_seconds");
    if (sp.size() != tp.size() || pp.size() != tp.size() || cp.size() != tp.size() ||
        wall.size() != tp.size() || mkl_samples.size() != tp.size() ||
        tp.size() > static_cast<std::size_t>(o.reps) ||
        json_size(s, "completed_timed_repetitions") != tp.size() ||
        (json_bool(s, "complete") && tp.size() != static_cast<std::size_t>(o.reps)))
        throw std::runtime_error("checkpoint timing vector sizes are inconsistent");
    for (const auto* values : {&sp, &pp, &cp, &tp, &wall, &mkl_samples})
        for (double value : *values)
            if (!std::isfinite(value) || value < 0 ||
                ((values == &wall || values == &mkl_samples) && value == 0))
                throw std::runtime_error("checkpoint contains invalid timing samples");
}
void checkpoint(const Opts& o, const std::string& precision, std::size_t n, std::uint64_t seed,
                ozamx::ProductBudget budget, const RunIdentity& identity,
                const std::vector<double>& sp, const std::vector<double>& pp,
                const std::vector<double>& cp, const std::vector<double>& tp,
                const std::vector<double>& wall, const std::vector<double>& mkl_samples,
                bool complete) {
    if (o.checkpoint.empty())
        return;
    const auto path = checkpoint_file(o, precision, n, budget);
    std::ofstream f(path + ".tmp");
    if (!f)
        throw std::runtime_error("cannot write checkpoint");
    f.exceptions(std::ios::badbit | std::ios::failbit);
    auto arr = [&](const std::vector<double>& v) {
        f << '[';
        for (std::size_t i = 0; i < v.size(); ++i) {
            if (i)
                f << ',';
            f << std::setprecision(17) << v[i];
        }
        f << ']';
    };
    f << "{\"source_id\":\"" << kCheckpointSourceId << "\",\"timing_schema\":\"" << kTimingSchema
      << "\",\"measurement_protocol\":\"" << kMeasurementProtocol
      << "\",\"driver_source_sha256\":\"" << identity.source_sha256
      << "\",\"benchmark_executable_sha256\":\"" << identity.executable_sha256
      << "\",\"mkl_runtime_sha256\":\"" << identity.mkl_sha256
      << "\",\"run_identity\":\"" << identity.key << "\",\"precision\":\"" << precision
      << "\",\"distribution\":\"" << o.dist
      << "\",\"budget\":" << (precision == "fp32" ? 6 : static_cast<int>(budget)) << ",\"N\":" << n
      << ",\"threads\":" << o.threads << ",\"seed\":" << seed
      << ",\"requested_repetitions\":" << o.reps << ",\"completed_timed_repetitions\":" << tp.size()
      << ",\"complete\":" << (complete ? "true" : "false") << ",\"split_seconds\":";
    arr(sp);
    f << ",\"pack_seconds\":";
    arr(pp);
    f << ",\"compute_reconstruction_seconds\":";
    arr(cp);
    f << ",\"total_seconds\":";
    arr(tp);
    f << ",\"call_wall_seconds\":";
    arr(wall);
    f << ",\"mkl_gemm_seconds\":";
    arr(mkl_samples);
    f << "}\n";
    f.close();
    if (std::rename((path + ".tmp").c_str(), path.c_str()) != 0)
        throw std::runtime_error("cannot atomically replace checkpoint");
}
template <class T>
void run(std::ostream& out, const std::string& precision, std::size_t n, const Opts& o,
         std::uint64_t seed, ozamx::ProductBudget budget) {
    std::vector<T> a(n * n), b(n * n), c(n * n);
    fill(a, b, n, o, seed);
    MklResult<T> mr;
    mr.c.resize(n * n);
    mkl_set_dynamic(0);
    mkl_set_num_threads(o.threads);
    auto call = [&]() {
        if constexpr (std::is_same_v<T, float>)
            return ozamx::gemm_fp32_profiled(n, n, n, a.data(), n, b.data(), n, c.data(), n);
        else
            return ozamx::gemm_fp64_profiled(n, n, n, a.data(), n, b.data(), n, c.data(), n,
                                             budget);
    };
    // Both routines warm up once before identity collection and timed pairs.
    (void)call();
    mkl_gemm(a, b, n, mr.c);
    const auto identity = run_identity();
    std::vector<double> sp, pp, cp, tp, wall;
    load_checkpoint(o, precision, n, seed, budget, identity, sp, pp, cp, tp, wall, mr.samples);
    auto measure_api = [&]() {
        const auto start = std::chrono::steady_clock::now();
        auto t = call();
        const double elapsed =
            std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        sp.push_back(t.split_seconds);
        pp.push_back(t.pack_seconds);
        cp.push_back(t.compute_and_reconstruct_seconds);
        tp.push_back(t.total_seconds);
        wall.push_back(elapsed);
    };
    auto measure_mkl = [&]() {
        const auto start = std::chrono::steady_clock::now();
        mkl_gemm(a, b, n, mr.c);
        mr.samples.push_back(
            std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count());
    };
    for (std::size_t q = tp.size(); q < static_cast<std::size_t>(o.reps); ++q) {
        if (q % 2 == 0) {
            measure_api();
            measure_mkl();
        } else {
            measure_mkl();
            measure_api();
        }
        // Save only complete pairs. Checkpoint I/O never enters either timer.
        checkpoint(o, precision, n, seed, budget, identity, sp, pp, cp, tp, wall, mr.samples,
                   false);
    }
    auto mean = [](const std::vector<double>& v) {
        long double s = 0;
        for (double x : v)
            s += x;
        return (double)(s / v.size());
    };
    auto stddev = [&](const std::vector<double>& v) {
        const double m = mean(v);
        long double s = 0;
        for (double x : v) {
            const long double d = x - m;
            s += d * d;
        }
        return std::sqrt(static_cast<double>(s / v.size()));
    };
    mr.seconds = mean(mr.samples);
    const auto mm = compare_mkl(c, mr, a, b, n);
    std::string scope;
    const auto hp = high_precision(a, b, c, n, seed, scope);
    long double checksum = 0;
    for (T x : c)
        checksum += (long double)x;
    const long double gflops = 2.L * n * n * n / mean(wall) / 1.e9L,
                      profile_gflops = 2.L * n * n * n / mean(tp) / 1.e9L,
                      mklg = 2.L * n * n * n / mr.seconds / 1.e9L;
    out << precision << ',' << o.dist << ',' << (precision == "fp32" ? "6" : budget_name(budget))
        << ',' << n << ',' << o.threads << ',' << seed << ',' << o.reps << ','
        << std::setprecision(12) << mean(sp) << ',' << mean(pp) << ',' << mean(cp) << ','
        << mean(tp) << ',' << (double)gflops << ',' << mr.seconds << ',' << (double)mklg << ','
        << mr.seconds / mean(tp) << ',' << (double)mm.ef << ',' << (double)mm.scaled << ',' << scope
        << ',' << (double)hp.ef << ',' << (double)hp.scaled << ',' << (double)checksum << ',';
    const char* order =
        precision == "fp32" ? ozamx::product_order_fp32() : ozamx::product_order_fp64(budget);
    out << mean(wall) << ',' << stddev(wall) << ",\"" << raw(sp) << "\",\"" << raw(pp) << "\",\""
        << raw(cp) << "\",\"" << raw(tp) << "\",\"" << raw(wall) << "\",\"" << order
        << "\",\"effective_GFLOP_s uses full API wall; profile_speedup remains MKL/profile; "
           "api_speedup is MKL/full API; pairs alternate API-first-even; MKL encloses GEMM only\",\""
        << mkl_version() << "\",\"" << mkl_runtime_path() << "\",\"" << mkl_threading_layer()
        << "\",ok," << (double)profile_gflops << ',' << mr.seconds / mean(wall) << ",\""
        << raw(mr.samples) << "\"," << kTimingSchema << ',' << kMeasurementProtocol << ','
        << identity.source_sha256 << ',' << identity.executable_sha256 << ',' << identity.mkl_sha256
        << ',' << identity.key << '\n';
    out.flush();
    checkpoint(o, precision, n, seed, budget, identity, sp, pp, cp, tp, wall, mr.samples, true);
}
} // namespace
int main(int argc, char** argv) try {
    const auto o = parse(argc, argv);
    initial_affinity = affinity_string();
#ifdef _OPENMP
    omp_set_dynamic(0);
    omp_set_num_threads(o.threads);
#endif
    if (!ozamx::request_amx_permission_for_current_thread().permission_available) {
        std::cerr << "AMX unavailable\n";
        return 2;
    }
    std::ofstream file;
    std::ostream* out = &std::cout;
    if (o.output != "-") {
        file.open(o.output);
        if (!file)
            throw std::runtime_error("cannot open output");
        out = &file;
    }
    out->exceptions(std::ios::badbit | std::ios::failbit);
    *out << "precision,distribution,budget,N,threads,seed,repetitions,split_s_mean,pack_s_mean,"
            "compute_recon_s_mean,profile_total_s_mean,effective_GFLOP_s,mkl_gemm_s,mkl_effective_"
            "GFLOP_s,profile_speedup,eF_mkl,e_scaled_mkl,hp_scope,eF_hp,e_scaled_hp,checksum,api_"
            "call_wall_s_mean,api_call_wall_s_std,raw_split_s,raw_pack_s,raw_compute_recon_s,raw_"
            "profile_total_s,raw_api_call_wall_s,product_order,timing_scope,mkl_version,mkl_"
            "runtime_path,mkl_threading_layer,status,profile_effective_GFLOP_s,api_speedup,"
            "raw_mkl_gemm_s,timing_schema,measurement_protocol,driver_source_sha256,"
            "benchmark_executable_sha256,mkl_runtime_sha256,run_identity\n";
    for (auto n : o.sizes) {
        if (!n)
            throw std::runtime_error("N must be positive");
        const auto seed = o.seed + n;
        if (o.precision == "all" || o.precision == "fp32")
            run<float>(*out, "fp32", n, o, seed, ozamx::ProductBudget::p6);
        if (o.precision == "all" || o.precision == "fp64")
            for (int budget : o.budgets)
                run<double>(*out, "fp64", n, o, seed, static_cast<ozamx::ProductBudget>(budget));
    }
    return 0;
} catch (const std::exception& e) {
    std::cerr << "benchmark error: " << e.what() << '\n';
    return 2;
}
