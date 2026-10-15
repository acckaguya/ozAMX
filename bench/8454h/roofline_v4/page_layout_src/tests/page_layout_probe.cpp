#include "../src/preprocess.hpp"

#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

namespace {
std::size_t anon_huge_kb_for(const void* ptr) {
    std::ifstream in("/proc/self/smaps");
    std::string line;
    const auto address=reinterpret_cast<std::uintptr_t>(ptr);
    bool hit=false;
    std::size_t value=0;
    while(std::getline(in,line)) {
        std::uintptr_t lo=0,hi=0;
        if(std::sscanf(line.c_str(),"%lx-%lx",&lo,&hi)==2) { hit=address>=lo&&address<hi; continue; }
        if(hit&&line.rfind("AnonHugePages:",0)==0) {
            std::istringstream ss(line.substr(14));ss>>value;return value;
        }
    }
    return 0;
}
}

int main() {
    using namespace ozamx::detail;
    constexpr std::size_t small_n=(std::size_t(1)<<20)+17;
    constexpr std::size_t large_n=(std::size_t(8)<<20)+123;
    AlignedBuffer<unsigned char> small(small_n), large(large_n);
    if(!small.data()||!large.data()) return 2;
    std::memset(large.data(),0x5a,large.size());
    const auto small_addr=reinterpret_cast<std::uintptr_t>(small.data());
    const auto large_addr=reinterpret_cast<std::uintptr_t>(large.data());
    const std::size_t large_alignment=OZV4_PAGE_ALIGNMENT;
    const bool align_ok=small_addr%64==0&&large_addr%large_alignment==0;
    const auto& pool=workspace_pool();
    const bool hint_ok=OZV4_MADV_HUGEPAGE ? pool.hint_attempts==1&&(pool.hint_successes+pool.hint_failures)==1 : pool.hint_attempts==0;
    const auto ahp=anon_huge_kb_for(large.data());
    std::printf("{\"status\":\"%s\",\"small_bytes\":%zu,\"small_alignment_mod64\":%zu,\"large_bytes\":%zu,\"large_alignment\":%zu,\"large_alignment_mod\":%zu,\"hint_enabled\":%d,\"hint_attempts\":%llu,\"hint_successes\":%llu,\"hint_failures\":%llu,\"hint_last_errno\":%d,\"anon_huge_kb_in_mapping\":%zu,\"smaps_scope\":\"VMA containing large allocation pointer; may include allocator mapping overhead\"}\n",
        align_ok&&hint_ok?"pass":"fail",small_n,std::size_t(small_addr%64),large_n,large_alignment,std::size_t(large_addr%large_alignment),int(OZV4_MADV_HUGEPAGE),
        (unsigned long long)pool.hint_attempts,(unsigned long long)pool.hint_successes,(unsigned long long)pool.hint_failures,pool.hint_last_errno,ahp);
    return align_ok&&hint_ok?0:1;
}
