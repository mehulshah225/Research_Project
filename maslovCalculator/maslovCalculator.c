#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_LINE 256

// ==================================================
// MASLOV MODEL
// ==================================================
int toffoli_cost(int controls)
{
    switch (controls)
    {
        case 0: return 1;
        case 1: return 1;
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

// ==================================================
// HEADER FILTER
// ==================================================
static int is_header_line(const char *s)
{
    if (!s || strlen(s) < 2) return 1;
    if (s[0] == '.') return 1;
    if (s[0] == '#') return 1;
    return 0;
}

// ==================================================
// COUNTERS
// ==================================================
int count_fixed_controls(const char *s)
{
    int c = 0;
    for (int i = 0; s[i]; i++)
        if (s[i] == '0' || s[i] == '1')
            c++;
    return c;
}

int count_negations(const char *s)
{
    int n = 0;
    for (int i = 0; s[i]; i++)
        if (s[i] == '0')
            n++;
    return n;
}

// ==================================================
// T-COUNT MODEL
// ==================================================
int t_count(int k)
{
    if (k < 3) return 0;
    return 8 * k - 16;
}

// ==================================================
// COST MODELS
// ==================================================
int esop_cost(const char *cube)
{
    return toffoli_cost(count_fixed_controls(cube))
         + 2 * count_negations(cube);
}

int esop_tcount(const char *cube)
{
    return t_count(count_fixed_controls(cube));
}

int pse_cost(const char *L, const char *R1, const char *R2)
{
    return toffoli_cost(count_fixed_controls(L))
         + toffoli_cost(count_fixed_controls(R1))
         + toffoli_cost(count_fixed_controls(R2))
         + 2 * (count_negations(R1) + count_negations(R2));
}

int pse_tcount(const char *L, const char *R1, const char *R2)
{
    return t_count(count_fixed_controls(L))
         + t_count(count_fixed_controls(R1))
         + t_count(count_fixed_controls(R2));
}

// ==================================================
// TOKENIZER
// ==================================================
int tokenize(char *line, char tokens[4][128])
{
    int n = 0;
    char *tok = strtok(line, " \t\n");

    while (tok && n < 4)
    {
        strcpy(tokens[n++], tok);
        tok = strtok(NULL, " \t\n");
    }

    return n;
}

// ==================================================
// MAIN
// ==================================================
int main(int argc, char *argv[])
{
    FILE *fp;
    char line[MAX_LINE];

    int total_cost = 0;
    int total_t = 0;

    int esop_count = 0;
    int eosops_count = 0;
    int final_count = 0;

    if (argc < 2)
    {
        printf("Usage: %s <file>\n", argv[0]);
        return 1;
    }

    fp = fopen(argv[1], "r");
    if (!fp)
    {
        perror("file");
        return 1;
    }

    while (fgets(line, sizeof(line), fp))
    {
        if (line[0] == '.' && line[1] == 'e')
            break;

        if (is_header_line(line))
            continue;

        char copy[MAX_LINE];
        strcpy(copy, line);

        char t[4][128] = {0};
        int n = tokenize(copy, t);

        if (n <= 0)
            continue;

        // ==================================================
        // ESOP (single cube)
        // ==================================================
        if (n == 2)
        {
            int cost = esop_cost(t[0]);
            int tc   = esop_tcount(t[0]);

            total_cost += cost;
            total_t += tc;
            esop_count++;

            printf("[ESOP ] %s | C=%d T=%d\n", t[0], cost, tc);
        }

        // ==================================================
        // EOSOPS (2 cubes)
        // ==================================================
        else if (n == 3)
        {
            int cost = pse_cost(t[0], t[1], "");
            int tc   = pse_tcount(t[0], t[1], "");

            total_cost += cost;
            total_t += tc;
            eosops_count++;

            printf("[EOSOPS] %s %s | C=%d T=%d\n",
                   t[0], t[1], cost, tc);
        }

        // ==================================================
        // FINAL (3 cubes)
        // ==================================================
        else
        {
            int cost = pse_cost(t[0], t[1], t[2]);
            int tc   = pse_tcount(t[0], t[1], t[2]);

            total_cost += cost;
            total_t += tc;
            final_count++;

            printf("[FINAL ] %s %s %s | C=%d T=%d\n",
                   t[0], t[1], t[2], cost, tc);
        }
    }

    fclose(fp);

    // ==================================================
    // SUMMARY
    // ==================================================
    printf("\n========================\n");
    printf("ESOP   terms : %d\n", esop_count);
    printf("EOSOPS terms : %d\n", eosops_count);
    printf("FINAL  terms : %d\n", final_count);
    printf("TOTAL MASLOV COST = %d\n", total_cost);
    printf("TOTAL TCOUNT      = %d\n", total_t);
    printf("========================\n");

    return 0;
}