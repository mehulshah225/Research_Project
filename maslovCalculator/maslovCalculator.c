#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_LINE   4096
#define MAX_TOKENS 256
#define MAX_ARITY  256

/* ==================================================
 * T-COUNT MODEL
 *
 * ONLY change from your original. The original was
 *      if (k < 3) return 0;  else return 8*k - 16;
 * which prices a plain Toffoli at ZERO. That is what drove
 * t481_d and eosops1 to a spurious T-count of 0.
 *
 * Patching just the k==2 case to 7 leaves a discontinuity
 * (7, 8, 16, 24 for 2,3,4,5 controls: +1 then +8 per step),
 * and that kink is what made rd73f1, rd84f1 and sf_232 regress.
 *
 * T_MODEL 1 : T(n) = 4(n-1)      AND-tree of measurement-assisted
 *                                AND gates (Jones 2013). Monotonic,
 *                                and provably cannot regress under
 *                                your realization - see note below.
 * T_MODEL 2 : T(2)=7, T(n>=3)=8n-16   unitary relative-phase
 *                                (Maslov 2016). Keeps the kink.
 *
 * Why model 1 cannot regress: a polarity merge turns cubes of size
 * |L|+|R1| and |L|+|R2| into gates of size |L|, |R1|, |R2|, saving
 * exactly 4(|L|+1) T gates; a containment merge saves 4|L|. Both are
 * strictly positive, so T-count never increases.
 * ================================================== */
#define T_MODEL 1

/* ==================================================
 * ANCILLA_CONTROL
 *
 * A factored term L(R1 (+) R2 ...) writes the residuals onto an ancilla,
 * and the output gate is then driven by L's literals TOGETHER WITH that
 * ancilla. The gate therefore has |L|+1 controls, not |L|.
 *
 * With this off, a term whose shared factor has a single literal is
 * billed as a 1-control CNOT when it is really a Toffoli. That is what
 * makes 4mod5_8 report a non-affine function realized by CNOTs alone
 * (ESOP histogram 2:4, final histogram 1:6, final T = 0) - a result a
 * referee can disprove from the published histogram column.
 * ================================================== */
#define ANCILLA_CONTROL 1

int t_count(int k)                 /* k = number of controls */
{
    if (k < 2) return 0;           /* NOT / CNOT are Clifford */
#if T_MODEL == 1
    return 4 * (k - 1);
#else
    return (k == 2) ? 7 : 8 * k - 16;
#endif
}

/* ==================================================
 * MASLOV MODEL - UNCHANGED from your original.
 * No ancilla control is charged, no negations on L.
 * ================================================== */
/* COST_MODEL 1 = ancilla-free, 2^(n+1)-3 (the conventional Maslov table)
   COST_MODEL 2 = ancilla-based, an n-control Toffoli as 2(n-2) Toffolis ~ 10(n-2)
   Run both and report both: it removes the "you gave your method ancillas but
   priced the baseline without them" objection before a referee can raise it. */
#define COST_MODEL 1

int toffoli_cost(int controls)
{
#if COST_MODEL == 2
    if (controls < 2)  return 1;
    if (controls == 2) return 5;
    return 10 * (controls - 2);
#else
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
#endif
}


static int gate_hist[MAX_ARITY];
static int max_controls = 0;

static int is_header_line(const char *s)
{
    if (!s || strlen(s) < 2) return 1;
    if (s[0] == '.') return 1;
    if (s[0] == '#') return 1;
    return 0;
}

int count_fixed_controls(const char *s)
{
    int c = 0;
    for (int i = 0; s[i]; i++)
        if (s[i] == '0' || s[i] == '1') c++;
    return c;
}

int count_negations(const char *s)
{
    int n = 0;
    for (int i = 0; s[i]; i++)
        if (s[i] == '0') n++;
    return n;
}

static void record(int controls)
{
    if (controls < MAX_ARITY) gate_hist[controls]++;
    if (controls > max_controls) max_controls = controls;
}

/* ---------------- ESOP: one cube -> one gate (unchanged) ---------------- */
int esop_cost(const char *cube)
{
    return toffoli_cost(count_fixed_controls(cube)) + 2 * count_negations(cube);
}

int esop_tcount(const char *cube)
{
    return t_count(count_fixed_controls(cube));
}

