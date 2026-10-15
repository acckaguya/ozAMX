// Reuse the audited private AMX split/pack/panel microkernel without changing
// the public API. This diagnostic is intentionally independent of CMake.
#define main native_kernel_audit_hidden_main
#include "native_kernel_audit.cpp"
#undef main

#include <array>
#include <filesystem>
#include <fstream>
#include <regex>
#include <mkl.h>

namespace {
constexpr std::size_t N=256, COUNT=N*N;
constexpr std::array<const char*,1> METHODS={"diagnostic_signed_rho44"};
constexpr std::array<int,4> DEPTHS={3,4,5,6};

std::string read_text(const std::filesystem::path& path) {
    std::ifstream in(path);
    if(!in)throw std::runtime_error("cannot read metadata: "+path.string());
    return std::string(std::istreambuf_iterator<char>(in),{});
}
std::uint64_t json_uint(const std::string& text,const std::string& key) {
    const std::regex pattern("\\\""+key+"\\\"\\s*:\\s*([0-9]+)");
    std::smatch match;
    if(!std::regex_search(text,match,pattern))throw std::runtime_error("metadata lacks numeric key: "+key);
    return std::stoull(match[1].str());
}
template<class T>std::vector<T> read_raw(const std::filesystem::path& path,std::size_t count) {
    if(std::filesystem::file_size(path)!=count*sizeof(T))throw std::runtime_error("unexpected raw file size: "+path.string());
    std::vector<T> values(count);
    std::ifstream in(path,std::ios::binary);
    if(!in||!in.read(reinterpret_cast<char*>(values.data()),static_cast<std::streamsize>(count*sizeof(T))))
        throw std::runtime_error("cannot read raw file: "+path.string());
    return values;
}
std::uint32_t alt_fbits(float x){std::uint32_t u;std::memcpy(&u,&x,sizeof(u));return u;}
std::uint32_t alt_ordered(std::uint32_t u){return (u&0x80000000u)?~u:(u|0x80000000u);}
std::uint32_t ulp_distance(float a,float b){const auto x=alt_ordered(alt_fbits(a)),y=alt_ordered(alt_fbits(b));return x>y?x-y:y-x;}

struct ErrorMetrics { double ef=0.0, scaled_max=0.0; };
ErrorMetrics compare(const std::vector<long double>& value,
                     const std::vector<long double>& reference,
                     const std::vector<long double>& denominator) {
    long double error2=0,reference2=0,scaled=0;
    for(std::size_t q=0;q<COUNT;++q){
        const long double d=value[q]-reference[q];
        error2+=d*d;reference2+=reference[q]*reference[q];
        const long double absd=std::fabs(d);
        scaled=std::max(scaled,denominator[q]==0?absd:absd/denominator[q]);
    }
    return {static_cast<double>(reference2==0?std::sqrt(error2):std::sqrt(error2/reference2)),
            static_cast<double>(scaled)};
}

void write_method(std::ostream& out,const std::filesystem::path& dir,
                  const std::string& method,std::uint64_t seed,
                  const std::vector<long double>& reference,
                  const std::vector<long double>& denominator,
                  const std::vector<long double>& mkl_reference,
                  const std::vector<long double>& mkl_denominator) {
    const auto as=read_raw<std::uint16_t>(dir/(method+"_A.bf16le"),6*COUNT);
    const auto bs=read_raw<std::uint16_t>(dir/(method+"_B.bf16le"),6*COUNT);
    auto packed=ozamx::pack64<6>(as,bs,N,N,N);

    // Materialize every real AMX component/BK output once. The source arrays
    // are the exported BF16 slices; this path never calls split64 or GEMM API.
    std::array<std::vector<float>,36> amx_products;
    for(auto& product:amx_products)product.resize(COUNT);
    for(int ai=0;ai<6;++ai)for(int bi=0;bi<6;++bi){
        auto& product=amx_products[ai*6+bi];
        for(std::size_t mi=0;mi<N;mi+=ozamx::TM)
         for(std::size_t nj=0;nj<N;nj+=ozamx::TN){
            float tile[ozamx::TM*ozamx::TN];
            ozamx::run_fp64_product<6>(packed,ai,bi,0,0,0,mi,nj,tile);
            for(std::size_t i=0;i<ozamx::TM;++i)
             std::copy(tile+i*ozamx::TN,tile+(i+1)*ozamx::TN,
                       product.data()+(mi+i)*N+nj);
         }
    }

    std::array<std::vector<long double>,4> selected_ld,selected_fp32,actual_amx;
    for(int q=0;q<4;++q){selected_ld[q].assign(COUNT,0);selected_fp32[q].assign(COUNT,0);actual_amx[q].assign(COUNT,0);}
    std::array<std::uint64_t,4> store_mismatches{};
    std::array<std::uint32_t,4> max_ulp{};
    std::array<std::array<std::uint64_t,36>,4> product_mismatches{};
    std::array<std::array<std::uint32_t,36>,4> product_max_ulp{};

    // Exact-enough independent references use host long double (documented in
    // the accompanying note) and row parallelism only for the reference math.
    for(int diagonal=0;diagonal<6;++diagonal)for(int ai=0;ai<=diagonal;++ai){
        const int bi=diagonal-ai, product_id=ai*6+bi;
        std::vector<long double> direct(COUNT,0);
#pragma omp parallel for schedule(static)
        for(std::size_t i=0;i<N;++i){
            for(std::size_t k=0;k<N;++k){
                const long double av=ozamx::bf16_to_float(as[std::size_t(ai)*COUNT+i*N+k]);
                // Each parallel iteration owns a complete output row.
                for(std::size_t j=0;j<N;++j)
                    direct[i*N+j]+=av*static_cast<long double>(
                        ozamx::bf16_to_float(bs[std::size_t(bi)*COUNT+k*N+j]));
            }
        }
        const auto& hardware=amx_products[product_id];
        for(int budget=0;budget<4;++budget)if(diagonal<DEPTHS[budget]){
            for(std::size_t q=0;q<COUNT;++q){
                const float rounded=static_cast<float>(direct[q]);
                selected_ld[budget][q]+=direct[q];
                selected_fp32[budget][q]+=static_cast<long double>(rounded);
                actual_amx[budget][q]+=static_cast<long double>(hardware[q]);
                const auto distance=ulp_distance(rounded,hardware[q]);
                if(alt_fbits(rounded)!=alt_fbits(hardware[q])){
                    ++store_mismatches[budget];++product_mismatches[budget][product_id];
                }
                max_ulp[budget]=std::max(max_ulp[budget],distance);
                product_max_ulp[budget][product_id]=
                    std::max(product_max_ulp[budget][product_id],distance);
            }
        }
    }
    const std::array<const char*,4> names={"6","10","15","21"};
    for(int q=0;q<4;++q){
        const auto exact_selected=compare(selected_ld[q],reference,denominator);
        const auto ideal_fp32=compare(selected_fp32[q],reference,denominator);
        const auto hardware=compare(actual_amx[q],reference,denominator);
        const auto mkl=compare(actual_amx[q],mkl_reference,mkl_denominator);
        out<<"summary,"<<method<<','<<names[q]<<",,"<<N<<','<<seed<<','
           <<std::setprecision(17)<<exact_selected.ef<<','<<exact_selected.scaled_max<<','
           <<ideal_fp32.ef<<','<<ideal_fp32.scaled_max<<','
           <<hardware.ef<<','<<hardware.scaled_max<<','<<mkl.ef<<','<<mkl.scaled_max<<','
           <<store_mismatches[q]<<','<<max_ulp[q]<<'\n';
        for(int diagonal=0;diagonal<DEPTHS[q];++diagonal)
         for(int ai=0;ai<=diagonal;++ai){
            const int bi=diagonal-ai,product_id=ai*6+bi;
            out<<"product,"<<method<<','<<names[q]<<",a"<<ai<<"b"<<bi<<','<<N<<','<<seed
               <<",,,,,,,,,"<<product_mismatches[q][product_id]<<','
               <<product_max_ulp[q][product_id]<<'\n';
         }
    }
}
}

