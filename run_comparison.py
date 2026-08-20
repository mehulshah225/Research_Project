import argparse
import csv
import glob
import os
import statistics
import subprocess
import sys
import time
import multiprocessing as mp

import pyzx as zx


# ============================================================
# CONFIG
# ============================================================

QASM_DIR = "qasm"
PYZX_QASM_DIR = "qasm_pyzx"

ESOP_DIR = os.path.join("results", "esop")
FACT_DIR = os.path.join("results", "final_parser")


# ============================================================
# TARGETED LONG-RUN BENCHMARKS
# ============================================================

TARGET_BENCHMARKS = {
    "shor_modexp_2_mod21_bit0",
    "shor_modexp_2_mod21_bit1",
    "shor_modexp_5_mod33_bit0",
    "shor_modexp_5_mod33_bit1",

    "9sym_d_100",
    "sym10_d_100",
    "life_d_100",
    "max46_d_100",

    "majority9",
    "majority11",
    "ryy6_198",
}


# ============================================================
# DEFAULT SETTINGS
# ============================================================

# 600 = 10 minutes
# 28800 = 8 hours
TIMEOUT_SECONDS = 600

# None = no limit
MAX_BENCHMARKS = None


# ============================================================
# QASM GENERATION
# ============================================================

def generate_pyzx_qasm(source, output):
    """
    Convert an ESOP/factorized representation to QASM with all
    multi-controlled-X gates decomposed.

    PyZX 0.10.5 does not understand the OpenQASM 'mcx'
    instruction, so --decompose is mandatory here.
    """

    os.makedirs(
        os.path.dirname(output),
        exist_ok=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            "export_qasm.py",
            "--decompose",
            source,
        ],
        stdout=open(output, "w"),
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        raise RuntimeError(
            f"export_qasm.py failed for {source}:\n"
            f"{result.stderr}"
        )

    # --------------------------------------------------------
    # Safety check: PyZX 0.10.5 cannot parse MCX.
    # --------------------------------------------------------

    with open(output, "r") as fh:

        text = fh.read()

    if any(
        line.strip().lower().startswith("mcx ")
        for line in text.splitlines()
    ):

        raise RuntimeError(
            "MCX remains after --decompose"
        )


# ============================================================
# PYZX
# ============================================================

def load_circuit(path):

    with open(path, "r") as f:

        text = f.read()

    if any(
        line.strip().lower().startswith("mcx ")
        for line in text.splitlines()
    ):

        raise RuntimeError(
            "MCX remains in QASM"
        )

    return zx.Circuit.from_qasm(text)


def basic_tcount(path):

    c = load_circuit(path)

    return zx.tcount(
        c.to_basic_gates()
    )


def circuit_stats(path):
    """
    Return physical-circuit statistics after MCX decomposition.
    """

    c = load_circuit(path)

    basic = c.to_basic_gates()

    return {
        "qubits": c.qubits,
        "gates": len(c.gates),
        "basic_gates": len(basic.gates),
        "tcount": zx.tcount(basic),
    }


# ============================================================
# PYZX WORKER
# ============================================================

def pyzx_worker(path, queue):

    try:

        c = load_circuit(path)

        g = c.to_graph()

        zx.full_reduce(g)

        extracted = zx.extract_circuit(
            g.copy()
        )

        basic = extracted.to_basic_gates()

        t = zx.tcount(basic)

        queue.put(
            (
                "OK",
                {
                    "tcount": int(t),
                    "qubits": extracted.qubits,
                    "gates": len(extracted.gates),
                    "basic_gates": len(basic.gates),
                },
            )
        )

    except Exception as ex:

        queue.put(
            (
                "ERROR",
                f"{type(ex).__name__}: {ex}",
            )
        )


# ============================================================
# PYZX OPTIMIZATION WITH TIMEOUT
# ============================================================

def pyzx_optimize(path, timeout):

    ctx = mp.get_context("spawn")

    queue = ctx.Queue()

    p = ctx.Process(
        target=pyzx_worker,
        args=(path, queue),
    )

    start = time.time()

    p.start()

    p.join(timeout)

    elapsed = time.time() - start

    # --------------------------------------------------------
    # TIMEOUT
    # --------------------------------------------------------

    if p.is_alive():

        p.terminate()

        p.join(5)

        return (
            None,
            "TIMEOUT",
            elapsed,
        )

    # --------------------------------------------------------
    # PROCESS EXITED WITHOUT RESULT
    # --------------------------------------------------------

    if queue.empty():

        return (
            None,
            "NO_RESULT",
            elapsed,
        )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    status, value = queue.get()

    if status == "OK":

        return (
            value,
            "OK",
            elapsed,
        )

    return (
        None,
        value,
        elapsed,
    )


