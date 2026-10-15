#!/usr/bin/env python3
"""Run the 47-case extended validation at two cache settings and compare JSON rows without JSONL files."""
import argparse
import fcntl
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
SOURCE = ROOT / "tests/extended_validation.cpp"
HEADER_ROOT = ROOT / "bench/8454h/versions/v2/include"
HEADER = HEADER_ROOT / "ozamx/gemm.hpp"
DEFAULT_LIB = pathlib.Path("/tmp/ozamx-roofline-production/libozamx.a")
LOCK = pathlib.Path("/tmp/ozamx-perf.lock")
DEFAULT_SUMMARY = ROOT / "bench/8454h/roofline/extended47_cache_gate.json"
LOGS = ROOT / "bench/8454h/roofline/extended47_cache_gate_logs"
FLAGS = ["-std=c++17", "-O2", "-march=sapphirerapids", "-ffp-contract=off",
         "-mamx-tile", "-mamx-bf16", "-fopenmp"]
SHAPES = [[1,17,31],[7,33,33],[17,65,257],[65,129,65],[256,256,256],
          [512,512,512],[256,512,256],[512,256,512],[1024,1024,1024]]


def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(65536),b""):h.update(chunk)
    return h.hexdigest()


def run_stream(binary, cache_bytes, cpu, log_path, env_base):
    env=dict(env_base, OZAMX_WORKSPACE_CACHE_BYTES=str(cache_bytes))
    with pathlib.Path(log_path).open("wb") as err:
        proc=subprocess.Popen(["taskset","-c",str(cpu),str(binary)],stdout=subprocess.PIPE,
                              stderr=err,bufsize=0,env=env)
        rows=[]
        for line_num,line in enumerate(proc.stdout,1):
            if not line.endswith(b"\n"):
                proc.kill();proc.wait()
                raise RuntimeError(f"cache={cache_bytes}: unterminated JSON row {line_num}")
            try: rows.append(json.loads(line))
            except Exception as exc:
                proc.kill();proc.wait()
                raise RuntimeError(f"cache={cache_bytes}: invalid JSON row {line_num}: {exc}")
        rc=proc.wait()
    return rows,rc