int main(int argc,char**argv)try{
    if(argc!=2){std::cerr<<"usage: native_alternative_accuracy EXPORT_DIR\n";return 2;}
    const std::filesystem::path dir=argv[1];
    const auto metadata=read_text(dir/"metadata.json");
    if(json_uint(metadata,"n")!=N)throw std::runtime_error("export must contain N=256");
    const auto seed=json_uint(metadata,"seed");
    for(const char* method:METHODS)
        if(metadata.find(std::string("\"")+method+"\"")==std::string::npos)
            throw std::runtime_error(std::string("metadata lacks method: ")+method);
    const auto a=read_raw<double>(dir/"A.f64le",COUNT);
    const auto b=read_raw<double>(dir/"B.f64le",COUNT);
    std::vector<long double> reference(COUNT),denominator(COUNT),mkl_reference(COUNT),mkl_denominator(COUNT);
    std::vector<double> mkl_ref_f64(COUNT),mkl_den_f64(COUNT),abs_a(COUNT),abs_b(COUNT);
    for(std::size_t q=0;q<COUNT;++q){abs_a[q]=std::fabs(a[q]);abs_b[q]=std::fabs(b[q]);}
    cblas_dgemm(CblasRowMajor,CblasNoTrans,CblasNoTrans,N,N,N,1.0,a.data(),N,b.data(),N,0.0,mkl_ref_f64.data(),N);
    cblas_dgemm(CblasRowMajor,CblasNoTrans,CblasNoTrans,N,N,N,1.0,abs_a.data(),N,abs_b.data(),N,0.0,mkl_den_f64.data(),N);
    for(std::size_t q=0;q<COUNT;++q){mkl_reference[q]=mkl_ref_f64[q];mkl_denominator[q]=mkl_den_f64[q];}
#pragma omp parallel for schedule(static)
    for(std::size_t i=0;i<N;++i)for(std::size_t j=0;j<N;++j){
        long double sum=0,bound=0;
        for(std::size_t k=0;k<N;++k){
            const long double x=a[i*N+k],y=b[k*N+j];
            sum+=x*y;bound+=std::fabs(x)*std::fabs(y);
        }
        reference[i*N+j]=sum;denominator[i*N+j]=bound;
    }
    const auto permission=ozamx::request_amx_permission_for_current_thread();
    if(!permission.cpu_amx_tile||!permission.cpu_amx_bf16||!permission.permission_available)
        throw std::runtime_error("AMX unavailable: "+permission.message);
    ozamx::load_config();
    std::cout<<"record_type,method,budget,product,N,seed,eF_selected_longdouble,scaledmax_selected_longdouble,eF_selected_fp32_rounded,scaledmax_selected_fp32_rounded,eF_actual_amx,scaledmax_actual_amx,eF_vs_mkl,scaledmax_vs_mkl,product_store_mismatches,max_ulp\n";
    for(const char* method:METHODS)write_method(std::cout,dir,method,seed,reference,denominator,mkl_reference,mkl_denominator);
    _tile_release();
    return 0;
}catch(const std::exception&e){std::cerr<<"signed-shift native diagnostic: "<<e.what()<<'\n';return 2;}