# ============================================================
# BENCHMARK DISCOVERY
# ============================================================

def find_benchmarks(
    only=None,
    targeted=False,
):

    files = sorted(
        glob.glob(
            os.path.join(
                ESOP_DIR,
                "*.esop",
            )
        )
    )

    result = []

    # --------------------------------------------------------
    # Determine benchmark filter
    # --------------------------------------------------------

    requested = None

    if only:

        requested = set(only)

    elif targeted:

        requested = TARGET_BENCHMARKS

    # --------------------------------------------------------
    # Discover benchmarks
    # --------------------------------------------------------

    for path in files:

        name = os.path.basename(path)[:-5]

        # If a filter is active, ignore everything else.

        if requested is not None:

            if name not in requested:

                continue

        fact = os.path.join(
            FACT_DIR,
            f"{name}.final.eosops",
        )

        if os.path.exists(fact):

            result.append(
                (
                    name,
                    path,
                    fact,
                )
            )

    # --------------------------------------------------------
    # Optional maximum benchmark limit
    # --------------------------------------------------------

    if MAX_BENCHMARKS is not None:

        result = result[:MAX_BENCHMARKS]

    return result


# ============================================================
# COMMAND LINE
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Compare baseline and EXORCISM-5 "
            "factorized circuits with PyZX."
        )
    )

    parser.add_argument(
        "--only",
        nargs="+",
        default=None,
        help=(
            "Run only the specified benchmark names. "
            "Example: "
            "--only shor_modexp_2_mod21_bit0"
        ),
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT_SECONDS,
        help=(
            "PyZX timeout in seconds. "
            "Example: --timeout 28800 for 8 hours."
        ),
    )

    parser.add_argument(
        "--targeted",
        action="store_true",
        help=(
            "Run the 11 targeted timeout benchmarks."
        ),
    )

    parser.add_argument(
        "--output-prefix",
        default="comparison",
        help=(
            "Prefix for output CSV files. "
            "Example: "
            "--output-prefix comparison_shor0"
        ),
    )

    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_args()

    timeout = args.timeout

    # --------------------------------------------------------
    # Benchmark selection
    # --------------------------------------------------------

    benchmarks = find_benchmarks(
        only=args.only,
        targeted=args.targeted,
    )

    print(
        f"Found {len(benchmarks)} benchmarks.",
        flush=True,
    )

    print(
        f"PyZX timeout: {timeout} seconds "
        f"({timeout / 3600:.1f} hours)",
        flush=True,
    )

    if args.only:

        print(
            "Mode: explicit --only selection",
            flush=True,
        )

    elif args.targeted:

        print(
            "Mode: targeted 11-benchmark run",
            flush=True,
        )

    else:

        print(
            "Mode: all discovered benchmarks",
            flush=True,
        )

    # --------------------------------------------------------
    # Warn if requested benchmarks were not found
    # --------------------------------------------------------

    if args.only:

        found_names = {
            name
            for name, _, _ in benchmarks
        }

        missing = [
            name
            for name in args.only
            if name not in found_names
        ]

        if missing:

            print(
                "WARNING: requested benchmarks not found:",
                flush=True,
            )

            for name in missing:

                print(
                    f"  {name}",
                    flush=True,
                )

    # --------------------------------------------------------
    # Directories
    # --------------------------------------------------------

    os.makedirs(
        PYZX_QASM_DIR,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    rows = []

    failures = []

    # ========================================================
    # BENCHMARK LOOP
    # ========================================================

    for index, (name, esop, fact) in enumerate(
        benchmarks,
        1,
    ):

        print()

        print(
            "=" * 70,
            flush=True,
        )

        print(
            f"[{index}/{len(benchmarks)}] {name}",
            flush=True,
        )

        try:

            # ====================================================
            # GENERATE PYZX-COMPATIBLE CIRCUITS
            # ====================================================

            base_qasm = os.path.join(
                PYZX_QASM_DIR,
                f"{name}_base.qasm",
            )

            fact_qasm = os.path.join(
                PYZX_QASM_DIR,
                f"{name}_fact.qasm",
            )

            print(
                "  generating decomposed baseline QASM...",
                flush=True,
            )

            generate_pyzx_qasm(
                esop,
                base_qasm,
            )

            print(
                "  generating decomposed factorized QASM...",
                flush=True,
            )

            generate_pyzx_qasm(
                fact,
                fact_qasm,
            )

            # ====================================================
            # A: DECOMPOSED BASELINE
            # ====================================================

            start = time.time()

            base_stats = circuit_stats(
                base_qasm
            )

            A = base_stats["tcount"]

            print(
                f"  A decomposed baseline = {A} "
                f"({time.time() - start:.1f}s)",
                flush=True,
            )

            print(
                f"    qubits={base_stats['qubits']} "
                f"gates={base_stats['gates']} "
                f"basic={base_stats['basic_gates']}",
                flush=True,
            )

            # ====================================================
            # C: DECOMPOSED FACTORIZED
            # ====================================================

            start = time.time()

            fact_stats = circuit_stats(
                fact_qasm
            )

            C = fact_stats["tcount"]

            print(
                f"  C decomposed factorized = {C} "
                f"({time.time() - start:.1f}s)",
                flush=True,
            )

            print(
                f"    qubits={fact_stats['qubits']} "
                f"gates={fact_stats['gates']} "
                f"basic={fact_stats['basic_gates']}",
                flush=True,
            )

            # ====================================================
            # B: BASELINE + PYZX
            # ====================================================

            print(
                f"  B PyZX baseline "
                f"(timeout={timeout}s)...",
                flush=True,
            )

            Bdata, status_b, time_b = pyzx_optimize(
                base_qasm,
                timeout,
            )

            if status_b != "OK":

                B = None

                print(
                    f"  B FAILED: {status_b} "
                    f"after {time_b:.1f}s",
                    flush=True,
                )

                failures.append(
                    (
                        name,
                        f"baseline_pyzx_{status_b}",
                        f"{time_b:.1f}",
                    )
                )

            else:

                B = Bdata["tcount"]

                print(
                    f"  B baseline+PyZX = {B} "
                    f"({time_b:.1f}s)",
                    flush=True,
                )

            # ====================================================
            # D: FACTORIZED + PYZX
            #
            # IMPORTANT:
            #
            # D is ALWAYS attempted, even if B timed out.
            # ====================================================

            print(
                f"  D PyZX factorized "
                f"(timeout={timeout}s)...",
                flush=True,
            )

            Ddata, status_d, time_d = pyzx_optimize(
                fact_qasm,
                timeout,
            )

            if status_d != "OK":

                D = None

                print(
                    f"  D FAILED: {status_d} "
                    f"after {time_d:.1f}s",
                    flush=True,
                )

                failures.append(
                    (
                        name,
                        f"factorized_pyzx_{status_d}",
                        f"{time_d:.1f}",
                    )
                )

            else:

                D = Ddata["tcount"]

                print(
                    f"  D factor+PyZX = {D} "
                    f"({time_d:.1f}s)",
                    flush=True,
                )

            # ====================================================
            # RESULT
            # ====================================================

            if B is not None and D is not None:

                print(
                    f"  RESULT: "
                    f"A={A} B={B} C={C} D={D}",
                    flush=True,
                )

                print(
                    f"  PyZX advantage of factorization: "
                    f"{B - D:+d} T gates",
                    flush=True,
                )

            else:

                print(
                    f"  PARTIAL RESULT: "
                    f"A={A} "
                    f"B={B} "
                    f"C={C} "
                    f"D={D}",
                    flush=True,
                )

            # ====================================================
            # SAVE ROW
            #
            # IMPORTANT:
            # Even partial results are saved.
            # ====================================================

            rows.append(
                (
                    name,

                    A,
                    B,
                    C,
                    D,

                    base_stats["qubits"],
                    fact_stats["qubits"],

                    base_stats["gates"],
                    fact_stats["gates"],

                    base_stats["basic_gates"],
                    fact_stats["basic_gates"],

                    (
                        Bdata["qubits"]
                        if Bdata is not None
                        else None
                    ),

                    (
                        Ddata["qubits"]
                        if Ddata is not None
                        else None
                    ),

                    (
                        Bdata["gates"]
                        if Bdata is not None
                        else None
                    ),

                    (
                        Ddata["gates"]
                        if Ddata is not None
                        else None
                    ),

                    time_b,
                    time_d,
                )
            )

        except Exception as ex:

            print(
                f"  ERROR: "
                f"{type(ex).__name__}: {ex}",
                flush=True,
            )

            failures.append(
                (
                    name,
                    type(ex).__name__,
                    str(ex),
                )
            )

    # ============================================================
    # CSV FILENAMES
    # ============================================================

    comparison_file = (
        f"{args.output_prefix}.csv"
    )

    failures_file = (
        f"{args.output_prefix}_failures.csv"
    )

    # ============================================================
    # CSV: COMPARISON RESULTS
    # ============================================================

    comparison_file = f"{args.output_prefix}.csv"

    with open(comparison_file, "w", newline="") as fh:

        w = csv.writer(fh)

        w.writerow(
            [
                "function",

                "decomposed_baseline",
                "baseline_pyzx",

                "decomposed_factorized",
                "factorized_pyzx",

                "baseline_qubits",
                "factorized_qubits",

                "baseline_gates",
                "factorized_gates",

                "baseline_basic_gates",
                "factorized_basic_gates",

                "baseline_pyzx_qubits",
                "factorized_pyzx_qubits",

                "baseline_pyzx_gates",
                "factorized_pyzx_gates",

                "baseline_pyzx_seconds",
                "factorized_pyzx_seconds",
            ]
        )

        w.writerows(rows)

    # ============================================================
    # CSV: FAILURES
    # ============================================================

    failures_file = f"{args.output_prefix}_failures.csv"

    with open(
        failures_file,
        "w",
        newline="",
    ) as fh:

        w = csv.writer(fh)

        w.writerow(
            [
                "function",
                "error_type",
                "error",
            ]
        )

        w.writerows(failures)

    # ============================================================
    # SUMMARY
    # ============================================================

    print()

    print(
        "=" * 80
    )

    print(
        "COMPARISON SUMMARY"
    )

    print(
        "=" * 80
    )

    print(
        f"Completed result rows : {len(rows)}"
    )

    print(
        f"PyZX failures         : {len(failures)}"
    )

    print(
        f"Total benchmarks      : {len(benchmarks)}"
    )

    if not rows:

        print(
            "No benchmark results."
        )

        return

    # ============================================================
    # ONLY FULL B/D COMPARISONS
    # ============================================================

    complete_rows = [
        r
        for r in rows
        if r[2] is not None
        and r[4] is not None
    ]

    print(
        f"Complete B/D comparisons : "
        f"{len(complete_rows)}"
    )

    # ============================================================
    # REDUCTIONS
    # ============================================================

    reduction_rows = [
        r
        for r in complete_rows
        if r[1] is not None
        and r[1] > 0
    ]

    if reduction_rows:

        pyzx_reduction = [
            100 * (1 - r[2] / r[1])
            for r in reduction_rows
        ]

        factor_reduction = [
            100 * (1 - r[3] / r[1])
            for r in reduction_rows
        ]

        combined_reduction = [
            100 * (1 - r[4] / r[1])
            for r in reduction_rows
        ]

        print()

        print(
            f"Nonzero-T comparisons : "
            f"{len(reduction_rows)}"
        )

        print()

        print(
            f"Median reduction, PyZX alone       : "
            f"{statistics.median(pyzx_reduction):.1f}%"
        )

        print(
            f"Median reduction, EXORCISM-5 alone : "
            f"{statistics.median(factor_reduction):.1f}%"
        )

        print(
            f"Median reduction, both combined    : "
            f"{statistics.median(combined_reduction):.1f}%"
        )

        # --------------------------------------------------------
        # Factorization advantage after PyZX
        # --------------------------------------------------------

        better = sum(
            r[4] < r[2]
            for r in complete_rows
        )

        equal = sum(
            r[4] == r[2]
            for r in complete_rows
        )

        worse = sum(
            r[4] > r[2]
            for r in complete_rows
        )

        print()

        print(
            f"Factorization helps after PyZX : "
            f"{better}/{len(complete_rows)}"
        )

        print(
            f"Equal                          : "
            f"{equal}/{len(complete_rows)}"
        )

        print(
            f"Worse                          : "
            f"{worse}/{len(complete_rows)}"
        )

    else:

        print()

        print(
            "No complete nonzero-T comparisons "
            "available for reduction statistics."
        )

    # ============================================================
    # PARTIAL RESULTS
    # ============================================================

    partial_rows = [
        r
        for r in rows
        if r[2] is None
        or r[4] is None
    ]

    if partial_rows:

        print()

        print(
            "Partial results:"
        )

        for r in partial_rows:

            name = r[0]
            A = r[1]
            B = r[2]
            C = r[3]
            D = r[4]

            print(
                f"  {name}: "
                f"A={A}, B={B}, C={C}, D={D}"
            )

    # ============================================================
    # FILES
    # ============================================================

    print()

    print(
        "Files:"
    )

    print(
        f"  {comparison_file}"
    )

    print(
        f"  {failures_file}"
    )

    print(
        f"  {PYZX_QASM_DIR}\\"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    mp.freeze_support()

    main()