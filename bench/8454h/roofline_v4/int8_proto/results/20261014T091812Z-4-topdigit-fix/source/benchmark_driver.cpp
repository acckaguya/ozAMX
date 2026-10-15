#include "int8.hpp"
#include "ozamx/gemm.hpp"
#include <mkl.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;
struct Options { std::size_t n=0; int threads=64, reps=5; std::uint64_t seed=260904; std::string output; };
Options parse(int argc, char** argv) {
    Options o;
    for (int i=1;i<argc;++i) {
        const std::string k=argv[i];
        if (k=="--help") { std::cout<<"--n N --threads T --reps R --seed S --output FILE\n"; std::exit(0); }
        if (i+1>=argc) throw std::runtime_error("missing value for "+k);
        const std::string v=argv[++i];
        if(k=="--n") o.n=std::stoull(v); else if(k=="--threads") o.threads=std::stoi(v);
        else if(k=="--reps") o.reps=std::stoi(v); else if(k=="--seed") o.seed=std::stoull(v);
        else if(k=="--output") o.output=v; else throw std::runtime_error("unknown option: "+k);
    }
    if(!o.n || o.n%32 || o.n>static_cast<std::size_t>(std::numeric_limits<MKL_INT>::max()))
        throw std::runtime_error("N must be a positive multiple of 32 and fit MKL_INT");
    if(o.threads<1 || o.reps<1 || o.output.empty()) throw std::runtime_error("threads, reps, and output are required");
    return o;
}
struct Sample { double wall=0, phase1=0, phase2=0, phase3=0, profile=0; };
struct Metrics { double ef=0, scaled=0, max_abs=0; };
double seconds(Clock::time_point start) { return std::chrono::duration<double>(Clock::now()-start).count(); }
std::vector<double> median_copy(const std::vector<Sample>& v) {
    std::vector<double> x; x.reserve(v.size()); for(const auto&s:v)x.push_back(s.wall);
    std::sort(x.begin(),x.end()); return x;
}
double median(const std::vector<Sample>& v) { const auto x=median_copy(v); return x.size()%2?x[x.size()/2]:(x[x.size()/2-1]+x[x.size()/2])/2; }
std::pair<double,double> mean_sd(const std::vector<Sample>& v) {
    long double sum=0; for(const auto&s:v)sum+=s.wall;
    const long double mean=sum/v.size(); long double sq=0;
    for(const auto&s:v){const long double d=s.wall-mean;sq+=d*d;}
    return {static_cast<double>(mean),static_cast<double>(std::sqrt(sq/v.size()))};
}
std::vector<double> raw(const std::vector<Sample>& v, int field) {
    std::vector<double>x; x.reserve(v.size()); for(const auto&s:v) x.push_back(field==0?s.wall:field==1?s.phase1:field==2?s.phase2:field==3?s.phase3:s.profile); return x;
}
void array(std::ostream& o,const std::vector<double>& v) { o<<'['; for(std::size_t i=0;i<v.size();++i){if(i)o<<',';o<<std::setprecision(17)<<v[i];}o<<']'; }
Metrics compare_full(const std::vector<double>& got,const std::vector<double>& ref,const std::vector<double>& denom) {
    long double e2=0,r2=0; double scaled=0,max_abs=0;
    for(std::size_t i=0;i<got.size();++i) {
        const long double d=static_cast<long double>(got[i])-ref[i];
        e2+=d*d; r2+=static_cast<long double>(ref[i])*ref[i];
        max_abs=std::max(max_abs,std::abs(static_cast<double>(d)));
        const double abs_error=std::abs(static_cast<double>(d));
        const double element_scale=denom[i]==0?abs_error:abs_error/denom[i];
        scaled=std::max(scaled,element_scale);
    }
    return {static_cast<double>(r2==0?std::sqrt(e2):std::sqrt(e2/r2)),scaled,max_abs};
}
void atomic_checkpoint(const Options& o,const std::vector<Sample>& i8,const std::vector<Sample>& v3,
                       const std::vector<Sample>& mkl,const std::vector<std::string>& order,
                       bool complete,const std::string& status,const Metrics* mi=nullptr,const Metrics* mv=nullptr) {
    const std::string tmp=o.output+".tmp";
    std::ofstream f(tmp,std::ios::trunc); if(!f)throw std::runtime_error("cannot write checkpoint: "+tmp);
    auto method=[&](const char* key,const std::vector<Sample>& s){
        f<<"\""<<key<<"\":{\"api_wall_raw_s\":";array(f,raw(s,0));
        f<<",\"phase1_raw_s\":";array(f,raw(s,1)); f<<",\"phase2_raw_s\":";array(f,raw(s,2));
        f<<",\"phase3_raw_s\":";array(f,raw(s,3)); f<<",\"profile_total_raw_s\":";array(f,raw(s,4));
        const auto ms=mean_sd(s);
        f<<",\"api_wall_median_s\":"<<std::setprecision(17)<<median(s)
         <<",\"api_wall_mean_s\":"<<ms.first<<",\"api_wall_population_sd_s\":"<<ms.second<<'}';
    };
    f<<"{\"schema\":\"ozamx-roofline-v4-int8-match-v1\",\"source_id\":\"int8-36-vs-v3-p21-vs-mkl\",\"N\":"<<o.n
     <<",\"threads\":"<<o.threads<<",\"requested_repetitions\":"<<o.reps<<",\"seed\":"<<o.seed
     <<",\"products\":{\"int8\":36,\"v3\":21},\"timing_scope\":\"API wall includes complete ozAMX call and teardown; MKL wall is dgemm call only; profile phases are auxiliary and profile total is not used as API performance\""
     <<",\"alternating_order\":[";
    for(std::size_t j=0;j<order.size();++j){if(j)f<<',';f<<'"'<<order[j]<<'"';}
    f<<"],\"completed_repetitions\":"<<i8.size()<<",\"complete\":"<<(complete?"true":"false")<<",\"status\":\""<<status<<"\",\"samples\":{";
    method("int8_36",i8);f<<',';method("v3_p21",v3);f<<',';method("mkl_dgemm",mkl);f<<'}';
    if(mi&&mv) f<<",\"full_N_vs_mkl\":{\"reference_scope\":\"oneMKL DGEMM; full matrix\",\"denominator\":\"oneMKL DGEMM(abs(A),abs(B))\",\"int8_36\":{\"eF\":"<<std::setprecision(17)<<mi->ef<<",\"e_scaled\":"<<mi->scaled<<",\"max_abs\":"<<mi->max_abs
       <<"},\"v3_p21\":{\"eF\":"<<mv->ef<<",\"e_scaled\":"<<mv->scaled<<",\"max_abs\":"<<mv->max_abs<<"},\"products_differ\":true}";
    f<<"}\n"; f.close();
    if(std::rename(tmp.c_str(),o.output.c_str()))throw std::runtime_error("cannot atomically commit checkpoint");
}
}
int main(int argc,char**argv) try {
    const auto o=parse(argc,argv); const std::size_t count=o.n*o.n;
    if(count/o.n!=o.n)throw std::overflow_error("matrix element count overflow");
    std::vector<double>a(count),b(count),abs_a(count),abs_b(count),ci8(count),cv3(count),cmkl(count),denom(count);
    std::mt19937_64 rng(o.seed); std::uniform_real_distribution<double> uniform(-1.0,1.0);
    for(std::size_t q=0;q<count;++q){a[q]=uniform(rng);b[q]=uniform(rng);abs_a[q]=std::abs(a[q]);abs_b[q]=std::abs(b[q]);}
    mkl_set_dynamic(0); mkl_set_num_threads(o.threads);
    const auto n=static_cast<MKL_INT>(o.n);
    auto call_i8=[&](){return ozamx_int8_36::gemm_fp64_int8_36_profiled(o.n,o.n,o.n,a.data(),o.n,b.data(),o.n,ci8.data(),o.n,o.threads);};
    auto call_v3=[&](){return ozamx::gemm_fp64_profiled(o.n,o.n,o.n,a.data(),o.n,b.data(),o.n,cv3.data(),o.n,ozamx::ProductBudget::p21);};
    auto call_mkl=[&](){cblas_dgemm(CblasRowMajor,CblasNoTrans,CblasNoTrans,n,n,n,1.0,a.data(),n,b.data(),n,0.0,cmkl.data(),n);};
    if(!ozamx::request_amx_permission_for_current_thread().permission_available)throw std::runtime_error("AMX permission unavailable");
    call_i8(); call_v3(); call_mkl(); // one untimed warm-up per implementation
    std::vector<Sample> i8,v3,mkl; std::vector<std::string> order;
    i8.reserve(o.reps);v3.reserve(o.reps);mkl.reserve(o.reps);order.reserve(o.reps);
    for(int rep=0;rep<o.reps;++rep) {
        const bool reverse=(rep&1)!=0;
        order.push_back(reverse?"int8_36,v3_p21,mkl_dgemm":"v3_p21,int8_36,mkl_dgemm");
        auto runi=[&](){const auto t=Clock::now();const auto p=call_i8();return Sample{seconds(t),p.scan_seconds,p.pack_seconds,p.compute_reconstruct_seconds,p.total_seconds};};
        auto runv=[&](){const auto t=Clock::now();const auto p=call_v3();return Sample{seconds(t),p.split_seconds,p.pack_seconds,p.compute_and_reconstruct_seconds,p.total_seconds};};
        auto runm=[&](){const auto t=Clock::now();call_mkl();return Sample{seconds(t),0,0,0,0};};
        if(reverse){i8.push_back(runi());v3.push_back(runv());}else{v3.push_back(runv());i8.push_back(runi());}
        mkl.push_back(runm());
        atomic_checkpoint(o,i8,v3,mkl,order,false,"timed_samples_complete_metrics_pending");
    }
    // Full-N numerical comparison is deliberately outside all timed regions.
    cblas_dgemm(CblasRowMajor,CblasNoTrans,CblasNoTrans,n,n,n,1.0,abs_a.data(),n,abs_b.data(),n,0.0,denom.data(),n);
    const auto mi=compare_full(ci8,cmkl,denom),mv=compare_full(cv3,cmkl,denom);
    atomic_checkpoint(o,i8,v3,mkl,order,true,"complete",&mi,&mv);
    return 0;
} catch(const std::exception& e) { std::cerr<<"benchmark_driver: "<<e.what()<<'\n'; return 2; }
