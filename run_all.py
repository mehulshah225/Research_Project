import os
import subprocess
import re
import pandas as pd
from containment import parse_file, compute_ssd

# ==================================================
# CONFIG
# ==================================================
WORKDIR = os.path.dirname(os.path.abspath(__file__))
RESULT_FILE = "results.xlsx"

ESOP_DIR = os.path.join(WORKDIR, "results/esop")
EOSOPS_DIR = os.path.join(WORKDIR, "results/eosops")
FINAL_DIR = os.path.join(WORKDIR, "results/final_parser")
LOG_DIR = os.path.join(WORKDIR, "results/logs")

os.makedirs(ESOP_DIR, exist_ok=True)
os.makedirs(EOSOPS_DIR, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

ESOP_MIN_BIN = os.path.join(WORKDIR, "esop_min")
MASLOV_BIN = os.path.join(WORKDIR, "maslov")
FINAL_PARSER_BIN = os.path.join(WORKDIR, "final_parser")


# ==================================================
# RUN COMMAND
# ==================================================
def run_command(cmd):
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=WORKDIR,
        capture_output=True,
        text=True
    )

    output = result.stdout + result.stderr

    if result.returncode != 0:
        print("\n[COMMAND FAILED]")
        print(cmd)
        print(output)
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {cmd}"
        )

    return output

class EquivalenceFailure(Exception):
    pass

# ==================================================
# EQUIVALENCE VERIFICATION
# ==================================================
VERIFY_SCRIPT = os.path.join(WORKDIR, "verify_equivalence.py")


def verify_equivalence(esop_path, final_path):
    """
    Verify that the final factorized representation is functionally
    equivalent to the EXORCISM ESOP.

    Raises an exception if equivalence fails.
    """

    if not os.path.exists(VERIFY_SCRIPT):
        raise Exception(
            f"Equivalence checker not found: {VERIFY_SCRIPT}"
        )

    if not os.path.exists(esop_path):
        raise Exception(
            f"ESOP file not found: {esop_path}"
        )

    if not os.path.exists(final_path):
        raise Exception(
            f"Final EOSOPS file not found: {final_path}"
        )

    result = subprocess.run(
        ["python", VERIFY_SCRIPT, esop_path, final_path],
        cwd=WORKDIR,
        capture_output=True,
        text=True
    )

    output = result.stdout + result.stderr

    print("\n========== EQUIVALENCE CHECK ==========")
    print(output.strip())
    print("=======================================\n")

    if result.returncode != 0:
        raise EquivalenceFailure(
            "EQUIVALENCE FAILURE — final circuit does not match ESOP"
        )

    return True

# ==================================================
# EXTRACT INPUT COUNT FROM PLA
# ==================================================
def extract_inputs(pla_path):
    with open(pla_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith(".i"):
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1])
    return None


# ==================================================
# GENERIC METRIC PARSER
#
# CHANGE 1: one parser for every metric, and it RAISES when a metric
# is missing instead of silently substituting a value.
#
# The old extract_tcount() did:
#       print("[WARN] T-count missing -> using 0"); return 0
# If the binary's output format ever drifts, that records T = 0 for
# every benchmark, and the savings column then reads a perfect 100%.
# A silent 0 is indistinguishable in the spreadsheet from a real
# result, which is exactly the failure mode that is hardest to catch.
# ==================================================
def extract_metric(output, patterns, label, default=None):
    for p in patterns:
        m = re.search(p, output, re.IGNORECASE)
        if m:
            return int(m.group(1))

    if default is not None:
        return default

    print(f"\n[DEBUG OUTPUT for missing '{label}']\n{output}")
    raise Exception(f"{label} missing from analyzer output")


def extract_cost(output):
    return extract_metric(output, [
        r"TOTAL\s*MASLOV\s*COST\s*=\s*(\d+)",
        r"MASLOV\s*COST\s*=\s*(\d+)",
        r"TOTAL\s*COST\s*=\s*(\d+)"
    ], "Maslov cost")


