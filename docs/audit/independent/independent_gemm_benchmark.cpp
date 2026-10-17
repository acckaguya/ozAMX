// Audit attachment only. Does not include any existing benchmark/test implementation.
#include "ozamx/gemm.hpp"
#include <mkl.h>
#include <omp.h>
#include <sys/random.h>
#include <sys/resource.h>
#include <time.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

using Steady = std::chrono::steady_clock;
constexpr std::int64_t prime = 2147483647;
std::uint64_t splitmix(std::uint64_t& state) {
    std::uint64_t z = (state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}
std::uint16_t bf16(float x) {
    std::uint32_t u; std::memcpy(&u, &x, 4);
    u += 0x7fffU + ((u >> 16) & 1U);
    return static_cast<std::uint16_t>(u >> 16);
}
float decode(std::uint16_t h) {
    const std::uint32_t u = std::uint32_t(h) << 16;
    float x; std::memcpy(&x, &u, 4); return x;
}
std::uint64_t hash_bytes(const void* pointer, std::size_t bytes) {
    const auto* p = static_cast<const unsigned char*>(pointer);
    std::uint64_t h = 14695981039346656037ULL;
    for (std::size_t i=0;i<bytes;++i) {h ^= p[i]; h *= 1099511628211ULL;}
    return h;
}
double raw_seconds() {
    timespec t{};
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &t)) throw std::runtime_error("raw clock failed");
    return double(t.tv_sec) + double(t.tv_nsec)*1e-9;
}
double cpu_seconds() {
    rusage r{};
    if (getrusage(RUSAGE_SELF, &r)) throw std::runtime_error("getrusage failed");
    return double(r.ru_utime.tv_sec+r.ru_stime.tv_sec) +
           double(r.ru_utime.tv_usec+r.ru_stime.tv_usec)*1e-6;
}
std::int64_t mod(std::int64_t x) {x %= prime; return x < 0 ? x + prime : x;}
void entropy(void* target, std::size_t bytes) {
    auto* p = static_cast<unsigned char*>(target);
    while (bytes) {
        const auto got = getrandom(p, bytes, 0);
        if (got < 0 && errno == EINTR) continue;
        if (got <= 0) throw std::runtime_error("getrandom failed");
        p += got; bytes -= std::size_t(got);
    }
}
struct Matrices {
    std::size_t n;
    bool dyadic;
    std::vector<float> a,b,c;
    std::vector<std::uint16_t> ah,bh;
    std::vector<std::int8_t> ai,bi;
    std::uint64_t rng;
    Matrices(std::size_t dim, bool exact):n(dim),dyadic(exact),a(n*n),b(n*n),c(n*n),
        ah(n*n),bh(n*n),ai(exact?n*n:0),bi(exact?n*n:0),rng(0xa260a015ULL+dim+exact) {
        for(std::size_t q=0;q<n*n;++q) {
            if(dyadic) {
                ai[q]=std::int8_t(int(splitmix(rng)%17)-8);
                bi[q]=std::int8_t(int(splitmix(rng)%17)-8);
                a[q]=float(ai[q])/16.0f; b[q]=float(bi[q])/16.0f;
            } else {
                a[q]=float(std::int32_t(splitmix(rng)>>40)-8388608)/8388608.0f;
                b[q]=float(std::int32_t(splitmix(rng)>>40)-8388608)/8388608.0f;
            }
            ah[q]=bf16(a[q]); bh[q]=bf16(b[q]);
        }
    }
    void mutate(int round) {
        const std::size_t q=(std::size_t(round+2)*2654435761ULL)%(n*n);
        if(dyadic) {ai[q]= ai[q]==8 ? -8 : std::int8_t(ai[q]+1); a[q]=float(ai[q])/16.0f;}
        else {
            // Change every output row's dot inputs, so fixed sampled rows also
            // exercise new input. This remains sampled validation, not full C.
            const std::size_t column=std::size_t(round+2)%n;
            for(std::size_t i=0;i<n;++i) {
                const auto index=i*n+column;
                a[index]=a[index]>=0 ? a[index]-0.25f : a[index]+0.25f;
                ah[index]=bf16(a[index]);
            }
        }
        if(dyadic) ah[q]=bf16(a[q]);
    }
};
struct Check {std::uint64_t mismatches=0, nonfinite=0, hash=0; double scaled=0,maxabs=0; std::size_t oracle_entries=0; int challenges=0; std::uint64_t challenge_bytes_offset=0;};
Check validate(Matrices& s, int routine, std::ofstream& challenge_file) {
    Check ck; const auto n=s.n;
    ck.hash=hash_bytes(s.c.data(),s.c.size()*sizeof(float));
    for(float x:s.c) if(!std::isfinite(x)) ++ck.nonfinite;
    if(ck.nonfinite) {ck.mismatches=ck.nonfinite; return ck;}
    if(s.dyadic) {
        std::vector<std::int32_t> ci(n*n);
        for(std::size_t q=0;q<n*n;++q) {
            const double x=std::ldexp(double(s.c[q]),8);
            // Check exact lattice and bound before conversion; do not round away errors.
            if(std::trunc(x)!=x || std::abs(x)>double(64*n)) ++ck.mismatches;
            else ci[q]=std::int32_t(x);
        }
        if(ck.mismatches) return ck;
        if(n<=128) {
            for(std::size_t i=0;i<n;++i) for(std::size_t j=0;j<n;++j) {
                std::int64_t want=0;
                for(std::size_t k=0;k<n;++k) want+=std::int64_t(s.ai[i*n+k])*std::int64_t(s.bi[k*n+j]);
                if(want!=ci[i*n+j]) ++ck.mismatches;
                ++ck.oracle_entries;
            }
        }
        // Exact Freivalds over F_p. Challenges are drawn after the completed output.
        // n<=4096: each |C_integer|<=64n; sum |C_integer*r|<64*n*n*p<2^62.
        ck.challenge_bytes_offset=static_cast<std::uint64_t>(challenge_file.tellp());
        for(int challenge=0;challenge<3;++challenge) {
            std::vector<std::uint32_t> rv(n);
            for(auto& x:rv) {do {entropy(&x,sizeof(x));} while(std::uint64_t(x)>=2ULL*prime); x%=prime;}
            challenge_file.write(reinterpret_cast<const char*>(rv.data()),std::streamsize(rv.size()*4));
            std::vector<std::int64_t> br(n);
            for(std::size_t k=0;k<n;++k) {
                std::int64_t v=0;
                for(std::size_t j=0;j<n;++j) v+=std::int64_t(s.bi[k*n+j])*std::int64_t(rv[j]);
                br[k]=mod(v);
            }
            for(std::size_t i=0;i<n;++i) {
                std::int64_t left=0,right=0;
                for(std::size_t j=0;j<n;++j) left+=std::int64_t(ci[i*n+j])*std::int64_t(rv[j]);
                for(std::size_t k=0;k<n;++k) right+=std::int64_t(s.ai[i*n+k])*br[k];
                if(mod(left)!=mod(right)) ++ck.mismatches;
            }
            ++ck.challenges;
        }
    } else {
        // Independent long-double dots: all entries for N128, 512 selected entries otherwise.
        const std::size_t count=n<=128?n*n:512;
        std::uint64_t pick=0x6a09e667f3bcc909ULL+n;
        for(std::size_t q=0;q<count;++q) {
            const auto index=n<=128?q:std::size_t(splitmix(pick)%(n*n));
            const auto i=index/n,j=index%n;
            long double sum=0,bound=0;
            for(std::size_t k=0;k<n;++k) {
                const long double x=routine==2?decode(s.ah[i*n+k]):s.a[i*n+k];
                const long double y=routine==2?decode(s.bh[k*n+j]):s.b[k*n+j];
                sum+=x*y; bound+=std::abs(x*y);
            }
            const long double error=std::abs(static_cast<long double>(s.c[index])-sum);
            ck.maxabs=std::max(ck.maxabs,double(error));
            ck.scaled=std::max(ck.scaled,double(bound?error/bound:error));
            if((bound?error/bound:error)>5e-6L) ++ck.mismatches;
            ++ck.oracle_entries;
        }
    }
    return ck;
}
int main(int argc,char** argv) try {
    const std::string prefix=argc>1?argv[1]:"independent";
    const int reps=argc>2?std::stoi(argv[2]):10;
    if(reps<=0) throw std::runtime_error("positive reps required");
    if(mkl_set_threading_layer(MKL_THREADING_GNU)!=MKL_THREADING_GNU) throw std::runtime_error("GNU MKL required");
    mkl_set_dynamic(0);mkl_set_num_threads(64);omp_set_dynamic(0);omp_set_num_threads(64);
    if(!ozamx::request_amx_permission_for_current_thread().permission_available) throw std::runtime_error("AMX unavailable");
    std::ofstream output(prefix+".csv"), challenges(prefix+".challenges.u32",std::ios::binary),
        negatives(prefix+".negative_controls.jsonl");
    if(!output||!challenges||!negatives) throw std::runtime_error("output files unavailable");
    output.exceptions(std::ios::badbit|std::ios::failbit);
    challenges.exceptions(std::ios::badbit|std::ios::failbit);
    negatives.exceptions(std::ios::badbit|std::ios::failbit);
    output<<"family,N,round,warmup,position,routine,raw_wall_s,steady_wall_s,cpu_s,output_hash,input_a_hash,input_b_hash,input_unchanged,nonfinite,mismatches,oracle_entries,scaled_error,max_abs_error,field_challenges,challenge_offset\n";
    const std::array<const char*,3> names{{"ozamx_fp32","mkl_sgemm","mkl_bf16"}};
    int actual=0;
#pragma omp parallel
    {
#pragma omp single
        actual=omp_get_num_threads();
    }
    std::cout<<"actual_ready_team="<<actual<<" long_double_digits="<<std::numeric_limits<long double>::digits<<'\n';
    bool all_ok=true;
    for(bool exact:{true,false}) for(std::size_t n:{128U,1024U,4096U}) {
        Matrices s(n,exact);
        for(int round=-1;round<reps;++round) {
            s.mutate(round);
            std::array<int,3> order{{0,1,2}};
            std::uint64_t ordering=0x12345678ULL+n+std::uint64_t(round+1)*31+exact;
            for(int i=2;i>0;--i) std::swap(order[i],order[splitmix(ordering)%std::uint64_t(i+1)]);
            for(int position=0;position<3;++position) {
                const int routine=order[position];
                const auto a_hash=routine==2?hash_bytes(s.ah.data(),s.ah.size()*2):hash_bytes(s.a.data(),s.a.size()*4);
                const auto b_hash=routine==2?hash_bytes(s.bh.data(),s.bh.size()*2):hash_bytes(s.b.data(),s.b.size()*4);
                std::fill(s.c.begin(),s.c.end(),std::numeric_limits<float>::quiet_NaN());
                const auto cpu0=cpu_seconds(); const auto raw0=raw_seconds(); const auto steady0=Steady::now();
                if(routine==0) ozamx::gemm_fp32(n,n,n,s.a.data(),n,s.b.data(),n,s.c.data(),n);
                else if(routine==1) cblas_sgemm(CblasRowMajor,CblasNoTrans,CblasNoTrans,MKL_INT(n),MKL_INT(n),MKL_INT(n),1.0f,s.a.data(),MKL_INT(n),s.b.data(),MKL_INT(n),0.0f,s.c.data(),MKL_INT(n));
                else cblas_gemm_bf16bf16f32(CblasRowMajor,CblasNoTrans,CblasNoTrans,MKL_INT(n),MKL_INT(n),MKL_INT(n),1.0f,s.ah.data(),MKL_INT(n),s.bh.data(),MKL_INT(n),0.0f,s.c.data(),MKL_INT(n));
                const auto steady1=Steady::now(); const auto raw1=raw_seconds(); const auto cpu1=cpu_seconds();
                const double wall=raw1-raw0,swall=std::chrono::duration<double>(steady1-steady0).count();
                // Verify the actual inputs after the call, outside both timers,
                // before using them in the independently computed oracle.
                const auto a_after=routine==2?hash_bytes(s.ah.data(),s.ah.size()*2):hash_bytes(s.a.data(),s.a.size()*4);
                const auto b_after=routine==2?hash_bytes(s.bh.data(),s.bh.size()*2):hash_bytes(s.b.data(),s.b.size()*4);
                const bool inputs_unchanged=a_hash==a_after && b_hash==b_after;
                const auto ck=validate(s,routine,challenges);
                all_ok &= inputs_unchanged && ck.mismatches==0 && ck.nonfinite==0 && wall>0 && swall>0;
                output<<(exact?"dyadic_exact":"uniform_fp32")<<','<<n<<','<<round<<','<<(round<0)<<','<<position<<','<<names[routine]<<','<<std::setprecision(17)<<wall<<','<<swall<<','<<(cpu1-cpu0)<<','<<ck.hash<<','<<a_hash<<','<<b_hash<<','<<inputs_unchanged<<','<<ck.nonfinite<<','<<ck.mismatches<<','<<ck.oracle_entries<<','<<ck.scaled<<','<<ck.maxabs<<','<<ck.challenges<<','<<ck.challenge_bytes_offset<<'\n';
                output.flush();
                if(!inputs_unchanged) std::cerr<<"INPUT MODIFIED N="<<n<<" round="<<round<<" routine="<<names[routine]<<'\n';
                if(ck.mismatches || ck.nonfinite) std::cerr<<"VALIDATION FAILURE family="<<exact<<" N="<<n<<" round="<<round<<" routine="<<names[routine]<<" mismatches="<<ck.mismatches<<'\n';
                // Deliberate wrong-output controls are outside all timed calls.
                // N1024 uses the field test, without the small full-dot oracle.
                if(exact && n==1024 && round==-1 && routine==0) {
                    const auto original=s.c;
                    for(const char* fault:{"one_entry_corrupt","all_zero_output"}) {
                        s.c=original;
                        if(std::string(fault)=="one_entry_corrupt") s.c[0]+=1.0f/256.0f;
                        else std::fill(s.c.begin(),s.c.end(),0.0f);
                        const auto negative=validate(s,routine,challenges);
                        all_ok &= negative.mismatches>0;
                        negatives<<"{\"fault\":\""<<fault<<"\",\"N\":"<<n
                            <<",\"mismatches\":"<<negative.mismatches
                            <<",\"field_challenges\":"<<negative.challenges
                            <<",\"oracle_entries\":"<<negative.oracle_entries
                            <<",\"challenge_offset\":"<<negative.challenge_bytes_offset<<"}\n";
                        negatives.flush();
                    }
                    s.c=original;
                }
            }
        }
        std::cout<<"completed family="<<(exact?"dyadic_exact":"uniform_fp32")<<" N="<<n<<std::endl;
    }
    challenges.flush(); output.flush(); negatives.flush();
    std::cout<<"validation="<<(all_ok?"pass":"FAIL")<<std::endl;
    return all_ok?0:1;
} catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 2;}
