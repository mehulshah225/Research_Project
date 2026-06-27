import os
import subprocess
import re
import pandas as pd

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
# RUN COMMAND (SAFE)
# ==================================================
def run_command(cmd):
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=WORKDIR,
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr


# ==================================================
# MASLOV PARSER (ROBUST)
# ==================================================
def extract_cost(output):
    patterns = [
        r"TOTAL\s*MASLOV\s*COST\s*=\s*(\d+)",
        r"MASLOV\s*COST\s*=\s*(\d+)",
        r"TOTAL\s*COST\s*=\s*(\d+)"
    ]

    for p in patterns:
        m = re.search(p, output, re.IGNORECASE)
        if m:
            return int(m.group(1))

    print("\n[DEBUG MASLOV OUTPUT]\n", output)
    raise Exception("Maslov cost missing")


# ==================================================
# T-COUNT PARSER (ROBUST)
# ==================================================
def extract_tcount(output):
    patterns = [
        r"TOTAL\s*T[- ]?COUNT\s*=\s*(\d+)",
        r"TOTAL\s*TCOUNT\s*=\s*(\d+)",
        r"FINAL\s*TCOUNT\s*=\s*(\d+)",
        r"TCOUNT\s*=\s*(\d+)"
    ]

    for p in patterns:
        m = re.search(p, output, re.IGNORECASE)
        if m:
            return int(m.group(1))

    print("[WARN] T-count missing → using 0")
    return 0


# ==================================================
# COUNT ESOP TERMS
# ==================================================
def count_terms(filepath):
    c = 0
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("."):
                continue
            c += 1
    return c


# ==================================================
# FIND BENCHMARKS
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
# MAIN PIPELINE
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
            # ==================================================
            # STEP 1: EXORCISM-4
            # ==================================================
            print("Running EXORCISM-4...")

            run_command(f'wine exorcism4.exe "{pla_path}"')

            generated_esop = os.path.splitext(pla_path)[0] + ".esop"

            if not os.path.exists(generated_esop):
                raise Exception("ESOP not generated")

            os.rename(generated_esop, esop_path)

            esop_out = run_command(f'{MASLOV_BIN} "{esop_path}"')
            esop_cost = extract_cost(esop_out)
            esop_t = extract_tcount(esop_out)

            # ==================================================
            # STEP 2: EOSOPS
            # ==================================================
            print("Running ESOP postprocessor...")

            run_command(f'{ESOP_MIN_BIN} "{esop_path}" "{eosops_path}"')

            if not os.path.exists(eosops_path):
                raise Exception("EOSOPS not generated")

            eosops_out = run_command(f'{MASLOV_BIN} "{eosops_path}"')
            eosops_cost = extract_cost(eosops_out)
            eosops_t = extract_tcount(eosops_out)

            # ==================================================
            # STEP 3: FINAL PARSER
            # ==================================================
            print("Running Final Parser...")

            final_cmd = f'{FINAL_PARSER_BIN} "{eosops_path}"'
            final_out = run_command(final_cmd)

            # write output manually (because program prints to stdout)
            with open(final_path, "w") as f:
                f.write(final_out)

            if not os.path.exists(final_path):
                raise Exception("FINAL not generated")

            final_out = run_command(f'{MASLOV_BIN} "{final_path}"')
            final_cost = extract_cost(final_out)
            final_t = extract_tcount(final_out)

            # ==================================================
            # SAVINGS (vs ESOP baseline)
            # ==================================================
            eosops_savings = ((esop_cost - eosops_cost) / esop_cost) * 100
            final_savings = ((esop_cost - final_cost) / esop_cost) * 100

            # ==================================================
            # STORE RESULTS
            # ==================================================
            results.append({
                "Benchmark": benchmark,

                "ESOP Cost": esop_cost,
                "ESOP T": esop_t,

                "EOSOPS Cost": eosops_cost,
                "EOSOPS T": eosops_t,
                "EOSOPS Savings %": round(eosops_savings, 2),

                "FINAL Cost": final_cost,
                "FINAL T": final_t,
                "FINAL Savings %": round(final_savings, 2),
            })

            print(f"ESOP Cost   : {esop_cost}")
            print(f"EOSOPS Cost : {eosops_cost}")
            print(f"FINAL Cost  : {final_cost}")
            print(f"FINAL T     : {final_t}")

        except Exception as e:
            print(f"FAILED: {benchmark}")
            print("Reason:", e)

    # ==================================================
    # EXPORT
    # ==================================================
    if not results:
        print("No results generated.")
        return

    df = pd.DataFrame(results)
    output_path = os.path.join(WORKDIR, RESULT_FILE)

    df.to_excel(output_path, index=False)

    print("\n====================================")
    print("DONE")
    print("====================================")
    print("Saved:", output_path)


if __name__ == "__main__":
    main()