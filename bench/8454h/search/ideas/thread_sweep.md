# Thread-count sweep

Five runs were ordered 64, 32, 16, 32, 64 workers, using the same default binary and cache cap, with five repetitions per configuration. At N=4096, reducing to 32 or 16 workers generally increased wall time; at N=1024 the differences were smaller and noisy, and 32 workers sometimes won. Treat this as workload scaling evidence rather than a global default change.

Raw passes are in `../thread_sweep/`; aggregated medians are in `comparison.json` and run protocol in `experiment_metadata.json`.
