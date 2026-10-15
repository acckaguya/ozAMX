#include <mkl.h>
#include <dlfcn.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr const char* kSourceId="v3-paper-alignment-20261014";
using Clock = std::chrono::steady_clock;
struct Options {
    std::vector<std::size_t> sizes{256,512,1024,2048,4096,8192,16384,32768};
    int threads=64, reps=10;
    bool resume=false;
    std::uint64_t seed=260904;
    std::string output="-", checkpoint="";
};
std::vector<std::size_t> parse_sizes(const std::string& text) {
    std::vector<std::size_t> result;
    std::stringstream ss(text); std::string token;
    while (std::getline(ss, token, ',')) result.push_back(std::stoull(token));
    if (result.empty()) throw std::runtime_error("--sizes cannot be empty");
    return result;
}
Options parse(int argc, char** argv) {
    Options o;
    for (int i=1;i<argc;++i) {
        const std::string key=argv[i];
        if (key=="--resume") { o.resume=true; continue; }
        if (key=="--help") {
            std::cout << "usage: raw_bf16 [--sizes 256,512,...] [--threads 64] [--reps 10] [--seed N] [--output FILE] [--checkpoint FILE] [--resume]\n";
            std::exit(0);
        }
        if (i+1>=argc) throw std::runtime_error("missing value for "+key);
        const std::string value=argv[++i];
        if (key=="--sizes") o.sizes=parse_sizes(value);
        else if (key=="--threads") o.threads=std::stoi(value);
        else if (key=="--reps") o.reps=std::stoi(value);
        else if (key=="--seed") o.seed=std::stoull(value);
        else if (key=="--output") o.output=value;
        else if (key=="--checkpoint") o.checkpoint=value;
        else throw std::runtime_error("unknown option: "+key);
    }
    if(o.threads<1||o.reps<1)throw std::runtime_error("threads and reps must be positive");
    return o;
}
std::uint16_t float_to_bf16_rne(float x) {
    std::uint32_t bits; std::memcpy(&bits,&x,sizeof(bits));
    bits += 0x7fffu + ((bits >> 16) & 1u);
    return static_cast<std::uint16_t>(bits >> 16);
}
std::string mkl_version() {
    char buffer[512]{}; mkl_get_version_string(buffer,sizeof(buffer)); return buffer;
}
std::string mkl_path() {
    Dl_info info{};
    const auto address=reinterpret_cast<void*>(reinterpret_cast<std::uintptr_t>(&cblas_gemm_bf16bf16f32));
    return dladdr(address,&info)&&info.dli_fname?info.dli_fname:"unavailable";
}
std::string threading_maps() {
    std::ifstream maps("/proc/self/maps"); std::string line, result;
    while(std::getline(maps,line)) {
        if(line.find("libmkl_gnu_thread")!=std::string::npos || line.find("libmkl_intel_thread")!=std::string::npos ||
           line.find("libiomp5.so")!=std::string::npos || line.find("libgomp.so")!=std::string::npos) {
            const auto slash=line.find_last_of('/'); const std::string path=slash==std::string::npos?line:line.substr(slash+1);
            if(result.find(path)==std::string::npos) { if(!result.empty())result+=';'; result+=path; }
        }
    }
    return result;
}
void smoke() {
    const std::uint16_t a[4]={float_to_bf16_rne(1.f),float_to_bf16_rne(2.f),float_to_bf16_rne(3.f),float_to_bf16_rne(4.f)};
    const std::uint16_t b[4]={float_to_bf16_rne(5.f),float_to_bf16_rne(6.f),float_to_bf16_rne(7.f),float_to_bf16_rne(8.f)};
    float c[4]{};
    cblas_gemm_bf16bf16f32(CblasRowMajor,CblasNoTrans,CblasNoTrans,2,2,2,1.f,a,2,b,2,0.f,c,2);
    if(c[0]!=19.f||c[1]!=22.f||c[2]!=43.f||c[3]!=50.f)throw std::runtime_error("oneMKL BF16-BF16-FP32 smoke mismatch");
    const float sf_a[4]={1,2,3,4},sf_b[4]={5,6,7,8};float sf_c[4]{};
    cblas_sgemm(CblasRowMajor,CblasNoTrans,CblasNoTrans,2,2,2,1.f,sf_a,2,sf_b,2,0.f,sf_c,2);
    if(sf_c[0]!=19.f||sf_c[1]!=22.f||sf_c[2]!=43.f||sf_c[3]!=50.f)throw std::runtime_error("oneMKL SGEMM smoke mismatch");
}

