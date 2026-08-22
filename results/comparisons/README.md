# Circuit-level comparison results

Output of `run_comparison.py`, comparing conventional and EXORCISM-5 factorized
realizations of each benchmark before and after optimization with PyZX 0.10.5.

## Files

| file | rows | description |
|---|---|---|
| `comparison_600s.csv` | 45 | standard sweep, 600 s PyZX limit per circuit |
| `comparison_600s_failures.csv` | 12 | attempts that exceeded the 600 s limit |
| `comparison_extended_timeout.csv` | 8 | large instances rerun with an 8 h or 24 h limit |
| `comparison_extended_timeout_failures.csv` | 3 | attempts that exceeded the extended limit |

## Columns

| column | meaning |
|---|---|
| `function` | benchmark name |
| `decomposed_baseline` | A, T-count of the conventional realization |
| `baseline_pyzx` | B, A after PyZX; empty if the optimizer timed out |
| `decomposed_factorized` | C, T-count of the factorized realization |
| `factorized_pyzx` | D, C after PyZX; empty if the optimizer timed out |
| `baseline_qubits`, `factorized_qubits` | qubit count of each realization |
| `baseline_gates`, `factorized_gates` | gate count before decomposition |
| `baseline_basic_gates`, `factorized_basic_gates` | gate count after Clifford+T decomposition |
| `baseline_pyzx_seconds`, `factorized_pyzx_seconds` | optimizer wall-clock time |

An empty `baseline_pyzx` or `factorized_pyzx` means that circuit did not finish
within the limit; the corresponding row appears in the matching failures file
with the elapsed time recorded.

## Scope

`comparison_600s.csv` covers 45 of the 64 benchmarks in the suite: 37 structured
benchmarks and 8 oracles. Of these, 39 completed and 6 exceeded the limit
(`sym10_d_100`, `9sym_d_100`, `life_d_100`, `max46_d_100`, `ryy6_198`,
`majority11`), each timing out on both realizations.

The 14 hundred-variable random functions were not submitted for circuit-level
comparison. Their decomposed circuits contain on the order of 10^5 to 10^6 basic
gates, beyond the practical range of the optimizer at any timeout used here.

`comparison_extended_timeout.csv` contains the large instances rerun with an 8 h
or 24 h limit; these are the basis of Fig. 3. Three of the eight benchmarks
appear in both files, having timed out at 600 s and completed under the extended
limit. `shor_modexp_5_mod33_bit1` did not complete its baseline optimization
within 24 h and therefore has no `baseline_pyzx` value; it is reported in the
text and excluded from the Fig. 3 panels, since no paired comparison exists.

## Reproducing

```
python run_comparison.py --timeout 600 --output-prefix cmp --only <benchmark names>
```

Extended-timeout runs used `--timeout 28800` or `--timeout 86400`.