def compare_rows(a,b):
    if len(a)!=47 or len(b)!=47:raise RuntimeError(f"expected 47 rows each, got {len(a)} and {len(b)}")
    comparisons=[];total_slots=0;full_rows=0;digest_rows=0
    for ix,(x,y) in enumerate(zip(a,b)):
        if x.get("case")!=y.get("case"):raise RuntimeError(f"case identity differs at row {ix}")
        for key in ("m","n","k","ldc","budget","output_slots","oracle_samples"):
            if x.get(key)!=y.get(key):raise RuntimeError(f"{key} differs for {x['case']}")
        if "guards_ok" in x or "guards_ok" in y:
            if x.get("guards_ok") is not True or y.get("guards_ok") is not True:
                raise RuntimeError(f"oracle/padding/canary failure at {x['case']}")
        slots=int(x.get("output_slots",0));total_slots+=slots
        if "bits" in x or "bits" in y:
            if x.get("bits") is None or y.get("bits") is None:raise RuntimeError(f"one full-bit vector missing at {x['case']}")
            if len(x["bits"])!=len(y["bits"]):raise RuntimeError(f"bit vector length differs at {x['case']}")
            mismatch=next((q for q,(u,v) in enumerate(zip(x["bits"],y["bits"])) if u!=v),None)
            if mismatch is not None:raise RuntimeError(f"full bit mismatch at {x['case']} slot {mismatch}")
            method="full_bit_vector";full_rows+=1
        elif "output_digest" in x or "output_digest" in y:
            if x.get("output_digest")!=y.get("output_digest"):raise RuntimeError(f"full-output digest mismatch at {x['case']}")
            method="128_bit_full_output_digest";digest_rows+=1
        else:
            for key in ("threw","c_unchanged"):
                if x.get(key)!=y.get(key):raise RuntimeError(f"{key} differs at {x['case']}")
            if x.get("case")=="fp32_overflow_transaction" and not(x.get("threw") and x.get("c_unchanged")):
                raise RuntimeError("FP32 overflow must throw and leave C unchanged")
            if x.get("case")=="fp64_invalid_transaction" and not(x.get("threw") and x.get("c_unchanged")):
                raise RuntimeError("FP64 invalid input must throw and leave C unchanged")
            method="transactional_exception";digest_rows+=1
        comparisons.append({"case":x["case"],"output_slots":slots,"method":method,
                            "exact_match":True,"guards_ok":True})
    return {"cases":len(comparisons),"compared_output_slots":total_slots,
            "full_bit_vector_cases":full_rows,"digest_or_transaction_cases":digest_rows,
            "bitwise_mismatches":0,"case_results":comparisons}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--library",type=pathlib.Path,default=DEFAULT_LIB)
    ap.add_argument("--header",type=pathlib.Path,default=HEADER)
    ap.add_argument("--summary",type=pathlib.Path,default=DEFAULT_SUMMARY)
    ap.add_argument("--threads",type=int,default=1)
    args=ap.parse_args()
    lib=args.library.resolve();header=args.header.resolve();out=args.summary.resolve()
    if not SOURCE.is_file() or not lib.is_file() or not header.is_file():raise SystemExit("missing source/library/header")
    if sha(header)!=sha(HEADER):raise SystemExit("requested public header differs from frozen V2 header")
    if args.threads<1:raise SystemExit("--threads must be positive")
    global LOGS
    LOGS=out.parent/f"{out.stem}_logs";LOGS.mkdir(parents=True,exist_ok=True);out.parent.mkdir(parents=True,exist_ok=True)
    cxx=os.environ.get("CXX","g++")
    with tempfile.TemporaryDirectory(prefix="ozamx-extended47-") as temp:
        exe=pathlib.Path(temp)/"extended47"
        cmd=[cxx,*FLAGS,f"-I{header.parent.parent}",str(SOURCE),str(lib),"-o",str(exe)]
        build_log=LOGS/"build.log"
        with build_log.open("wb") as f: build_rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
        if build_rc:raise SystemExit(f"extended47 build failed; see {build_log}")
        env=dict(os.environ,OMP_NUM_THREADS=str(args.threads),OMP_DYNAMIC="FALSE",OMP_PLACES="cores",OMP_PROC_BIND="close")
        started=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
        rows2,rc2=run_stream(exe,2147483648,0,LOGS/"cache_2g.stderr.log",env)
        rows0,rc0=run_stream(exe,0,1,LOGS/"cache_0.stderr.log",env)
        report={"status":"running","started_utc":started,"completed_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                "library_path":str(lib),"library_sha256":sha(lib),"header_sha256":sha(header),
                "source_path":str(SOURCE),"source_sha256":sha(SOURCE),"runner_sha256":sha(__file__),
                "build_command":cmd,"build_log":str(build_log),"build_log_sha256":sha(build_log),
                "run_conditions":{"threads":args.threads,"openmp_dynamic":False,"cache_bytes":[2147483648,0],
                                  "processes_sequential":True,"pinning":{"2g":"CPU0","cache0":"CPU1"},
                                  "stdout":"JSON lines consumed directly from pipes; no JSONL/output files retained"},
                "shapes":SHAPES,"precisions":["fp32","fp64-p6","fp64-p10","fp64-p15","fp64-p21"],
                "process_exit_codes":{"cache_2g":rc2,"cache_0":rc0},
                "stderr_logs":{"cache_2g":str(LOGS/"cache_2g.stderr.log"),"cache_0":str(LOGS/"cache_0.stderr.log")},
                "checks":None}
        try:
            report["checks"]=compare_rows(rows2,rows0)
            if rc2 or rc0:raise RuntimeError(f"child exit codes: 2g={rc2} cache0={rc0}")
            report["status"]="pass"
        except Exception as exc:
            report["status"]="fail";report["failure"]=repr(exc)
        out.write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps({"status":report["status"],"cases":report["checks"]["cases"] if report["checks"] else 0,
                          "summary":str(out)}))
        return 0 if report["status"]=="pass" else 1


if __name__=="__main__":
    with LOCK.open("a+") as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        sys.exit(main())
