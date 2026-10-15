#!/usr/bin/env python3
"""Tiny protocol negative test; it never links or calls the GEMM library."""
import importlib.util, pathlib, tempfile

script=pathlib.Path(__file__).with_name("run_matched.py")
spec=importlib.util.spec_from_file_location("run_matched",script)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

try:
    mod.parse_json_line("{not-json", "test")
except RuntimeError:
    pass
else:
    raise SystemExit("malformed JSON was accepted")
try:
    mod.parse_json_line('{"api_wall_seconds":NaN}', "test")
except RuntimeError:
    pass
else:
    raise SystemExit("non-finite JSON number was accepted")

# Exercise a malformed line through the persistent-child protocol reader.
with tempfile.TemporaryDirectory() as td:
    fake=pathlib.Path(td)/"bad-child"
    fake.write_text("#!/bin/sh\nprintf 'this is not JSON\\n'\nsleep 2\n")
    fake.chmod(0o755)
    log=pathlib.Path(td)/"fake.log"
    try:
        mod.Child("fake",fake,dict(__import__("os").environ),log)
    except RuntimeError as e:
        if "malformed JSON" not in str(e): raise
    else:
        raise SystemExit("malformed child greeting was accepted")
print("protocol malformed-input checks passed")
