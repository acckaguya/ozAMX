# Local AMX/xstate validation probes

These four C files were written locally for a read-only CPU/OS capability and permission check. They are **not Intel upstream examples** and are not performance benchmarks. `ARCH_REQ_XCOMP_PERM` only set process permission in each short-lived probe process; nothing was changed system-wide. The AMX instruction probe executes only `TILERELEASE`; it does not run GEMM or time instructions.

Compile/run commands used (from repository root):

- `xstate_probe`: `gcc -O2 -Wall -Wextra -o /tmp/ozamx-8454h/xstate_probe third_party/intel/xeon-8454h/hardware-snapshot/local-probes/xstate_probe.c && /tmp/ozamx-8454h/xstate_probe`
- `amx_perm_probe`: `gcc -O2 -Wall -Wextra -o /tmp/ozamx-8454h/amx_perm_probe third_party/intel/xeon-8454h/hardware-snapshot/local-probes/amx_perm_probe.c && /tmp/ozamx-8454h/amx_perm_probe`
- `amx_exec_probe`: `gcc -O2 -Wall -Wextra -mamx-tile -o /tmp/ozamx-8454h/amx_exec_probe third_party/intel/xeon-8454h/hardware-snapshot/local-probes/amx_exec_probe.c && /tmp/ozamx-8454h/amx_exec_probe`
- `amx_thread_probe`: `gcc -O2 -Wall -Wextra -pthread -o /tmp/ozamx-8454h/amx_thread_probe third_party/intel/xeon-8454h/hardware-snapshot/local-probes/amx_thread_probe.c && /tmp/ozamx-8454h/amx_thread_probe`

Source hashes and sizes:

- `third_party/intel/xeon-8454h/hardware-snapshot/local-probes/amx_exec_probe.c` — 634 bytes, SHA-256 `53b4145f20e1b05dc4e4e6926b7e9fd187484bff7a85135cbf0e5d93efc9d619`
- `third_party/intel/xeon-8454h/hardware-snapshot/local-probes/amx_perm_probe.c` — 697 bytes, SHA-256 `0c23c9ef37d053f508d461451f4b38067c145d8b85ccebf5754018bb94f14234`
- `third_party/intel/xeon-8454h/hardware-snapshot/local-probes/amx_thread_probe.c` — 1448 bytes, SHA-256 `005afdd1ef54c37cd20ced85e38845aae37c39182efd520d143820d797c13af4`
- `third_party/intel/xeon-8454h/hardware-snapshot/local-probes/xstate_probe.c` — 1356 bytes, SHA-256 `0ac712fc9bcd15f973658cf2be828695db6ce5b8d5f9a2babfbaa8fb154743f6`
