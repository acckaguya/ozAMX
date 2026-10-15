#include "ozamx/gemm.hpp"

#include <chrono>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sched.h>
#include <type_traits>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif

namespace {
template<class T> struct State {
    std::size_t n = 0;
    std::vector<T> a, b, c;
    std::uint64_t a_hash=1469598103934665603ULL, b_hash=1469598103934665603ULL;
};
State<float> f32;
State<double> f64;

template<class T> void prepare(State<T>& s, std::size_t n) {
    if (s.n == n) return;
    s.n=n; s.a.resize(n*n); s.b.resize(n*n); s.c.resize(n*n);
    std::mt19937_64 rng(260904ULL+n);
    std::uniform_real_distribution<T> dist(T(-1),T(1));
    for(auto& x:s.a)x=dist(rng);
    for(auto& x:s.b)x=dist(rng);
    std::fill(s.c.begin(),s.c.end(),T(0));
    auto hash=[](const std::vector<T>& v) {
        std::uint64_t h=1469598103934665603ULL;
        const auto* p=reinterpret_cast<const unsigned char*>(v.data());
        for(std::size_t i=0;i<v.size()*sizeof(T);++i){h^=p[i];h*=1099511628211ULL;}
        return h;
    };
    s.a_hash=hash(s.a);s.b_hash=hash(s.b);
}
template<class T> int call(State<T>& s, int budget) {
    ozamx::GemmTimings t;
    const auto start=std::chrono::steady_clock::now();
    if constexpr(std::is_same_v<T,float>)
        t=ozamx::gemm_fp32_profiled(s.n,s.n,s.n,s.a.data(),s.n,s.b.data(),s.n,s.c.data(),s.n);
    else
        t=ozamx::gemm_fp64_profiled(s.n,s.n,s.n,s.a.data(),s.n,s.b.data(),s.n,s.c.data(),s.n,static_cast<ozamx::ProductBudget>(budget));
    const double wall=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    std::cout<<std::setprecision(17)<<"{\"status\":\"ok\",\"api_wall_seconds\":"<<wall
             <<",\"split_seconds\":"<<t.split_seconds<<",\"pack_seconds\":"<<t.pack_seconds
             <<",\"compute_reconstruct_seconds\":"<<t.compute_and_reconstruct_seconds
             <<",\"profile_total_seconds\":"<<t.total_seconds
             <<",\"input_a_fnv1a64\":"<<s.a_hash<<",\"input_b_fnv1a64\":"<<s.b_hash<<"}"<<std::endl;
    return 0;
}
template<class T> void dump(const State<T>& s, std::size_t requested_n, const std::string& path) {
    if(!requested_n||s.n!=requested_n)throw std::runtime_error("dump size does not match active configuration");
    std::ofstream out(path,std::ios::binary|std::ios::trunc);
    if(!out) throw std::runtime_error("cannot open dump path");
    out.write(reinterpret_cast<const char*>(s.c.data()),static_cast<std::streamsize>(s.c.size()*sizeof(T)));
    if(!out)throw std::runtime_error("output dump failed");
    std::cout<<"{\"status\":\"dumped\",\"N\":"<<s.n<<",\"bytes\":"<<(s.c.size()*sizeof(T))<<"}"<<std::endl;
}
}
int main() try {
    cpu_set_t inherited_affinity;CPU_ZERO(&inherited_affinity);sched_getaffinity(0,sizeof(inherited_affinity),&inherited_affinity);
#ifdef _OPENMP
    omp_set_dynamic(0); omp_set_num_threads(64);
#endif
    std::vector<int> team_cpus(64,-1);
    int actual_team_size=1;
#ifdef _OPENMP
#pragma omp parallel
    {
#pragma omp single
        actual_team_size=omp_get_num_threads();
        const int tid=omp_get_thread_num();
        if(tid>=0&&static_cast<std::size_t>(tid)<team_cpus.size())team_cpus[static_cast<std::size_t>(tid)]=sched_getcpu();
    }
#else
    team_cpus[0]=sched_getcpu();
#endif
    const auto amx=ozamx::request_amx_permission_for_current_thread();
    cpu_set_t affinity;CPU_ZERO(&affinity);sched_getaffinity(0,sizeof(affinity),&affinity);
    std::cout<<"{\"event\":\"ready\",\"amx_permission\":"<<(amx.permission_available?"true":"false")
#ifdef _OPENMP
             <<",\"requested_omp_threads\":64,\"max_omp_threads\":"<<omp_get_max_threads()
#else
             <<",\"requested_omp_threads\":64,\"max_omp_threads\":1
#endif
             <<",\"actual_omp_threads\":"<<actual_team_size
             <<",\"calling_cpu\":"<<sched_getcpu()<<",\"calling_thread_affinity_cpus\":[";
    bool first_cpu=true;for(int cpu=0;cpu<CPU_SETSIZE;++cpu)if(CPU_ISSET(cpu,&affinity)){if(!first_cpu)std::cout<<',';std::cout<<cpu;first_cpu=false;}
    std::cout<<"],\"inherited_affinity_cpus\":[";first_cpu=true;
    for(int cpu=0;cpu<CPU_SETSIZE;++cpu)if(CPU_ISSET(cpu,&inherited_affinity)){if(!first_cpu)std::cout<<',';std::cout<<cpu;first_cpu=false;}
    std::cout<<"],\"omp_thread_cpus\":[";
    for(std::size_t i=0;i<team_cpus.size();++i){if(i)std::cout<<',';std::cout<<team_cpus[i];}
    std::cout<<"]}"<<std::endl;
    std::string line;
    while(std::getline(std::cin,line)) {
        try {
            if(line=="quit"){std::cout<<"{\"status\":\"bye\"}"<<std::endl;return 0;}
            std::istringstream in(line);std::string op,precision;std::size_t n;int budget=6;
            in>>op>>precision>>n;
            if(op=="dump") {std::string path;in>>path;if(!in)throw std::runtime_error("malformed dump command");if(precision=="fp32")dump(f32,n,path);else if(precision=="fp64")dump(f64,n,path);else throw std::runtime_error("bad precision");continue;}
            if(op!="warm"&&op!="run")throw std::runtime_error("unknown operation");
            if(precision=="fp64")in>>budget;
            if(!in||n==0)throw std::runtime_error("malformed command");
            if(precision=="fp32"){prepare(f32,n);call(f32,6);}
            else if(precision=="fp64"){prepare(f64,n);call(f64,budget);}
            else throw std::runtime_error("bad precision");
        } catch(const std::exception& e) {
            std::cerr<<"child command error: "<<e.what()<<'\n';
            std::cout<<"{\"status\":\"error\",\"message\":\"child command failed; see stderr log\"}"<<std::endl;
        }
    }
    return 0;
} catch(const std::exception& e) { std::cerr<<"driver fatal: "<<e.what()<<'\n';return 2; }
