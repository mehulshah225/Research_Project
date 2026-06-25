import os
import subprocess
import re
import pandas as pd

# ==================================================
# CONFIG
# ==================================================
WORKDIR = os.path.dirname(os.path.abspath(__file__))
RESULT_FILE = "results.xlsx"

# Output directories (clean research structure)
ESOP_DIR = os.path.join(WORKDIR, "results/esop")
EOSOPS_DIR = os.path.join(WORKDIR, "results/eosops")
LOG_DIR = os.path.join(WORKDIR, "results/logs")

os.makedirs(ESOP_DIR, exist_ok=True)
os.makedirs(EOSOPS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Binaries (from Makefile)
ESOP_MIN_BIN = os.path.join(WORKDIR, "esop_min")
MASLOV_BIN = os.path.join(WORKDIR, "maslov")


# ==================================================
# COMMAND RUNNER
# ==================================================
def run_command(cmd):
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=WORKDIR,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"\nCommand failed: {cmd}")
        print(result.stderr)

    return result.stdout + result.stderr


# ==================================================
# MASLOV COST PARSER
# ==================================================
def extract_cost(output):
    match = re.search(r"TOTAL MASLOV COST\s*=\s*(\d+)", output)
    if match:
        return int(match.group(1))
    raise Exception("Could not find Maslov cost in output.")


# ==================================================
# COUNT ESOP TERMS
# ==================================================
def count_terms(filepath):
    count = 0
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("."):
                continue
            count += 1
    return count


# ==================================================
# FIND ALL PLA FILES (RECURSIVE)
# ==================================================
def find_pla_files():
    pla_files = []

    for root, _, files in os.walk(os.path.join(WORKDIR, "benchmarks")):
        for f in files:
            if f.endswith(".pla"):
                pla_files.append(os.path.join(root, f))

    return sorted(pla_files)


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

        print("\n====================================")
        print(f"Processing: {benchmark}")
        print("====================================")

        try:
            # ------------------------------------------
            # STEP 1: PLA -> ESOP (EXORCISM-4)
            # ------------------------------------------
            print("Running EXORCISM-4...")

            run_command(f'wine exorcism4.exe "{os.path.abspath(pla_path)}"')

            generated_esop = os.path.splitext(pla_path)[0] + ".esop"

            if not os.path.exists(generated_esop):
                raise Exception(f"ESOP not generated: {generated_esop}")

            os.rename(generated_esop, esop_path)

            # ------------------------------------------
            # STEP 2: ESOP -> EOSOPS
            # ------------------------------------------
            print("Running ESOP postprocessor...")

            run_command(f'{ESOP_MIN_BIN} "{esop_path}" "{eosops_path}"')

            if not os.path.exists(eosops_path):
                raise Exception(f"EOSOPS not created: {eosops_path}")

            # ------------------------------------------
            # STEP 3: Term counts
            # ------------------------------------------
            esop_terms = count_terms(esop_path)
            eosops_terms = count_terms(eosops_path)

            # ------------------------------------------
            # STEP 4: Maslov cost
            # ------------------------------------------
            print("Computing ESOP cost...")
            esop_output = run_command(f'{MASLOV_BIN} "{esop_path}"')
            esop_cost = extract_cost(esop_output)

            print("Computing EOSOPS cost...")
            eosops_output = run_command(f'{MASLOV_BIN} "{eosops_path}"')
            eosops_cost = extract_cost(eosops_output)

            # ------------------------------------------
            # STEP 5: Savings
            # ------------------------------------------
            savings = ((esop_cost - eosops_cost) / esop_cost) * 100

            results.append({
                "Benchmark": benchmark,
                "ESOP Terms": esop_terms,
                "EOSOPS Terms": eosops_terms,
                "ESOP Cost": esop_cost,
                "EOSOPS Cost": eosops_cost,
                "Savings %": round(savings, 2)
            })

            print(f"ESOP Terms   : {esop_terms}")
            print(f"EOSOPS Terms : {eosops_terms}")
            print(f"ESOP Cost    : {esop_cost}")
            print(f"EOSOPS Cost  : {eosops_cost}")
            print(f"Savings      : {savings:.2f}%")

        except Exception as e:
            print(f"FAILED: {benchmark}")
            print("Reason:", e)

    # ==================================================
    # EXPORT RESULTS
    # ==================================================
    if not results:
        print("No successful runs.")
        return

    df = pd.DataFrame(results)
    df = df.sort_values(by="Savings %", ascending=False)

    avg_savings = df["Savings %"].mean()
    best_row = df.iloc[0]

    summary = pd.DataFrame([{
        "Benchmark": "AVERAGE",
        "ESOP Terms": "",
        "EOSOPS Terms": "",
        "ESOP Cost": "",
        "EOSOPS Cost": "",
        "Savings %": round(avg_savings, 2)
    }])

    final_df = pd.concat([df, summary], ignore_index=True)

    output_path = os.path.join(WORKDIR, RESULT_FILE)
    final_df.to_excel(output_path, index=False)

    print("\n====================================")
    print("SUMMARY")
    print("====================================")
    print(f"Average Savings : {avg_savings:.2f}%")
    print(f"Best Benchmark  : {best_row['Benchmark']}")
    print(f"Best Reduction  : {best_row['Savings %']}%")
    print(f"Excel saved to  : {output_path}")


if __name__ == "__main__":
    main()