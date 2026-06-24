#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "cube_types.h"
#include "cube_containment.h"
#include "cube_merge.h"

#define MAX_CUBES  2048
#define MAX_LINE   512

static int gNumInputs = 0;

// ------------------------------------------------------------
// Convert Cube → string of 0/1/- (lowest-bit is rightmost)
// `out` must be at least `n+1` bytes.
static void cubeToStr(const Cube *c, int n, char *out)
{
    if (n <= 0) {
        out[0] = '\0';
        return;
    }

    for (int i = 0; i < n; i++) {
        int pos = n - 1 - i;
        uint32_t bit = 1u << pos;

        out[i] = (c->mask & bit) ? '-' : ((c->bits & bit) ? '1' : '0');
    }
    out[n] = '\0';
}

// Write ESOP-format file from array of OutputCube.
void writeESOPFile(const char *filename, OutputCube *arr, int count, int n)
{
    FILE *fp = fopen(filename, "w");
    if (!fp) {
        fprintf(stderr, "ERROR: Could not create output file %s\n", filename);
        return;
    }

    // Header
    fprintf(fp, ".i %d\n", n);
    fprintf(fp, ".o 1\n");
    fprintf(fp, ".p %d\n", count);
    fprintf(fp, ".type eosops\n");

    // Write each cube (use VLA sized buffers)
    for (int k = 0; k < count; k++) {
        char gstr[n + 1];
        char cstr[n + 1];

        cubeToStr(&arr[k].g, n, gstr);
        cubeToStr(&arr[k].c, n, cstr);

        if (arr[k].hasNegative) {
            fprintf(fp, "%s %s 1\n", gstr, cstr);
        } else {
            fprintf(fp, "%s 1\n", gstr);
        }
    }

    fprintf(fp, ".e\n");
    fclose(fp);

    printf("\n[INFO] ESOP written to: %s\n", filename);
}

// OutputCube → "G" or "G C", written into `out` (caller must provide enough space)
static void outputCubeToStr(const OutputCube *oc, int n, char *out)
{
    char gStr[n + 1];
    cubeToStr(&oc->g, n, gStr);

    if (!oc->hasNegative) {
        snprintf(out, 256, "%s", gStr);
    } else {
        char cStr[n + 1];
        cubeToStr(&oc->c, n, cStr);
        snprintf(out, 256, "%s %s", gStr, cStr);
    }
}

// ------------------------------------------------------------
// Parse a line into an OutputCube
// Accepts either: "G 1" or "G C 1"
// Returns zeroed OutputCube on parse failure.
static OutputCube parseOutputCubeLine(const char *line, int n, int id)
{
    OutputCube oc;
    memset(&oc, 0, sizeof(oc));
    oc.id = id;
    oc.hasNegative = false;

    if (n <= 0) return oc;

    char buf[MAX_LINE];
    strncpy(buf, line, sizeof(buf));
    buf[sizeof(buf) - 1] = '\0';

    char gStr[128] = {0}, cStr[128] = {0};
    int val = 0;

    // Try to read up to three tokens: gStr [, cStr] [, val]
    int fields = sscanf(buf, "%127s %127s %d", gStr, cStr, &val);

    if (fields == 2) {
        // Format: "G 1" (second token is numeric)
        val = atoi(cStr);
        if (val != 1) return oc;

        Cube G = {0, 0};
        int len = (int)strlen(gStr);
        for (int i = 0; i < n && i < len; i++) {
            uint32_t bit = 1u << (n - 1 - i);
            if (gStr[i] == '-')      G.mask |= bit;
            else if (gStr[i] == '1') G.bits |= bit;
        }
        oc.g = G;
        oc.hasNegative = false;
    } else if (fields >= 3) {
        // Format: "G C 1"
        if (val != 1) return oc;

        Cube G = {0, 0}, C = {0, 0};
        int lenG = (int)strlen(gStr);
        int lenC = (int)strlen(cStr);

        for (int i = 0; i < n && i < lenG; i++) {
            uint32_t bit = 1u << (n - 1 - i);
            if (gStr[i] == '-')      G.mask |= bit;
            else if (gStr[i] == '1') G.bits |= bit;
        }
        for (int i = 0; i < n && i < lenC; i++) {
            uint32_t bit = 1u << (n - 1 - i);
            if (cStr[i] == '-')      C.mask |= bit;
            else if (cStr[i] == '1') C.bits |= bit;
        }

        oc.g = G;
        oc.c = C;
        oc.hasNegative = true;
    }

    return oc;
}

