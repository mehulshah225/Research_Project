# EXORCISM-5: Factorized Boolean Representations for Quantum Circuit Synthesis

Implementation, benchmarks, and evaluation code accompanying "Factorized Boolean
representations for efficient quantum synthesis." This repository takes ESOP
expressions from EXORCISM-4 and applies a two-stage factorization that reduces
quantum cost and T-count by extracting shared computational structure, at a
cost of at most two auxiliary qubits.

**These numbers supersede any earlier statement in this repository or its
history.** All figures below are from the results deposited in this repo,
verified by exhaustive or random-sample equivalence checking against the
originating ESOP for every function reported.

---

## Results

Across 64 single-output Boolean functions (37 structured benchmarks, 14
randomly generated 100-variable functions, and 13 oracles drawn from Shor,
adder and majority-function families):

| | median quantum-cost reduction | median T-count reduction |
|---|---|---|
| Structured benchmarks (37) | 49.7% | 35.4% |
| Random 100-variable functions (14) | 32.9% | 24.0% |
| Oracles — Shor / adder / majority (13) | 61.9% | 38.5% |
| **All 64 functions** | **42.7%** | **28.6%** |

No function increased in quantum cost or T-count; eight were left exactly
unchanged. Auxiliary qubit use never exceeded two, regardless of function size.
All 64 functions pass equivalence verification.

A separate comparison against circuit-level optimization (PyZX) is reported in
the manuscript; see `qasm_pyzx/`, `run_comparison.py` and
`results/comparisons/`.

A second evaluation applies the same transformation to modular-exponentiation
circuits built compositionally rather than from truth tables; see
`benchmarks/mod_cells_pla/`, `results/*/mod_cell/` and `results_modcells.xlsx`.

---

## Pipeline

The pipeline runs in two separately-invoked parts: `run_all.py` builds and
scores every representation (fast, always run this first); `run_comparison.py`
exports circuits and calls PyZX (slow, run only what you need — see below).

### Part 1 — build the executables

```bash
make
```

Builds three binaries from `main_code/` and `maslovCalculator/` via the
`Makefile` (`gcc -O3 -Wall`): `esop_min`, `final_parser`, `maslov`. Nothing
below will run without these. `make clean` removes them.

### Part 2 — representation pipeline (`run_all.py`)

`run_all.py` does not itself contain the algorithm — it drives the three
binaries above plus `verify_equivalence.py` and `containment.py`, and must find
all of them in the repository root. For each PLA file in `benchmarks/`:

1. Read the Boolean function in **PLA format**.
2. **EXORCISM-4** (`exorcism4.exe`, included here) minimizes it to an ESOP
   (`results/esop/`). `results/esop/` already contains its output for every
   deposited benchmark, so steps 3 onward run without re-invoking it.
3. **`esop_min`** (Stage 1, containment): pairs of cubes related by
   containment are merged when doing so strictly reduces quantum cost,
   selected greedily with ties broken by cube distance then residual literal
   count. Output: `results/eosops/`.
4. **`final_parser`** (Stage 2, polarity-aware): remaining cubes are matched
   by a maximum-weight matching on shared-literal count, extracting a common
   factor from complementary-polarity pairs. Output: `results/final_parser/`.
5. **`verify_equivalence.py`** is called by `run_all.py` after every
   benchmark and checks the Stage-2 output against the original ESOP —
   exhaustively for ≤20 variables, by 20,000 random vectors above that.
   **`run_all.py` aborts the entire run on the first failure; it does not
   continue past one.** (`verify_equivalence.py` can also be run standalone
   on any esop/final pair — see its `--help`.)
6. **`maslov`** evaluates quantum cost, T-count (4(n−1) per n-control gate,
   an AND-tree of measurement-assisted AND gates), gate count, maximum
   control count, and auxiliary qubit peak/total, on every stage's output.
7. **`containment.py`** supplies the structural metrics. `parse_file()` reads
   any stage's PLA/ESOP/EOSOPS/FINAL output and returns the variable count,
   declared cube count, literal count and cube list. `compute_ssd()` computes
   **Shared Support Density**: for every pair of cubes, the number of positions
   at which both are non-`-` and equal, averaged over all pairs and normalised
   by the variable count. SSD measures how much shared structure a
   representation contains, and so how much material the two factorization
   stages have to work with. It populates the Structure sheet of
   `results.xlsx`. `run_all.py` imports both functions.

Run it with:

```bash
python run_all.py
```

Regenerates `results.xlsx` (sheets: Maslov Cost, T-Count, Resources,
Structure) and prints a summary including equivalence pass/fail counts. Takes
well under a minute for the full 64-function suite (representation-level
synthesis, not circuit export — see the timing note below).

### Part 3 — circuit export and comparison with PyZX (`run_comparison.py`)

This is a **separate, optional** step that exports both representations to
OpenQASM (`export_qasm.py`) and optimizes each with PyZX, to test whether the
representation-level reduction survives translation to an executable circuit
and whether it composes with circuit-level optimization. It requires `pyzx`
(`pip install pyzx`) and is not needed to reproduce the Table/Fig. results
above, only the separate circuit-comparison result in the manuscript.

