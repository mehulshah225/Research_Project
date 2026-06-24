#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Maslov cost model (consistent with paper)
int toffoli_cost(int controls) {
    switch (controls) {
        case 0: return 1;   // NOT
        case 1: return 1;   // CNOT
        case 2: return 5;
        case 3: return 13;
        case 4: return 29;
        case 5: return 61;
        case 6: return 125;
        case 7: return 253;
        case 8: return 509;
        default: return 1021 + (controls - 9) * 1024;
    }
}

int count_fixed_controls(const char *s) {
    int c = 0;
    for (int i = 0; s[i]; i++)
        if (s[i] == '0' || s[i] == '1')
            c++;
    return c;
}

int count_negations(const char *s) {
    int n = 0;
    for (int i = 0; s[i]; i++)
        if (s[i] == '0')
            n++;
    return n;
}

// PSE cost model
int pse_cost(const char *P, const char *Q) {
    int cP = count_fixed_controls(P);
    int cQ = count_fixed_controls(Q);
    int nQ = count_negations(Q);

    return toffoli_cost(cP) + toffoli_cost(cQ) + 2 * nQ;
}

// ESOP cost model
int esop_cost(const char *cube) {
    int controls = count_fixed_controls(cube);
    return toffoli_cost(controls);
}

int main(int argc, char *argv[]) {
    FILE *fp;
    char line[256];
    int total_cost = 0;
    int mode = 0; // 1 after .type

    if (argc < 2) {
        printf("Usage: %s <input.pla>\n", argv[0]);
        return 1;
    }

    fp = fopen(argv[1], "r");
    if (!fp) {
        printf("Error opening file\n");
        return 1;
    }

    while (fgets(line, sizeof(line), fp)) {

        if (strstr(line, ".type")) {
            mode = 1;
            continue;
        }

        if (!mode) continue;
        if (line[0] == '.' && line[1] == 'e') break;

        char a[128] = {0}, b[128] = {0}, c[4] = {0};
        int parts = sscanf(line, "%s %s %s", a, b, c);

        // ESOP cube
        if (parts == 2 || (parts == 3 && strlen(b) == 0)) {
            int cost = esop_cost(a);
            total_cost += cost;
            printf("ESOP: %s -> %d\n", a, cost);
        }

        // PSE term
        else if (parts >= 2) {
            int cost = pse_cost(a, b);
            total_cost += cost;
            printf("PSE: %s %s -> %d\n", a, b, cost);
        }
    }

    fclose(fp);

    printf("\nTOTAL MASLOV COST = %d\n", total_cost);
    return 0;
}
