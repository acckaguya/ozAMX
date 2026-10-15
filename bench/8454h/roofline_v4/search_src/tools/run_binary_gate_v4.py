#!/usr/bin/env python3
"""Compare every V4 gate output against the immutable V3 release library."""
import argparse
import fcntl
import hashlib
import json
import os
import pathlib
import struct
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = ROOT.parents[3]
DRIVER = ROOT / "tools/roofline_binary_gate_v4.cpp"
HEADER_ROOT = ROOT / "include"
FROZEN_LIB = REPO / "bench/8454h/versions/v3_release/artifacts/libozamx_v3.a"
FROZEN_HEADER_ROOT = REPO / "bench/8454h/versions/v3_release/repo/include"
FROZEN_SHA = "73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"
LOCK = pathlib.Path("/tmp/ozamx-perf.lock")
HEADER = struct.Struct("<8sIIIIQQII")
CHUNK = 64 * 1024
CASES = [
    (1,"f32_4096_cube",1,0,4096,4096,4096,4,0),
    (2,"f64_4096_cube_p6",2,6,4096,4096,4096,8,0),
    (3,"f64_4096_cube_p10",2,10,4096,4096,4096,8,0),
    (4,"f64_4096_cube_p15",2,15,4096,4096,4096,8,0),
    (5,"f64_4096_cube_p21",2,21,4096,4096,4096,8,0),
    (6,"f32_4096x4097x257",1,0,4096,4097,257,4,0),
    (7,"f64_4096x4097x257_p21",2,21,4096,4097,257,8,0),
    (8,"f64_4097x4096x4097_p21",2,21,4097,4096,4097,8,0),
    (9,"f64_wide_overflow_k512",2,6,4096,4096,512,8,1),
    (10,"f64_wide_cancellation_k512",2,6,4096,4096,512,8,2),
    (11,"f64_alias_a_equals_c_p6",2,6,4096,4096,256,8,3),
    (12,"f64_alias_b_equals_c_p6",2,6,4096,4096,256,8,4),
    (13,"f32_late_overflow_k4096",1,0,2,3,4096,4,1),
    (14,"f32_late_cancellation_k4096",1,0,2,3,4096,4,2),
    (15,"f32_late_nan_input_k4096",1,0,2,3,4096,4,5),
    (16,"f32_late_inf_input_k4096",1,0,2,3,4096,4,6),
    (17,"f32_alias_a_equals_c_k4096",1,0,2,3,4096,4,3),
    (18,"f32_alias_b_equals_c_k4096",1,0,2,3,4096,4,4),
    (19,"f32_wide_geometry_k1",1,0,4096,4096,1,4,0),
    (20,"f64_wide_geometry_k1_p21",2,21,4096,4096,1,8,0),
]
MODE_NAMES = {0:"normal",1:"overflow_transaction",2:"cancellation_transaction",3:"alias_a_equals_c",
             4:"alias_b_equals_c",5:"nan_input_transaction",6:"inf_input_transaction",
             }

def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(CHUNK),b""): h.update(chunk)
    return h.hexdigest()

def read_exact(stream,n):
    data=bytearray()
    while len(data)<n:
        part=stream.read(n-len(data))
        if not part: raise EOFError(f"wanted {n} bytes, got {len(data)}")
        data.extend(part)
    return bytes(data)