def extract_tcount(output):
    return extract_metric(
        output,
        [
            r"TOTAL\s*T[- ]?COUNT\s*=\s*(\d+)",
            r"TOTAL\s*TCOUNT\s*=\s*(\d+)",
            r"FINAL\s*TCOUNT\s*=\s*(\d+)"
        ],
        "T-count",
        default=None
    )


# ---- CHANGE 2: the new metrics --------------------------------------
def extract_ancilla_peak(output):
    return extract_metric(output, [r"ANCILLA\s*PEAK\s*=\s*(\d+)"],
                          "ancilla peak", default=None)


def extract_ancilla_total(output):
    return extract_metric(output, [r"ANCILLA\s*TOTAL\s*=\s*(\d+)"],
                          "ancilla total", default=None)


def extract_gates(output):
    return extract_metric(output, [r"TOTAL\s*GATES\s*=\s*(\d+)"],
                          "gate count", default=None)


def extract_max_controls(output):
    return extract_metric(output, [r"MAX\s*CONTROLS\s*=\s*(\d+)"],
                          "max controls", default=None)


def extract_histogram(output):
    m = re.search(r"GATE\s*HISTOGRAM\s*=\s*(.*)", output, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def analyze(path):

    out = run_command(f'{MASLOV_BIN} "{path}"')

    data = parse_file(path)

    return {
        "cost": extract_cost(out),
        "t": extract_tcount(out),
        "gates": extract_gates(out),
        "max_controls": extract_max_controls(out),
        "anc_peak": extract_ancilla_peak(out),
        "anc_total": extract_ancilla_total(out),
        "hist": extract_histogram(out),

        "cubes": data["declared_cubes"],
        "literals": data["literals"],
        "ssd": compute_ssd(
            data["cubes"],
            data["variables"]
        )
    }


# ==================================================
# FIND ALL PLA FILES
# ==================================================
def find_pla_files():
    files = []
    base = os.path.join(WORKDIR, "benchmarks")

    for root, _, fns in os.walk(base):
        for f in fns:
            if f.endswith(".pla"):
                files.append(os.path.join(root, f))

    return sorted(files)


# ==================================================
# MAIN
# ==================================================
def main():
    results = []
    pla_files = find_pla_files()

    print(f"Found {len(pla_files)} PLA files")

    for pla_path in pla_files:
        benchmark = os.path.splitext(os.path.basename(pla_path))[0]

        esop_path = os.path.join(ESOP_DIR, benchmark + ".esop")
        eosops_path = os.path.join(EOSOPS_DIR, benchmark + ".eosops")
        final_path = os.path.join(FINAL_DIR, benchmark + ".final.eosops")

        print("\n====================================")
        print(f"Processing: {benchmark}")
        print("====================================")

        try:
            inputs = extract_inputs(pla_path)
            original = analyze(pla_path)

            # ---------- REMOVE STALE OUTPUTS ----------
            for path in [esop_path, eosops_path, final_path]:
                if os.path.exists(path):
                    os.remove(path)

            # ---------- STEP 1: EXORCISM-4 ----------
            print("Running EXORCISM-4...")
            run_command(f' exorcism4.exe "{pla_path}"')

            generated_esop = os.path.splitext(pla_path)[0] + ".esop"
            if not os.path.exists(generated_esop):
                raise Exception("ESOP not generated")
            os.replace(generated_esop, esop_path)

            esop = analyze(esop_path)

            # ---------- STEP 2: EOSOPS ----------
            print("Running EOSOPS...")
            run_command(f'{ESOP_MIN_BIN} "{esop_path}" "{eosops_path}"')
            if not os.path.exists(eosops_path):
                raise Exception("EOSOPS not generated")

            eosops = analyze(eosops_path)

            # ---------- STEP 3: FINAL PARSER ----------
            print("Running Final Parser...")

            parser_output = run_command(
                f'{FINAL_PARSER_BIN} "{eosops_path}"'
            )

            with open(final_path, "w") as f:
                f.write(parser_output)

            if not os.path.exists(final_path):
                raise Exception("FINAL file not generated")


            # ---------- STEP 3.5: EQUIVALENCE CHECK ----------
            print("Verifying functional equivalence...")

            verify_equivalence(
                esop_path,
                final_path
            )

            print("EQUIVALENCE PASS")


            # ---------- STEP 4: FINAL ANALYSIS ----------
            final = analyze(final_path)

            # ---------- SAVINGS ----------
            
            def saving(a, b):
                if a is None or b is None:
                    return "NA"

                if a == 0:
                    return "NA"

                return (a - b) / a * 100

            def safe_round(x):
                return round(x, 2) if isinstance(x, (int, float)) else x
            
            def display_t(t):
                if t is None or t == 0:
                    return "NA"
                return t

            # CHANGE 3: sanity checks that would have caught the earlier
            # bad run before it reached the spreadsheet.
            # Sanity checks
            if (
                esop["cost"] is not None
                and final["cost"] is not None
                and final["cost"] > esop["cost"]
            ):
                print(f"  [CHECK] cost INCREASED: {esop['cost']} -> {final['cost']}")

            if (
                esop["t"] is not None
                and final["t"] is not None
                and final["t"] > esop["t"]
            ):
                print(f"  [CHECK] T-count INCREASED: {esop['t']} -> {final['t']}")

            if (
                esop["t"] is not None
                and final["t"] is not None
                and esop["t"] > 0
                and final["t"] == 0
            ):
                raise RuntimeError(
                    f"Invalid T-count result for {benchmark}: "
                    f"ESOP T={esop['t']}, FINAL T=0"
                )

            esop_ssd_save = saving(original["ssd"], esop["ssd"])
            final_ssd_save = saving(original["ssd"], final["ssd"])
            eosops_t_save = saving(esop["t"], eosops["t"])
            final_t_save = saving(esop["t"], final["t"])

            results.append({
                "Function": benchmark,
                "Inputs": inputs,

                "Equivalence": "PASS",

                "ESOP Cost": esop["cost"],
                "EOSOPS Cost": eosops["cost"],
                "EOSOPS Cost Saving (%)": safe_round(saving(esop["cost"], eosops["cost"])),
                "Final Cost": final["cost"],
                "Final Cost Saving (%)": safe_round(saving(esop["cost"], final["cost"])),

                "ESOP T": display_t(esop["t"]),
                "EOSOPS T": display_t(eosops["t"]),
                "Final T": display_t(final["t"]),

                "ESOP Gates": esop["gates"],
                "Final Gates": final["gates"],
                "ESOP Max Controls": esop["max_controls"],
                "Final Max Controls": final["max_controls"],
                "Ancilla Peak": final["anc_peak"],
                "Ancilla Total": final["anc_total"],
                "ESOP Histogram": esop["hist"],
                "Final Histogram": final["hist"],


                "Orig Cubes": original["cubes"],
                "Orig Literals": original["literals"],
                "Orig SSD": original["ssd"],
                "ESOP Cubes": esop["cubes"],
                "ESOP Literals": esop["literals"],
                "ESOP SSD": esop["ssd"],

                "Final Cubes": final["cubes"],
                "Final Literals": final["literals"],
                "Final SSD": final["ssd"],


                "Cost Saving (%)": round(
                    saving(esop["cost"], final["cost"]), 2
                ),

                "T Saving (%)": safe_round(
                    saving(esop["t"], final["t"])
                ),
                "EOSOPS T Saving (%)": (
                    safe_round(eosops_t_save)
                    if isinstance(eosops_t_save, (int, float))
                    else eosops_t_save
                ),

                "Final T Saving (%)": (
                    safe_round(final_t_save)
                    if isinstance(final_t_save, (int, float))
                    else final_t_save
                ),

                "ESOP SSD Saving (%)": (
                    safe_round(esop_ssd_save)
                    if isinstance(esop_ssd_save, (int, float))
                    else esop_ssd_save
                ),

                "SSD Saving (%)": (
                    safe_round(final_ssd_save)
                    if isinstance(final_ssd_save, (int, float))
                    else final_ssd_save
                ),


                "Gates delta":
                    esop["gates"] - final["gates"]
                    if esop["gates"] is not None and final["gates"] is not None
                    else "NA",

                "Max Controls delta": (
                    esop["max_controls"] - final["max_controls"]
                    if esop["max_controls"] is not None and final["max_controls"] is not None
                    else "NA"
                ),
            })

            print(f"ESOP Cost   : {esop['cost']}")
            print(f"EOSOPS Cost : {eosops['cost']}")
            print(f"FINAL Cost  : {final['cost']}")
            print(f"ESOP T      : {esop['t']}")
            print(f"EOSOPS T    : {eosops['t']}")
            print(f"FINAL T     : {final['t']}")
            print(f"Gates       : {esop['gates']} -> {final['gates']}")
            print(f"Max controls: {esop['max_controls']} -> {final['max_controls']}")
            print(f"Ancilla     : peak {final['anc_peak']}, total {final['anc_total']}")

        except EquivalenceFailure as e:
            print("\n" + "!" * 70)
            print(f"FATAL EQUIVALENCE FAILURE: {benchmark}")
            print("Reason:", e)
            print("Pipeline aborted.")
            print("!" * 70)
            raise

        except Exception as e:
            print(f"FAILED: {benchmark}")
            print("Reason:", e)

    # ==========================================
    # EXPORT TO EXCEL
    # ==========================================
    if not results:
        print("No results generated.")
        return

    df = pd.DataFrame(results)

    maslov_df = df[[
        "Function", "Inputs",
        "ESOP Cost", "EOSOPS Cost", "EOSOPS Cost Saving (%)",
        "Final Cost", "Final Cost Saving (%)"
    ]]

    tcount_df = df[[
        "Function", "Inputs",
        "ESOP T", "EOSOPS T", "EOSOPS T Saving (%)",
        "Final T", "Final T Saving (%)"
    ]]

    # CHANGE 4: new sheet for the structural metrics
    resource_df = df[[
        "Function", "Inputs",
        "ESOP Gates", "Final Gates",
        "ESOP Max Controls", "Final Max Controls",
        "Ancilla Peak", "Ancilla Total",
        "ESOP Histogram", "Final Histogram"
    ]]

    #Combining all metrics into a single sheet for convenience
    structure_df = df[[
        "Function",
        "Inputs",
        "Equivalence",

        "Orig Cubes",
        "Orig Literals",
        "Orig SSD",

        "ESOP Cubes",
        "ESOP Literals",
        "ESOP SSD",
        "ESOP SSD Saving (%)",

        "Final Cubes",
        "Final Literals",
        "Final SSD",

        "SSD Saving (%)"
    ]]

    output_path = os.path.join(WORKDIR, RESULT_FILE)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        maslov_df.to_excel(writer, sheet_name="Maslov Cost", index=False)
        tcount_df.to_excel(writer, sheet_name="T-Count", index=False)
        resource_df.to_excel(writer, sheet_name="Resources", index=False)
        structure_df.to_excel(writer, sheet_name="Structure", index=False)

    # ---------- run-level summary ----------
    print("\n====================================")
    print("SUMMARY")
    print("====================================")
    print(f"benchmarks found      : {len(pla_files)}")
    print(f"benchmarks verified   : {len(df)}")
    print(f"equivalence failures  : {len(pla_files) - len(df)}")
    print(f"median cost saving   : {df['Final Cost Saving (%)'].median():.2f}%")
    print(f"cost increased       : {(df['Final Cost'] > df['ESOP Cost']).sum()}")
    numeric_t = pd.to_numeric(df["Final T Saving (%)"], errors="coerce")
    print(f"median T saving      : {numeric_t.median():.2f}%")

    esop_t = pd.to_numeric(df["ESOP T"], errors="coerce")
    final_t = pd.to_numeric(df["Final T"], errors="coerce")

    print(f"T-count increased    : {(final_t > esop_t).sum()}")
    print(f"zero final T (bad)   : {((esop_t > 0) & (final_t == 0)).sum()}")
    print(f"max ancilla peak     : {df['Ancilla Peak'].max()}")
    print("Saved:", output_path)


if __name__ == "__main__":
    main()