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
    return result.stdout + result.stderr


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
# MASLOV PARSER
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
# TCOUNT PARSER
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

    print("[WARN] T-count missing -> using 0")
    return 0


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

            # ==========================================
            # STEP 1: EXORCISM-4
            # ==========================================
            print("Running EXORCISM-4...")
            run_command(f'wine exorcism4.exe "{pla_path}"')

            generated_esop = os.path.splitext(pla_path)[0] + ".esop"

            if not os.path.exists(generated_esop):
                raise Exception("ESOP not generated")

            os.rename(generated_esop, esop_path)

            esop_out = run_command(f'{MASLOV_BIN} "{esop_path}"')
            esop_cost = extract_cost(esop_out)
            esop_t = extract_tcount(esop_out)

            # ==========================================
            # STEP 2: EOSOPS
            # ==========================================
            print("Running EOSOPS...")
            run_command(f'{ESOP_MIN_BIN} "{esop_path}" "{eosops_path}"')

            if not os.path.exists(eosops_path):
                raise Exception("EOSOPS not generated")

            eosops_out = run_command(f'{MASLOV_BIN} "{eosops_path}"')
            eosops_cost = extract_cost(eosops_out)
            eosops_t = extract_tcount(eosops_out)

            # ==========================================
            # STEP 3: FINAL PARSER
            # ==========================================
            print("Running Final Parser...")
            final_cmd = f'{FINAL_PARSER_BIN} "{eosops_path}"'
            parser_output = run_command(final_cmd)

            with open(final_path, "w") as f:
                f.write(parser_output)

            if not os.path.exists(final_path):
                raise Exception("FINAL file not generated")

            final_out = run_command(f'{MASLOV_BIN} "{final_path}"')
            final_cost = extract_cost(final_out)
            final_t = extract_tcount(final_out)

            # ==========================================
            # SAVINGS
            # ==========================================
            eosops_cost_saving = (
                (esop_cost - eosops_cost) / esop_cost * 100
                if esop_cost else 0
            )

            final_cost_saving = (
                (esop_cost - final_cost) / esop_cost * 100
                if esop_cost else 0
            )

            eosops_t_saving = (
                (esop_t - eosops_t) / esop_t * 100
                if esop_t else 0
            )

            final_t_saving = (
                (esop_t - final_t) / esop_t * 100
                if esop_t else 0
            )

            # ==========================================
            # STORE
            # ==========================================
            results.append({
                "Function": benchmark,
                "Inputs": inputs,

                "ESOP Cost": esop_cost,
                "EOSOPS Cost": eosops_cost,
                "EOSOPS Cost Saving (%)": round(eosops_cost_saving, 2),
                "Final Cost": final_cost,
                "Final Cost Saving (%)": round(final_cost_saving, 2),

                "ESOP T": esop_t,
                "EOSOPS T": eosops_t,
                "EOSOPS T Saving (%)": round(eosops_t_saving, 2),
                "Final T": final_t,
                "Final T Saving (%)": round(final_t_saving, 2)
            })

            print(f"ESOP Cost   : {esop_cost}")
            print(f"EOSOPS Cost : {eosops_cost}")
            print(f"FINAL Cost  : {final_cost}")
            print(f"ESOP T      : {esop_t}")
            print(f"EOSOPS T    : {eosops_t}")
            print(f"FINAL T     : {final_t}")

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
        "Function",
        "Inputs",
        "ESOP Cost",
        "EOSOPS Cost",
        "EOSOPS Cost Saving (%)",
        "Final Cost",
        "Final Cost Saving (%)"
    ]]

    tcount_df = df[[
        "Function",
        "Inputs",
        "ESOP T",
        "EOSOPS T",
        "EOSOPS T Saving (%)",
        "Final T",
        "Final T Saving (%)"
    ]]

    output_path = os.path.join(WORKDIR, RESULT_FILE)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        maslov_df.to_excel(writer, sheet_name="Maslov Cost", index=False)
        tcount_df.to_excel(writer, sheet_name="T-Count", index=False)

    print("\n====================================")
    print("DONE")
    print("====================================")
    print("Saved:", output_path)


if __name__ == "__main__":
    main()