// ------------------------------------------------------------
// Print containment relationships (debug)
// ------------------------------------------------------------
static void printContainments(OutputCube *arr, int count, int n)
{
    for (int i = 0; i < count; i++) {
        for (int j = 0; j < count; j++) {
            if (i == j) continue;

            ContainmentResult cr =
                containment_relation(&arr[i], &arr[j], n);

            if (cr == CONTAINS_A_B) {
                char Ai[256], Aj[256];
                outputCubeToStr(&arr[i], n, Ai);
                outputCubeToStr(&arr[j], n, Aj);
                printf("%s (cube %d) contains %s (cube %d)\n",
                       Ai, arr[i].id, Aj, arr[j].id);
            }
        }
    }
}

// ------------------------------------------------------------
// Merge reduction driver
// Repeatedly finds best merges and replaces the pair with the merged cube.
// ------------------------------------------------------------
static void doMergeReduction(OutputCube *arr, int *pCount, int n)
{
    printf("\n--- Merge reduction ---\n");

    while (1) {
        int i = -1, j = -1;
        OutputCube R;

        if (!find_best_merge(arr, *pCount, n, &i, &j, &R))
            break;

        char Ai[256], Aj[256], Rstr[256];
        outputCubeToStr(&arr[i], n, Ai);
        outputCubeToStr(&arr[j], n, Aj);
        outputCubeToStr(&R,      n, Rstr);

        printf(" %s (cube %d) XOR %s (cube %d) → %s\n",
               Ai, arr[i].id, Aj, arr[j].id, Rstr);

        // Build new array without i,j and with R appended
        OutputCube tmp[MAX_CUBES];
        int k2 = 0;
        for (int k = 0; k < *pCount; k++) {
            if (k == i || k == j) continue;
            tmp[k2++] = arr[k];
        }
        if (k2 < MAX_CUBES) {
            tmp[k2++] = R;
        }

        memcpy(arr, tmp, k2 * sizeof(OutputCube));
        *pCount = k2;
    }

    printf("\n# Final cube count: %d\n", *pCount);
}

// ------------------------------------------------------------
// MAIN
// ------------------------------------------------------------
int main(int argc, char **argv)
{
    if (argc < 2) {
        printf("Usage: %s input.esop\n", argv[0]);
        return 1;
    }

    FILE *fp = fopen(argv[1], "r");
    if (!fp) {
        perror("open input");
        return 1;
    }

    OutputCube cubes[MAX_CUBES];
    int count = 0;
    char line[MAX_LINE];
    int startParsing = 0;

    while (fgets(line, sizeof(line), fp)) {
        char *p = line;
        while (*p == ' ' || *p == '\t') p++;

        if (*p == '\0' || *p == '#') continue;

        if (!strncmp(p, ".i", 2)) {
            // More robust parsing for .i <num>
            int tmp = 0;
            if (sscanf(p, ".i %d", &tmp) == 1) gNumInputs = tmp;
            continue;
        }
        if (!strncmp(p, ".o", 2)) continue;
        if (!strncmp(p, ".p", 2)) {
            startParsing = 1;
            continue;
        }
        if (!strncmp(p, ".type", 5)) {
            // accept .type esop or eosops, etc.
            if (strstr(p, "esop") || strstr(p, "eosop"))
                startParsing = 1;
            continue;
        }
        if (!strncmp(p, ".e", 2)) break;

        if (!startParsing) continue;

        // Parse cube line
        OutputCube oc = parseOutputCubeLine(p, gNumInputs, count);

        // Add into array if space remains (safe-guard)
        if (count < MAX_CUBES) {
            cubes[count++] = oc;
        } else {
            break;
        }
    }

    fclose(fp);

    printf("Loaded %d cubes.\n", count);

    // 1) Containment debug (prints relations)
    printContainments(cubes, count, gNumInputs);

    // 2) Merge reduction (in-place)
    doMergeReduction(cubes, &count, gNumInputs);

    // 3) Final ESOP (stdout)
    printf("\n# Final ESOP:\n");
    for (int i = 0; i < count; i++) {
        char buf[256];
        outputCubeToStr(&cubes[i], gNumInputs, buf);
        printf("%s 1\n", buf);
    }

    if (argc >= 3) {
        printf("\nWriting minimized ESOP to: %s\n", argv[2]);
        writeESOPFile(argv[2], cubes, count, gNumInputs);
    } else {
        printf("\nERROR: Missing output filename (argv[2]). Usage:\n");
        printf("  ./main <input.esop> <output.esops>\n");
    }

    return 0;
}