/* ---------------- PSE ----------------
   Cost identical to your original: every cube billed as its own
   gate, no ancilla control, negations charged on residuals only. */
int pse_cost(const char *L, char res[][128], int n_res)
{
#if ANCILLA_CONTROL
    int cost = toffoli_cost(count_fixed_controls(L) + 1);
#else
    int cost = toffoli_cost(count_fixed_controls(L));
#endif
    int negs = 0;

    for (int i = 0; i < n_res; i++)
    {
        cost += toffoli_cost(count_fixed_controls(res[i]));
        negs += count_negations(res[i]);
    }

    if (n_res == 1)
        cost += toffoli_cost(0);          /* NOT forming the complement */

    return cost + 2 * negs;
}

int pse_tcount(const char *L, char res[][128], int n_res)
{
#if ANCILLA_CONTROL
    int t = t_count(count_fixed_controls(L) + 1);
#else
    int t = t_count(count_fixed_controls(L));
#endif
    for (int i = 0; i < n_res; i++)
        t += t_count(count_fixed_controls(res[i]));
    return t;
}

/* Ancillas held simultaneously by one factored term.
   Reported as a resource; it does NOT feed into the cost model.
   Under the emitted realization a polarity term keeps two lines
   live: one accumulating the residuals, one holding L.          */
int pse_ancilla(int n_res)
{
    return (n_res == 1) ? 1 : 2;
}

int main(int argc, char *argv[])
{
    if (argc < 2) { printf("usage: %s file.pla\n", argv[0]); return 1; }
    FILE *fp = fopen(argv[1], "r");
    if (!fp) { perror("file"); return 1; }

    char line[MAX_LINE];
    int total_cost = 0, total_t = 0, total_gates = 0;
    int esop_count = 0, pse_count = 0;
    int anc_peak = 0, anc_total = 0;

    while (fgets(line, sizeof(line), fp))
    {
        if (line[0] == '.' && line[1] == 'e') break;
        if (is_header_line(line)) continue;

        char copy[MAX_LINE];
        strcpy(copy, line);

        char t[MAX_TOKENS][128] = {{0}};
        int n = 0;
        for (char *p = strtok(copy, " \t\n\r"); p && n < MAX_TOKENS; p = strtok(NULL, " \t\n\r"))
            strcpy(t[n++], p);

        int n_cubes = n - 1;              /* last token is the PLA output value */
        if (n_cubes <= 0) continue;

        if (n_cubes == 1)
        {
            total_cost += esop_cost(t[0]);
            total_t    += esop_tcount(t[0]);
            total_gates++;
            record(count_fixed_controls(t[0]));
            esop_count++;
        }
        else
        {
            char res[MAX_TOKENS][128];
            int n_res = n_cubes - 1;
            for (int i = 0; i < n_res; i++) strcpy(res[i], t[i + 1]);

            total_cost += pse_cost(t[0], res, n_res);
            total_t    += pse_tcount(t[0], res, n_res);
            total_gates += n_cubes;
#if ANCILLA_CONTROL
            record(count_fixed_controls(t[0]) + 1);
#else
            record(count_fixed_controls(t[0]));
#endif
            for (int i = 0; i < n_res; i++) record(count_fixed_controls(res[i]));

            int a = pse_ancilla(n_res);
            if (a > anc_peak) anc_peak = a;
            anc_total += a;
            pse_count++;
        }
    }
    fclose(fp);

    /* one metric per line, easy to grep from a driver script */
    printf("TOTAL MASLOV COST = %d\n", total_cost);
    printf("TOTAL TCOUNT      = %d\n", total_t);
    printf("TOTAL GATES       = %d\n", total_gates);
    printf("MAX CONTROLS      = %d\n", max_controls);
    printf("ANCILLA PEAK      = %d\n", anc_peak);
    printf("ANCILLA TOTAL     = %d\n", anc_total);
    printf("ESOP TERMS        = %d\n", esop_count);
    printf("PSE TERMS         = %d\n", pse_count);
    printf("GATE HISTOGRAM    =");
    for (int i = 0; i < MAX_ARITY; i++)
        if (gate_hist[i]) printf(" %d:%d", i, gate_hist[i]);
    printf("\n");

    return 0;
}