**Circuit export runs on every benchmark** and is always fast (well under a
second each; QASM files land in `qasm/`). **PyZX optimization is the slow
part**, and its runtime scales roughly with circuit size to a high power.
Small benchmarks finish in one to five seconds; the largest instances took
from forty minutes to over nineteen hours *each* in our runs. The 14
`f_100_*` random 100-variable functions were not submitted at all: their
decomposed circuits contain on the order of 10^5 to 10^6 basic gates, beyond
the practical range of the optimizer at any timeout used here.
`run_comparison.py` does not filter them out automatically, so an unfiltered
run will attempt them and stall.

Three ways to invoke it:

```bash
# a named set at the standard 600 s limit (this is how the deposited
# comparison results were produced; --output-prefix keeps parallel runs
# from overwriting each other)
python run_comparison.py --timeout 600 --output-prefix cmp_w1 --only 6sym alu_9 mux_185

# the 11 large-but-not-f_100 benchmarks, with an extended cap
python run_comparison.py --timeout 28800 --targeted

# one benchmark at a longer cap still
python run_comparison.py --only shor_modexp_5_mod33_bit0 --timeout 86400 --output-prefix cmp_mod33b0
```

`--targeted` runs exactly the 11 large-but-not-`f_100` benchmarks
(`shor_modexp_2_mod21_bit0/1`, `shor_modexp_5_mod33_bit0/1`, `9sym_d_100`,
`sym10_d_100`, `life_d_100`, `max46_d_100`, `majority9`, `majority11`,
`ryy6_198`) — this is the set worth raising the timeout for. `--only NAME`
restricts to named benchmarks; `--output-prefix` sets the output CSV prefix.

Never run `run_comparison.py` unfiltered against the full `benchmarks/`
directory without excluding `synth_benchmarks/` first — there is no
`f_100_*` skip built in.

#### Deposited comparison results (`results/comparisons/`)

| file | rows | description |
|---|---|---|
| `comparison_600s.csv` | 45 | standard sweep, 600 s PyZX limit per circuit |
| `comparison_600s_failures.csv` | 12 | attempts that exceeded the 600 s limit |
| `comparison_extended_timeout.csv` | 8 | large instances rerun at an 8 h or 24 h limit |
| `comparison_extended_timeout_failures.csv` | 3 | attempts that exceeded the extended limit |

The `cmp_w*.csv` and `cmp_oracles*.csv` files in the same directory are the raw
per-window outputs the two 600 s files were merged from, kept for provenance.

Columns are `function`, `decomposed_baseline` (A), `baseline_pyzx` (B),
`decomposed_factorized` (C), `factorized_pyzx` (D), qubit counts, gate counts
before and after Clifford+T decomposition, and optimizer wall-clock seconds. An
empty `baseline_pyzx` or `factorized_pyzx` means that circuit did not finish
within the limit, and the matching failures file records the elapsed time.

`comparison_600s.csv` covers 45 of the 64 benchmarks — the 37 structured plus 8
oracles. Of these, 39 completed and 6 exceeded the limit (`sym10_d_100`,
`9sym_d_100`, `life_d_100`, `max46_d_100`, `ryy6_198`, `majority11`), each
timing out on both realizations.

`comparison_extended_timeout.csv` holds the large instances rerun at 8 h or
24 h and is the basis of the circuit-comparison figure. Three benchmarks appear
in both files, having timed out at 600 s and completed under the extended cap.
`shor_modexp_5_mod33_bit1` did not complete its baseline optimization within
24 h and so has no `baseline_pyzx` value; it is reported in the manuscript text
and excluded from the figure panels, since no paired comparison exists.

---

## Repository structure

```
main_code/              main.c, cube_containment.c/.h, cube_merge.c/.h,
                          final_parser.c, cube_types.h
maslovCalculator/       maslovCalculator.c — cost and T-count evaluation
benchmarks/             one directory per structured benchmark;
                          synth_benchmarks/ (14 random 100-variable functions);
                          oracle_pla/ (Shor, adder, majority);
                          mod_cells_pla/ (compositional modular-exponentiation
                          cells, one directory per modulus width)
results/                esop/, eosops/, final_parser/ — output of each stage,
                          each with a mod_cell/ subdirectory for the
                          compositional cells
                        comparisons/ — deposited PyZX comparison CSVs
qasm/, qasm_pyzx/       circuit exports and PyZX-optimized circuits
containment.py          PLA/ESOP parsing and Shared Support Density metric,
                          imported by run_all.py
verify_equivalence.py   standalone equivalence checker (also called by run_all.py)
export_qasm.py          representation -> OpenQASM 2.0
run_comparison.py       PyZX comparison harness
generate_synthetic.py   regenerates the 14 random 100-variable benchmarks (seeded)
run_all.py              full pipeline driver
exorcism4.exe           EXORCISM-4 ESOP minimizer
results.xlsx            deposited results for the 64-function suite,
                          all rows equivalence-verified
results_modcells.xlsx   deposited results for the compositional cells,
                          same four sheets, same resource models
```

## Requirements

- `gcc` (`make` builds `esop_min`, `final_parser`, `maslov` via the Makefile)
- Python 3, `pandas`, `openpyxl` (for `run_all.py`)
- `pyzx` — only for `run_comparison.py` (Part 3); not needed for Parts 1–2.
- `scipy` — only if you want to recompute the sign test over the comparison
  results.

## Citation

If you use this repository, please cite the accompanying manuscript
(citation to be added on publication) rather than this repository directly.

## Contact

Mehul Shah — mehul@pdx.edu / mehulshah2225@gmail.com