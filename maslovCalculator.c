#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Maslov Toffoli cost table for up to 9 controls
int get_toffoli_cost(int controls) {
    switch (controls) {
        case 0: return 1;
        case 1: return 1;
        case 2: return 5;
        case 3: return 13;
        case 4: return 29;
        case 5: return 61;
        case 6: return 125;
        case 7: return 253;
        case 8: return 509;
        case 9: return 1021;
        default: return 1021 + (controls - 9) * 1024; // rough estimate
    }
}

int count_zeros(const char *s) {
    int zeros = 0;
    for (int i = 0; s[i]; i++)
        if (s[i] == '0') zeros++;
    return zeros;
}

int count_controls(const char *s) {
    int count = 0;
    for (int i = 0; s[i]; i++)
        if (s[i] == '0' || s[i] == '1')
            count++;
    return count;
}

int main(int argc, char *argv[]) {
    FILE *fp;
    char line[256];
    int total_cost = 0;
    int start = 0;

    if (argc < 2) {
        printf("Usage: %s <input.pla>\n", argv[0]);
        return 1;
    }

    fp = fopen(argv[1], "r");
    if (!fp) {
        printf("Error opening file: %s\n", argv[1]);
        return 1;
    }

    while (fgets(line, sizeof(line), fp)) {
        // Skip until .type esop
        if (!start) {
            if (strstr(line, ".type esop") || strstr(line, ".type eosop")) {
                start = 1;
            }
            continue;
        }

        // Stop at .e
        if (line[0] == '.') break;

        // Remove newline
        line[strcspn(line, "\r\n")] = 0;
        if (strlen(line) == 0) continue;

        // Determine if it's simple or complex minterm
        char cube[128] = {0}, mask[128] = {0}, out[4] = {0};
        int parts = sscanf(line, "%s %s %s", cube, mask, out);

        // Simple minterm (no mask)
        if (parts == 2 || (parts == 3 && mask[0] == '\0')) {
            int ones = 0, zeros = 0;
            for (int i = 0; cube[i]; i++) {
                if (cube[i] == '1') ones++;
                else if (cube[i] == '0') zeros++;
            }
            int m = ones + zeros;
            if (m == 0) continue;

            int toffoli = get_toffoli_cost(m);
            int not_cost = 2 * zeros; // only zeros
            int qc = toffoli + not_cost; // no output NOT
            total_cost += qc;

            printf("%s -> m=%d, zeros=%d, QC=%d\n", cube, m, zeros, qc);
        }
        // Complex minterm (cube + mask + output)
        else if (parts >= 3) {
            int cube_zeros = 0;
            int cube_controls = count_controls(cube);
            cube_zeros = count_zeros(cube);

            int mask_controls = count_controls(mask);
            int mask_neg = count_zeros(mask);

            int total_controls = cube_controls + mask_controls;

            int output_not = (out[0] == '1') ? 1 : 0;

            int qc = get_toffoli_cost(total_controls) + 2 * (cube_zeros + mask_neg) + output_not;
            total_cost += qc;

            printf("%s %s %s -> Controls: %d, zeros: %d, mask_neg: %d, output_not: %d, QC=%d\n",
                   cube, mask, out, total_controls, cube_zeros, mask_neg, output_not, qc);
        }
    }

    fclose(fp);

    printf("\nTotal Maslov Quantum Cost = %d\n", total_cost);

    return 0;
}
