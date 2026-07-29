#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_LINE   512
#define MAX_TOKENS 32      /* FIX 3: was 4 - silently truncated wide factored terms */

/* ------------------------------------------------------------------
 * FIX 4 (judgement call): charge negated literals in the shared factor L.
 *   esop_cost() charges 2*negations on every cube, but the original
 *   pse_cost() charged them only on R1/R2, never on L - so a negative
 *   literal in a shared factor was free in the factorized form and paid
 *   for in the baseline. Set to 0 to restore the original behaviour.
 * ------------------------------------------------------------------ */
#define CHARGE_NEGATIONS_ON_L 1

/* ==================================================
 * MASLOV MODEL  (unchanged)
 * ================================================== */
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

/* ==================================================
 * T-COUNT MODEL
 *
 * FIX 1: the original returned 0 for k < 3, making a plain Toffoli free.
 *        A 2-control Toffoli has T-count 7 (Amy et al.; 4 is achievable
 *        with the Jones measurement-assisted construction - set
 *        TOFFOLI_T to 4 if that is the intended architecture).
 *        k = 0,1 are NOT/CNOT and are genuinely Clifford, so still 0.
 *
 *        This matters because factorization replaces wide gates with
 *        plain Toffolis, i.e. precisely the gate the original priced
 *        at zero - so T-count savings were inflated by the very
 *        mechanism being measured.
 * ================================================== */
#define TOFFOLI_T 7

int t_count(int k)
{
    if (k < 2)  return 0;          /* NOT / CNOT: Clifford, no T */
    if (k == 2) return TOFFOLI_T;  /* FIX 1: was 0               */
    return 8 * k - 16;             /* k >= 3: unchanged          */
}

/* ==================================================
 * HEADER FILTER  (unchanged)
 * ================================================== */
static int is_header_line(const char *s)
{
    if (!s || strlen(s) < 2) return 1;
    if (s[0] == '.') return 1;
    if (s[0] == '#') return 1;
    return 0;
}

/* ==================================================
 * COUNTERS  (unchanged)
 * ================================================== */
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

/* ==================================================
 * ESOP: one cube -> one multi-controlled Toffoli  (unchanged)
 * ================================================== */
int esop_cost(const char *cube)
{
    return toffoli_cost(count_fixed_controls(cube))
         + 2 * count_negations(cube);
}

int esop_tcount(const char *cube)
{
    return t_count(count_fixed_controls(cube));
}

/* ==================================================
 * PSE: L (R1 (+) R2 (+) ...)
 *
 * Realization: each residual Ri is written onto an ancilla in turn, so
 * the ancilla accumulates R1 (+) R2 (+) ...; the output gate is then
 * driven by L's literals TOGETHER WITH that ancilla.
 *
 * FIX 2: the output gate therefore has |L| + 1 controls, not |L|.
 *        The original charged toffoli_cost(|L|), omitting the ancilla.
 *        In the verified con1f1 circuit this gate is toff(b, d, o1) -> o,
 *        three controls, where the original billed two.
 *
 * With a single residual the term is L * (R)', which needs one NOT on
 * the ancilla to form the complement. The original produced that +1
 * accidentally, via toffoli_cost(count_fixed_controls("")) == 1; it is
 * now explicit.
 * ================================================== */
int pse_cost(const char *L, char residuals[][128], int n_res)
{
    int cost = toffoli_cost(count_fixed_controls(L) + 1);   /* FIX 2 */
    int negs = 0;

    for (int i = 0; i < n_res; i++)
    {
        cost += toffoli_cost(count_fixed_controls(residuals[i]));
        negs += count_negations(residuals[i]);
    }

    if (n_res == 1)
        cost += 1;                    /* NOT forming the complement (R)' */

#if CHARGE_NEGATIONS_ON_L
    negs += count_negations(L);       /* FIX 4 */
#endif

    return cost + 2 * negs;
}

int pse_tcount(const char *L, char residuals[][128], int n_res)
{
    int t = t_count(count_fixed_controls(L) + 1);           /* FIX 2 */

    for (int i = 0; i < n_res; i++)
        t += t_count(count_fixed_controls(residuals[i]));

    return t;
}

/* ==================================================
 * TOKENIZER
 * FIX 3: generalized to any number of residuals (was capped at 4 tokens,
 *        so a term with three or more residuals was silently truncated).
 * ================================================== */
int tokenize(char *line, char tokens[MAX_TOKENS][128])
{
    int n = 0;
    char *tok = strtok(line, " \t\n\r");

    while (tok && n < MAX_TOKENS)
    {
        strcpy(tokens[n++], tok);
        tok = strtok(NULL, " \t\n\r");
    }

    return n;
}

/* ==================================================
 * MAIN
 * ================================================== */
int main(int argc, char *argv[])
{
    FILE *fp;
    char line[MAX_LINE];

    int total_cost = 0;
    int total_t = 0;

    int esop_count = 0;
    int pse_count = 0;

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

        char t[MAX_TOKENS][128] = {{0}};
        int n = tokenize(copy, t);

        /* last token is the PLA output value; the rest are cubes */
        int n_cubes = n - 1;
        if (n_cubes <= 0)
            continue;

        if (n_cubes == 1)
        {
            int cost = esop_cost(t[0]);
            int tc   = esop_tcount(t[0]);

            total_cost += cost;
            total_t    += tc;
            esop_count++;

            printf("[ESOP] %s | C=%d T=%d\n", t[0], cost, tc);
        }
        else
        {
            char res[MAX_TOKENS][128];
            int n_res = n_cubes - 1;
            for (int i = 0; i < n_res; i++)
                strcpy(res[i], t[i + 1]);

            int cost = pse_cost(t[0], res, n_res);
            int tc   = pse_tcount(t[0], res, n_res);

            total_cost += cost;
            total_t    += tc;
            pse_count++;

            printf("[PSE ] %s (%d residual%s) | C=%d T=%d\n",
                   t[0], n_res, n_res == 1 ? "" : "s", cost, tc);
        }
    }

    fclose(fp);

    printf("\n========================\n");
    printf("ESOP terms : %d\n", esop_count);
    printf("PSE  terms : %d\n", pse_count);
    printf("TOTAL MASLOV COST = %d\n", total_cost);
    printf("TOTAL TCOUNT      = %d\n", total_t);
    printf("========================\n");

    return 0;
}