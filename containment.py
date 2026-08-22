#!/usr/bin/env python3

import os
import time
from math import comb
from openpyxl import Workbook


# ==========================================================
# Paths
# ==========================================================

BENCHMARK_DIR = "/home/mehul/Mehul/gitrepos/Research_Project/benchmarks"

RESULT_DIR = "/home/mehul/Mehul/gitrepos/Research_Project/results"

OUTPUT_FILE = "pla_metrics.xlsx"



# ==========================================================
# Parse PLA / ESOP / EOSOPS / FINAL
# ==========================================================

def parse_file(filename):

    variables = 0
    declared_cubes = None
    literals = 0

    cubes = []

    inside = False


    with open(filename, "r") as f:

        for line in f:

            line = line.strip()


            if not line or line.startswith("#"):
                continue


            # Number of inputs
            if line.startswith(".i"):

                variables = int(line.split()[1])
                continue


            # Number of cubes
            if line.startswith(".p"):

                declared_cubes = int(line.split()[1])
                inside = True
                continue


            # Type line
            if line.startswith(".type"):

                inside = True
                continue


            # End
            if line == ".e":

                break


            if inside:

                tokens = line.split()


                if len(tokens) < 2:
                    continue


                # Ignore output bit
                input_cubes = tokens[:-1]


                for cube in input_cubes:

                    cubes.append(cube)

                    literals += (
                        cube.count("0")
                        +
                        cube.count("1")
                    )


    return {
        "variables": variables,
        "declared_cubes": declared_cubes,
        "literals": literals if cubes else "NA",
        "cubes": cubes
    }



# ==========================================================
# Weighted Shared Support Density (SSD)
# ==========================================================

def compute_ssd(cubes, variables):

    n = len(cubes)

    if n < 2 or variables == 0:
        return 0.0

    total_pairs = comb(n, 2)
    shared_total = 0

    for i in range(n):

        a = cubes[i]

        for j in range(i + 1, n):

            b = cubes[j]

            shared = 0

            for x, y in zip(a, b):

                if x != "-" and y != "-" and x == y:
                    shared += 1

            shared_total += shared

    return shared_total / (total_pairs * variables)


# ==========================================================
# Collect functions
# ==========================================================

def collect_extension(folder, extension):

    files = {}


    if not os.path.exists(folder):

        return files


    for root, _, filenames in os.walk(folder):

        for f in filenames:

            if f.endswith(extension):

                name = f[:-len(extension)]

                files[name] = os.path.join(root,f)


    return files



def collect_final(folder):

    files = {}


    if not os.path.exists(folder):

        return files


    ext = ".final.eosops"


    for root, _, filenames in os.walk(folder):

        for f in filenames:

            if f.endswith(ext):

                name = f[:-len(ext)]

                files[name] = os.path.join(root,f)


    return files



# ==========================================================
# Load all files
# ==========================================================


original_files = collect_extension(
    BENCHMARK_DIR,
    ".pla"
)


esop_files = collect_extension(
    os.path.join(RESULT_DIR,"esop"),
    ".esop"
)


final_files = collect_final(
    os.path.join(RESULT_DIR,"final_parser")
)



# ==========================================================
# Excel
# ==========================================================

wb = Workbook()

ws = wb.active

ws.title = "Metrics"



ws.append([

    "Benchmark",

    "Orig Cubes",
    "Orig Literals",
    "Orig SSD",

    "ESOP Cubes",
    "ESOP Literals",
    "ESOP SSD",

    "FINAL Cubes",
    "FINAL Literals",
    "FINAL SSD"

])



# ==========================================================
# Process benchmark by benchmark
# ==========================================================


def main():
    for name in sorted(original_files.keys()):

        print("\n")
        print("="*90)
        print("Benchmark:", name)
        print("="*90)

        row = []

        methods = [
            ("Original", original_files),
            ("ESOP", esop_files),
            ("EOSOPS", eosop_files),
            ("FINAL", final_files)
        ]

        for method, files in methods:
            if name not in files:
                print(method, ": missing")
                row.extend(["","",""])
                continue

            data = parse_file(files[name])

            ssd = compute_ssd(
                data["cubes"],
                data["variables"]
            )

            row.extend([
                data["declared_cubes"],
                data["literals"],
                round(ssd,6)
            ])

        ws.append(row)

    wb.save(OUTPUT_FILE)

    print("\nDONE")
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()