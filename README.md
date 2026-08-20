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

Across 63 single-output Boolean functions (36 structured benchmarks, 14
randomly generated 100-variable functions, and 13 oracles drawn from Shor,
adder and majority-function families):

| | median quantum-cost reduction | median T-count reduction |
|---|---|---|
| Structured benchmarks | 47.6% | — |
| Random 100-variable functions | 32.9% | — |
| Oracles (Shor / adder / majority) | 61.9% | 38.5% |
| **All 63 functions** | **42.2%** | **30.3%** |

No function increased in quantum cost or T-count. Auxiliary qubit use never
exceeded two, regardless of function size.

Search oracles built from random 3-SAT instances were evaluated but are **not
included** in the reported results: at the clause-to-variable ratio used
(4.26, the satisfiability threshold), instances typically admit only one to
four satisfying assignments, so the minimized expression comprises one or two
product terms and no pair of terms exists for factorization to act on. This
is a limitation of truth-table synthesis for that oracle family, not of the
transformation. See `benchmarks/grover_oracles/` (regenerate with
`generate_grover_oracles.py`) if you want to reproduce this.

A separate comparison against circuit-level optimization (PyZX) is reported
in the manuscript; see `qasm_pyzx/`, `run_comparison.py` and
`comparison.csv` / `comparison_failures.csv`.

---

## Pipeline

1. Boolean benchmark functions in **PLA format** (`benchmarks/`).
2. **EXORCISM-4** minimizes each to an ESOP (`results/esop/`).
3. **Stage 1 — containment factorization** (`main_code/cube_containment.c`,
   `main_code/cube_merge.c`, built as `esop_min`): pairs of cubes related by
   containment are merged when doing so strictly reduces quantum cost,
   selected greedily with ties broken by cube distance then residual literal
   count. Output: `results/eosops/`.
4. **Stage 2 — polarity-aware factorization** (`main_code/final_parser.c`,
   built as `final_parser`): remaining cubes are matched by a
   maximum-weight matching on shared-literal count, extracting a common
   factor from complementary-polarity pairs. Output: `results/final_parser/`.
5. **Equivalence verification** (`verify_equivalence.py`): every factorized
   representation is checked against its originating ESOP — exhaustively for
   ≤20 variables, by 20,000 random vectors above that. `run_all.py` aborts
   the run on any failure; it does not continue past one.
6. **Resource evaluation** (`maslovCalculator/maslovCalculator.c`, built as
   `maslov`): Maslov quantum cost, T-count (4(n-1) per n-control gate, an
   AND-tree of measurement-assisted AND gates), gate count, maximum control
   count, and auxiliary qubit peak/total.
7. **Circuit export and comparison** (`export_qasm.py`,
   `run_comparison.py`): both representations are decomposed to OpenQASM
   and optimized with PyZX, to test whether the representation-level
   reduction survives translation to an executable circuit and whether it
   composes with circuit-level optimization.

Run the full pipeline with:

```bash
python run_all.py
```

This regenerates `results.xlsx` (sheets: Maslov Cost, T-Count, Resources,
Structure) and prints a summary including equivalence pass/fail counts.

---

## Repository structure

```
main_code/            containment.c, cube_merge.c, final_parser.c, cube_types.h
maslovCalculator/      cost and T-count evaluation (maslov)
benchmarks/            one directory per structured benchmark; synth_benchmarks/
                        (14 random 100-variable functions); oracle_pla/
                        (Shor, adder, majority); grover_oracles/ (excluded, see above)
results/                esop/, eosops/, final_parser/ — output of each stage
qasm/, qasm_pyzx/       circuit exports and PyZX-optimized circuits
verify_equivalence.py   standalone equivalence checker (also called by run_all.py)
export_qasm.py          representation -> OpenQASM 2.0
run_comparison.py       PyZX comparison harness (produces comparison.csv)
generate_synthetic.py   regenerates the 14 random 100-variable benchmarks (seeded)
generate_grover_oracles.py   regenerates the excluded 3-SAT oracle set (seeded)
run_all.py              full pipeline driver
results.xlsx            deposited results, all rows equivalence-verified
```

## Requirements

- `gcc` (build `main_code/` and `maslovCalculator/` with `-O2 -w`)
- Python 3, `pandas`, `openpyxl`
- EXORCISM-4 (external; not redistributed here — see the original EXORCISM
  distribution) for Step 2. Steps 3–7 do not require it; `results/esop/`
  already contains its output for every deposited benchmark.
- `pyzx` (only for `run_comparison.py`)

## Citation

If you use this repository, please cite the accompanying manuscript
(citation to be added on publication) rather than this repository directly.

## Contact

Mehul Shah — mehul@pdx.edu