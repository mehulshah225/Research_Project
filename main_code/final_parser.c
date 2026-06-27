#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#define MAX_CUBES 1024
#define MAX_N 64
#define MAX_EDGES (MAX_CUBES * MAX_CUBES)
#define MERGE_TRACE 1

typedef struct {
    char cube[MAX_N];
} Term;

typedef struct {
    int u;
    int v;
    int weight;
} Edge;

typedef struct {
    int a;
    int b;
} Pair;

static int numInputs = 0;

/* free cubes */
static Term free_terms[MAX_CUBES];
static int freeCount = 0;

/* fixed G+C terms */
static char fixed_terms[MAX_CUBES][2][MAX_N];
static int fixedCount = 0;

/* graph edges */
static Edge edges[MAX_EDGES];
static int edgeCount = 0;

/* final matched pairs */
static Pair pairs[MAX_CUBES];
static int pairCount = 0;

/* =========================================
   DEBUG CONTROL
   Set to 0 to disable all debug traces
========================================= */
static void trace(const char *fmt, ...)
{
#if MERGE_TRACE
    va_list args;
    va_start(args, fmt);
    vfprintf(stderr, fmt, args);
    va_end(args);
#endif
}
/* ------------------------------------------------ */
static char safe_get(const char *c, int i)
{
    int len = strlen(c);
    if (i >= len) return '-';
    return c[i];
}

/* ------------------------------------------------ */
static int is_all_dash(const char *cube)
{
    for (int i = 0; i < numInputs; i++) {
        if (cube[i] != '-')
            return 0;
    }
    return 1;
}

/* ------------------------------------------------ */
static int build_factor(const char *A, const char *B, char *L)
{
    int shared = 0;

    for (int i = 0; i < numInputs; i++) {
        char a = safe_get(A, i);
        char b = safe_get(B, i);

        if (a == '-' || b == '-') {
            L[i] = '-';
        }
        else if (a == b) {
            L[i] = a;
            shared++;
        }
        else {
            L[i] = '-';
        }
    }

    L[numInputs] = '\0';
    return shared;
}

/* ------------------------------------------------ */
static void subtract(const char *A, const char *L, char *R)
{
    for (int i = 0; i < numInputs; i++) {
        if (L[i] != '-')
            R[i] = '-';
        else
            R[i] = A[i];
    }

    R[numInputs] = '\0';
}

/* ------------------------------------------------ */
static int can_merge(int i, int j)
{
    char L[MAX_N];
    char R1[MAX_N];
    char R2[MAX_N];

    int shared = build_factor(
        free_terms[i].cube,
        free_terms[j].cube,
        L
    );

    if (shared == 0)
        return 0;

    if (is_all_dash(L))
        return 0;

    subtract(free_terms[i].cube, L, R1);
    subtract(free_terms[j].cube, L, R2);

    if (is_all_dash(R1))
        return 0;

    if (is_all_dash(R2))
        return 0;

    return shared;
}

/* ------------------------------------------------ */
static int edge_compare(const void *a, const void *b)
{
    Edge *ea = (Edge *)a;
    Edge *eb = (Edge *)b;

    return eb->weight - ea->weight;
}

/* ------------------------------------------------ */
static void build_graph(void)
{
    edgeCount = 0;

    for (int i = 0; i < freeCount; i++) {
        for (int j = i + 1; j < freeCount; j++) {

            int score = can_merge(i, j);

            if (score > 0) {
                edges[edgeCount].u = i;
                edges[edgeCount].v = j;
                edges[edgeCount].weight = score;
                edgeCount++;
            }
        }
    }
}

/* ------------------------------------------------ */
static void maximum_matching(void)
{
    int used[MAX_CUBES] = {0};

    qsort(edges, edgeCount, sizeof(Edge), edge_compare);

    pairCount = 0;

    for (int i = 0; i < edgeCount; i++) {

        int u = edges[i].u;
        int v = edges[i].v;

        if (used[u] || used[v])
            continue;

        used[u] = 1;
        used[v] = 1;

        pairs[pairCount].a = u;
        pairs[pairCount].b = v;
        pairCount++;
    }
}

/* ------------------------------------------------ */
static void load_file(const char *filename)
{
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        perror("file");
        exit(1);
    }

    char line[256];

    while (fgets(line, sizeof(line), fp)) {

        if (line[0] == '.') {
            if (strncmp(line, ".i", 2) == 0)
                sscanf(line, ".i %d", &numInputs);
            continue;
        }

        if (line[0] == '\n')
            continue;

        char cube1[MAX_N];
        char cube2[MAX_N];
        int val;

        int tokens = sscanf(line, "%63s %63s %d", cube1, cube2, &val);

        if (tokens == 3) {
            strcpy(fixed_terms[fixedCount][0], cube1);
            strcpy(fixed_terms[fixedCount][1], cube2);
            fixedCount++;
        }
        else if (tokens == 2) {
            strcpy(free_terms[freeCount].cube, cube1);
            freeCount++;
        }
    }

    fclose(fp);
}

/* To print traces on the terminal */
static void trace_merge(int a_idx, int b_idx,
                        const char *A,
                        const char *B,
                        const char *L,
                        const char *R1,
                        const char *R2,
                        int score)
{
#if MERGE_TRACE
    fprintf(stderr, "\n====================================\n");
    fprintf(stderr, "[MERGE] Cube %d <--> Cube %d\n", a_idx, b_idx);
    fprintf(stderr, "A      : %s\n", A);
    fprintf(stderr, "B      : %s\n", B);
    fprintf(stderr, "Shared : %d\n", score);
    fprintf(stderr, "L      : %s\n", L);
    fprintf(stderr, "R1     : %s\n", R1);
    fprintf(stderr, "R2     : %s\n", R2);
    fprintf(stderr, "====================================\n");
#endif
}

/* ------------------------------------------------ */
static void output_result(void)
{
    int used[MAX_CUBES] = {0};

    int leftovers = freeCount - pairCount * 2;
    int totalP = fixedCount + pairCount + leftovers;

    printf(".i %d\n", numInputs);
    printf(".o 1\n");
    printf(".p %d\n", totalP);
    printf(".type exorcism5\n");

    /* fixed terms untouched */
    for (int i = 0; i < fixedCount; i++) {
        printf("%s %s 1\n",
               fixed_terms[i][0],
               fixed_terms[i][1]);
    }

    /* merged pairs */
    for (int i = 0; i < pairCount; i++) {

        int a = pairs[i].a;
        int b = pairs[i].b;

        char L[MAX_N];
        char R1[MAX_N];
        char R2[MAX_N];

        build_factor(
            free_terms[a].cube,
            free_terms[b].cube,
            L
        );

        subtract(free_terms[a].cube, L, R1);
        subtract(free_terms[b].cube, L, R2);

        trace_merge(
            a,
            b,
            free_terms[a].cube,
            free_terms[b].cube,
            L,
            R1,
            R2,
            build_factor(free_terms[a].cube,
                        free_terms[b].cube,
                        L)
        );

        printf("%s %s %s 1\n", L, R1, R2);

        used[a] = 1;
        used[b] = 1;
    }

    /* leftovers */
    for (int i = 0; i < freeCount; i++) {
        if (!used[i]) {
            printf("%s 1\n", free_terms[i].cube);
        }
    }

    printf(".e\n");
}

/* ------------------------------------------------ */
int main(int argc, char **argv)
{
    if (argc != 2) {
        printf("Usage: %s input.eosops\n", argv[0]);
        return 1;
    }

    load_file(argv[1]);
    build_graph();
    maximum_matching();
    output_result();

    return 0;
}