std::vector<double> load_checkpoint(const Options& o,std::size_t n,std::uint64_t seed) {
    if(!o.resume || o.checkpoint.empty()) return {};
    std::ifstream f(o.checkpoint); if(!f) return {};
    std::ostringstream ss; ss<<f.rdbuf(); const auto s=ss.str();
    auto str=[&](const std::string& k){const auto p=s.find("\""+k+"\":\"");if(p==std::string::npos)return std::string{};const auto b=p+k.size()+4,e=s.find('"',b);return e==std::string::npos?std::string{}:s.substr(b,e-b);};
    auto num=[&](const std::string& k){const auto p=s.find("\""+k+"\":");if(p==std::string::npos)throw std::runtime_error("raw checkpoint missing "+k);return std::stoull(s.substr(p+k.size()+3));};
    if(str("source_id")!=kSourceId || num("N")!=n || num("threads")!=(unsigned)o.threads || num("seed")!=seed || num("requested_repetitions")!=(unsigned)o.reps) throw std::runtime_error("raw checkpoint parameters/source mismatch");
    const auto p=s.find("\"raw_seconds\":[");if(p==std::string::npos)throw std::runtime_error("raw checkpoint missing samples");
    const auto b=p+15,e=s.find(']',b);if(e==std::string::npos)throw std::runtime_error("invalid raw checkpoint");
    std::vector<double> v;std::stringstream in(s.substr(b,e-b));std::string x;while(std::getline(in,x,','))if(!x.empty())v.push_back(std::stod(x));
    if(v.size()>static_cast<std::size_t>(o.reps) || v.size()!=num("completed_timed_repetitions"))throw std::runtime_error("raw checkpoint count mismatch");
    return v;
}
void save_checkpoint(const Options& o,std::size_t n,std::uint64_t seed,const std::vector<double>& v) {
    if(o.checkpoint.empty()) return;
    const std::string tmp=o.checkpoint+".tmp";std::ofstream f(tmp);
    f<<"{\"source_id\":\""<<kSourceId<<"\",\"N\":"<<n<<",\"threads\":"<<o.threads<<",\"seed\":"<<seed<<",\"requested_repetitions\":"<<o.reps<<",\"completed_timed_repetitions\":"<<v.size()<<",\"complete\":"<<(v.size()==(std::size_t)o.reps?"true":"false")<<",\"raw_seconds\":[";
    for(std::size_t i=0;i<v.size();++i){if(i)f<<',';f<<std::setprecision(17)<<v[i];}f<<"]}\n";f.close();
    if(std::rename(tmp.c_str(),o.checkpoint.c_str())!=0)throw std::runtime_error("cannot atomically replace raw checkpoint");
}

void run(std::ostream& out,std::size_t n,const Options& o) {
    if(n>static_cast<std::size_t>(std::numeric_limits<MKL_INT>::max()))throw std::runtime_error("N exceeds MKL_INT");
    const std::size_t count=n*n;
    std::vector<std::uint16_t>a(count),b(count);
    std::vector<float> c(count);
    std::mt19937_64 rng(o.seed+n);
    std::uniform_real_distribution<float> uniform(-1.f,1.f);
    for(std::size_t i=0;i<count;++i)a[i]=float_to_bf16_rne(uniform(rng));
    for(std::size_t i=0;i<count;++i)b[i]=float_to_bf16_rne(uniform(rng));
    const auto ni=static_cast<MKL_INT>(n);
    auto gemm=[&](){cblas_gemm_bf16bf16f32(CblasRowMajor,CblasNoTrans,CblasNoTrans,ni,ni,ni,1.f,a.data(),ni,b.data(),ni,0.f,c.data(),ni);};
    gemm(); // one warmup; conversion and allocation are outside the measured region.
    std::vector<double> samples=load_checkpoint(o,n,o.seed+n); samples.reserve(o.reps);
    for(std::size_t r=samples.size();r<(std::size_t)o.reps;++r){const auto t0=Clock::now();gemm();samples.push_back(std::chrono::duration<double>(Clock::now()-t0).count());save_checkpoint(o,n,o.seed+n,samples);}
    double mean=0;for(double t:samples)mean+=t;mean/=samples.size();
    const long double flops=2.L*n*n*n;
    long double checksum=0;for(float x:c)checksum+=x;
    out<<"raw_mkl_bf16bf16fp32,"<<n<<','<<o.threads<<','<<o.seed+n<<','<<o.reps<<','
       <<std::setprecision(12)<<mean<<','<<(double)(flops/mean/1.e9L)<<','<<(double)(flops/mean/1.e12L)<<','<<(double)checksum<<",\"";
    for(std::size_t i=0;i<samples.size();++i){if(i)out<<';';out<<samples[i];}
    out<<"\",\""<<mkl_version()<<"\",\""<<mkl_path()<<"\",\""<<threading_maps()<<"\",ok\n";
    out.flush();
}
}
int main(int argc,char**argv)try{
    const auto o=parse(argc,argv);
    const int layer=mkl_set_threading_layer(MKL_THREADING_GNU);
    if(layer!=MKL_THREADING_GNU)throw std::runtime_error("could not select oneMKL GNU threading layer");
    mkl_set_dynamic(0);mkl_set_num_threads(o.threads);
    smoke();
    std::ofstream file;std::ostream*out=&std::cout;
    if(o.output!="-"){file.open(o.output);if(!file)throw std::runtime_error("cannot open output file");out=&file;}
    *out<<"routine,N,threads,seed,repetitions,seconds_mean,GFLOP_s,TFLOP_s,checksum,raw_seconds,mkl_version,mkl_runtime_path,threading_runtime_maps,status\n";
    for(auto n:o.sizes){if(!n)throw std::runtime_error("N must be positive");run(*out,n,o);}
    return 0;
}catch(const std::exception&e){std::cerr<<"raw BF16 benchmark error: "<<e.what()<<'\n';return 2;}