def launch(binary,cid,label,logs,env):
    stderr=logs/f"{label}_{cid:02d}.stderr.log"
    err=stderr.open("wb")
    proc=subprocess.Popen(["taskset","-c","0-63",str(binary),str(cid)],stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,stderr=err,bufsize=0,env=env)
    proc.stdin.write(b"\x01");proc.stdin.flush()
    try: header=HEADER.unpack(read_exact(proc.stdout,HEADER.size))
    except Exception:
        proc.kill();proc.wait();err.close()
        raise RuntimeError(f"{label} child emitted no result header; see {stderr}")
    return proc,err,stderr,header

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate-library",type=pathlib.Path,required=True)
    ap.add_argument("--output",type=pathlib.Path,required=True)
    ap.add_argument("--case-ids",default=",".join(str(x[0]) for x in CASES))
    ap.add_argument("--lock-held",action="store_true",help="caller already holds /tmp/ozamx-perf.lock")
    args=ap.parse_args()
    candidate=args.candidate_library.resolve();out=args.output.resolve()
    out.parent.mkdir(parents=True,exist_ok=True);logs=out.parent/(out.stem+"_logs");logs.mkdir(parents=True,exist_ok=True)
    if not FROZEN_LIB.is_file() or sha(FROZEN_LIB)!=FROZEN_SHA: raise SystemExit("immutable V3 library missing or SHA mismatch")
    if sha(FROZEN_HEADER_ROOT/"ozamx/gemm.hpp")!=sha(HEADER_ROOT/"ozamx/gemm.hpp"):
        raise SystemExit("isolated V4 public header differs from immutable V3 header")
    if not candidate.is_file(): raise SystemExit(f"candidate library missing: {candidate}")
    selected={int(x) for x in args.case_ids.split(",") if x.strip()}
    cases=[x for x in CASES if x[0] in selected]
    if not cases or {x[0] for x in cases}!=selected: raise SystemExit("unknown or empty case selection")
    env=dict(os.environ,OMP_NUM_THREADS="64",OMP_PLACES="cores",OMP_PROC_BIND="close",OMP_DYNAMIC="FALSE")
    cxx=os.environ.get("CXX","g++"); flags=["-std=c++17","-O3","-march=sapphirerapids","-ffp-contract=off","-fno-fast-math","-fopenmp"]
    bindir=out.parent/(out.stem+"_bin");bindir.mkdir(parents=True,exist_ok=True)
    bins=[];commands=[]
    for name,lib,inc,exe in (("v3",FROZEN_LIB,FROZEN_HEADER_ROOT,bindir/"v3"),
                             ("candidate",candidate,HEADER_ROOT,bindir/"candidate")):
        cmd=[cxx,*flags,f"-I{inc}",str(DRIVER),str(lib),"-o",str(exe)]
        with (logs/f"build_{name}.log").open("wb") as f: p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
        commands.append({"binary":name,"argv":cmd,"exit_code":p.returncode,"log":str(logs/f"build_{name}.log")})
        if p.returncode: raise SystemExit(f"{name} gate driver build failed")
        bins.append(exe)
    result={"status":"running","started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
      "reference":"immutable V3 release artifact; full C allocation streamed and compared byte-for-byte",
      "frozen_library_sha256":sha(FROZEN_LIB),"candidate_library":str(candidate),"candidate_library_sha256":sha(candidate),
      "driver_sha256":sha(DRIVER),"header_sha256":sha(HEADER_ROOT/"ozamx/gemm.hpp"),
      "runner_sha256":sha(__file__),"build_commands":commands,"case_order":"V3 then candidate, isolated processes",
      "cases":[],"failure":None}
    out.write_text(json.dumps(result,indent=2)+"\n")
    for cid,name,typ,budget,m,n,k,esize,mode in cases:
        # Alias inputs can require more backing storage than the logical C matrix.
        slots=m*(n+1)+64//esize
        if mode==3: slots=max(slots,m*(k+1)+64//esize)
        if mode==4: slots=max(slots,k*(n+1)+64//esize)
        nbytes=slots*esize; children=[]
        try:
            for label,binary in zip(("v3","candidate"),bins): children.append(launch(binary,cid,label,logs,env))
            hashes=[hashlib.sha256(),hashlib.sha256()];mismatches=0;first=None;offset=0
            checks=[]
            expected_throw=mode in (1,2,5,6)
            for label,(_,_,_,h) in zip(("v3","candidate"),children):
                magic,version,gotid,gottype,status,pbytes,gslots,guards,flags=h
                unchanged=bool(flags&1);exc_kind=(flags>>1)&7
                valid=(magic==b"OZBGATE1" and version==1 and gotid==cid and gottype==typ and status==0 and
                       pbytes==nbytes and gslots==slots and guards==0 and unchanged==expected_throw and
                       exc_kind==(1 if expected_throw else 0))
                checks.append({"binary":label,"valid":valid,"status":status,"payload_bytes":pbytes,
                    "slots":gslots,"guard_failures":guards,"caller_c_unchanged":unchanged,
                    "exception_kind":{0:"none",1:"ozamx::Error",2:"std::exception",3:"unknown"}.get(exc_kind,"invalid")})
            procs=[x[0] for x in children]
            while offset<nbytes:
                count=min(CHUNK,nbytes-offset);parts=[read_exact(p.stdout,count) for p in procs]
                for h,b in zip(hashes,parts):h.update(b)
                if parts[0]!=parts[1]:
                    diff=[j for j,(a,b) in enumerate(zip(*parts)) if a!=b]
                    mismatches+=len(diff)
                    if first is None and diff:first=offset+diff[0]
                offset+=count
            extra=[bool(p.stdout.read(1)) for p in procs];rc=[p.wait() for p in procs]
            stderr_text=[]
            for _,err,path,_ in children:
                err.close();stderr_text.append(path.read_text(errors="replace"))
            ok=all(x["valid"] for x in checks) and mismatches==0 and not any(extra) and rc==[0,0]
            entry={"case":name,"id":cid,"precision":"fp32" if typ==1 else "fp64","budget":budget or None,
              "shape_mnk":[m,n,k],"leading_dimensions":[k+1,n+1,n+1],"mode":MODE_NAMES[mode],
              "expected_full_c_allocation_bytes":nbytes,"bytes_compared":offset,
              "full_output_sha256":{"v3":hashes[0].hexdigest(),"candidate":hashes[1].hexdigest()},
              "byte_mismatches":mismatches,"first_mismatch_offset":first,"binary_semantics":checks,
              "exception_stderr":{"v3":stderr_text[0],"candidate":stderr_text[1]},
              "child_exit_codes":{"v3":rc[0],"candidate":rc[1]},"extra_output_bytes":extra,"pass":ok}
            result["cases"].append(entry);result["status"]="running" if ok else "failed"
            if not ok:result["failure"]={"case":name,"reason":"exception/transaction semantics, full output bytes, guards, or process status failed"}
            out.write_text(json.dumps(result,indent=2)+"\n")
            if not ok:break
        except Exception as exc:
            for proc,err,_,_ in children:
                if proc.poll() is None:proc.kill()
                proc.wait()
                if not err.closed:err.close()
            result["status"]="failed";result["failure"]={"case":name,"reason":repr(exc)};out.write_text(json.dumps(result,indent=2)+"\n");raise
    if result["status"]!="failed":result["status"]="pass"
    result["completed_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime());out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"completed_cases":len(result["cases"]),"output":str(out)}))
    return 0 if result["status"]=="pass" else 1

if __name__=="__main__":
    import sys
    if "--lock-held" in sys.argv:
        raise SystemExit(main())
    with LOCK.open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        raise SystemExit(main())
