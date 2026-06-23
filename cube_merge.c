#include "cube_merge.h"
#include "cube_containment.h"
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>   /* for tracing prints */

/* Enable/disable tracing at runtime (set to 1 to trace) */
static int MERGE_TRACE = 1;

/* Helper: mask with lowest `n` bits set. */
static inline uint32_t inputs_full_mask(int n)
{
    if (n >= 32) return 0xFFFFFFFFu;
    return ((1u << n) - 1u);
}

/* Small helpers to stringify cubes for trace output. Caller provides buffer. */
static void cube_to_str(const Cube *c, int n, char *out, int out_len)
{
    int i, pos;
    if (n <= 0) { if (out_len>0) out[0]='\0'; return; }
    for (i = 0; i < n && i < out_len-1; ++i) {
        pos = n - 1 - i;
        uint32_t bit = 1u << pos;
        out[i] = (c->mask & bit) ? '-' : ((c->bits & bit) ? '1' : '0');
    }
    out[(n < out_len-1) ? n : out_len-1] = '\0';
}

static void outputcube_to_str(const OutputCube *oc, int n, char *out, int out_len)
{
    char g[128], c[128];
    cube_to_str(&oc->g, n, g, sizeof(g));
    if (!oc->hasNegative) {
        snprintf(out, out_len, "%s", g);
    } else {
        cube_to_str(&oc->c, n, c, sizeof(c));
        snprintf(out, out_len, "%s %s", g, c);
    }
}

/* Count fixed literals (non-dash) in `C` among the lowest `n` inputs. */
static int cdiff(const Cube *C, int n)
{
    uint32_t full = inputs_full_mask(n);
    uint32_t fixed = (~C->mask) & full;
#if defined(__GNUC__) || defined(__clang__)
    return __builtin_popcount(fixed);
#else
    int k = 0;
    while (fixed) { k += (fixed & 1u); fixed >>= 1; }
    return k;
#endif
}

/* Hamming distance restricted to positions where both cubes are fixed. */
static int hdist(const Cube *A, const Cube *B, int n)
{
    uint32_t full = inputs_full_mask(n);
    uint32_t common_fixed = (~A->mask & ~B->mask) & full;
    uint32_t diff = (A->bits ^ B->bits) & common_fixed;
#if defined(__GNUC__) || defined(__clang__)
    return __builtin_popcount(diff);
#else
    int d = 0; while (diff) { d += (diff & 1u); diff >>= 1; } return d;
#endif
}

/* Intersection G: positions where both A and B are fixed and equal stay fixed
   (value preserved); positions where either is dash or they disagree become dash. */
static Cube intersect_G(const Cube *A, const Cube *B, int n)
{
    uint32_t full = inputs_full_mask(n);
    uint32_t both_fixed = (~A->mask & ~B->mask) & full;
    uint32_t disagree = (A->bits ^ B->bits) & both_fixed;
    uint32_t agree = both_fixed & ~disagree;

    Cube G = {0,0};
    G.mask = (~agree) & full;        /* dash where not agree */
    G.bits = (A->bits & agree);      /* ones only where both had 1 */
    return G;
}

/* Compute C by taking fixed literals from the "more specific" side (src). */
static Cube diff_C(const Cube *A, const Cube *B, int n, int mode)
{
    const Cube *src = (mode == 1 ? A : B);
    uint32_t full = inputs_full_mask(n);

    uint32_t both_fixed = (~A->mask & ~B->mask) & full;
    uint32_t disagree = (A->bits ^ B->bits) & both_fixed;
    uint32_t agree = both_fixed & ~disagree;           /* agreement -> C dash */

    uint32_t src_fixed = (~src->mask) & full;          /* where src has literal */
    uint32_t either_dash = full & ~both_fixed;         /* one/both dashes */

    uint32_t C_mask = (agree | (either_dash & ~src_fixed)) & full;
    uint32_t C_bits = src->bits & src_fixed & (disagree | either_dash);

    Cube C = { C_bits, C_mask };
    return C;
}

/* Overlay fixed literals from Cdiff on top of Cold: where Cdiff is fixed it
   replaces Cold; otherwise Cold is preserved. */
static Cube overlay_diff_on_C(const Cube *Cold,
                              const Cube *Cdiff,
                              int n)
{
    uint32_t full = inputs_full_mask(n);
    uint32_t diff_fixed = (~Cdiff->mask) & full;

    Cube R;
    R.mask = Cold->mask & ~diff_fixed; /* clear dash where diff provides fixed */
    R.bits = (Cold->bits & ~diff_fixed) | (Cdiff->bits & diff_fixed);
    R.mask &= full;
    R.bits &= full;
    return R;
}

/* Check that the combined fixed literals in G and (if present) C do not
   contain both 0 and 1 values (i.e., consistent polarity). */
static bool consistent_polarity(const OutputCube *oc, int n)
{
    uint32_t full = inputs_full_mask(n);

    uint32_t g_fixed = (~oc->g.mask) & full;
    uint32_t g_ones = oc->g.bits & g_fixed;
    uint32_t g_zeros = g_fixed & ~oc->g.bits;

    uint32_t ones = g_ones;
    uint32_t zeros = g_zeros;

    if (oc->hasNegative) {
        uint32_t c_fixed = (~oc->c.mask) & full;
        ones |= (oc->c.bits & c_fixed);
        zeros |= (c_fixed & ~oc->c.bits);
    }

    return !((ones != 0) && (zeros != 0));
}

/* Invert fixed bits: dashes stay dash; fixed 1 -> 0, fixed 0 -> 1. */
static Cube invert_bits(const Cube *src, int n)
{
    uint32_t full = inputs_full_mask(n);
    uint32_t fixed = (~src->mask) & full;
    Cube out;
    out.mask = src->mask & full;
    out.bits = (~src->bits) & fixed;
    return out;
}

/* ------------------------------------------------------------
   Maslov/Toffoli cost helpers (Maslov table + QC estimation)
   ------------------------------------------------------------ */
static int get_toffoli_cost(int controls) {
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
        default: return 1021 + (controls - 9) * 1024;
    }
}

static inline int cube_fixed_count(const Cube *c, int n)
{
    uint32_t full = inputs_full_mask(n);
    uint32_t fixed = (~c->mask) & full;
#if defined(__GNUC__) || defined(__clang__)
    return __builtin_popcount(fixed);
#else
    int cnt = 0;
    while (fixed) { cnt += (fixed & 1u); fixed >>= 1; }
    return cnt;
#endif
}

static inline int cube_fixed_zeros(const Cube *c, int n)
{
    uint32_t full = inputs_full_mask(n);
    uint32_t zeros_mask = (~c->mask) & full & ~c->bits; /* fixed and zero */
#if defined(__GNUC__) || defined(__clang__)
    return __builtin_popcount(zeros_mask);
#else
    int cnt = 0;
    while (zeros_mask) { cnt += (zeros_mask & 1u); zeros_mask >>= 1; }
    return cnt;
#endif
}

/* Compute Maslov quantum cost for an OutputCube (approximation used earlier). */
static int maslov_cost_outputcube(const OutputCube *oc, int n)
{
    if (!oc->hasNegative) {
        int m = cube_fixed_count(&oc->g, n);
        int zeros = cube_fixed_zeros(&oc->g, n);
        int toff = get_toffoli_cost(m);
        int not_cost = 2 * zeros;
        return toff + not_cost;
    } else {
        int cube_controls = cube_fixed_count(&oc->g, n);
        int cube_zeros = cube_fixed_zeros(&oc->g, n);
        int mask_controls = cube_fixed_count(&oc->c, n);
        int mask_neg = cube_fixed_zeros(&oc->c, n);
        int total_controls = cube_controls + mask_controls;
        int toff = get_toffoli_cost(total_controls);
        int qc = toff + 2 * (cube_zeros + mask_neg) + 1; /* +1 for output not */
        return qc;
    }
}

/* ------------------------------------------------------------
   Merge rules: mixed+pure, pure+pure, special dash
   ------------------------------------------------------------ */
static bool merge_mixed_pure(const OutputCube *M,
                             const OutputCube *P,
                             int n,
                             OutputCube *Rout)
{
    if (!M->hasNegative || P->hasNegative) return false;

    ContainmentResult cr = pure_cube_containment(&M->g, &P->g, n);
    if (cr != CONTAINS_A_B) return false;

    if (cdiff(&M->c, n) > 1) return false;

    Cube G    = intersect_G(&M->g, &P->g, n);
    Cube diff = diff_C(&M->g, &P->g, n, 1);
    Cube C    = overlay_diff_on_C(&M->c, &diff, n);

    /* Prevent reconstruction of an existing pure cube via a full-dash P.
       If P is full-dash then intersect_G will produce a full-dash G and
       overlay will create a negative cube that simply recreates a pure term;
       disallow this to avoid undoing earlier useful merges. */
    uint32_t full = inputs_full_mask(n);
    if (!P->hasNegative && (P->g.mask == full) && (G.mask == full)) {
        if (MERGE_TRACE) {
            char sM[256], sP[256];
            outputcube_to_str(M, n, sM, sizeof(sM));
            outputcube_to_str(P, n, sP, sizeof(sP));
            printf("[TRACE] merge_mixed_pure prevented: would reconstruct pure via dash: M=%s P=%s\n", sM, sP);
        }
        return false;
    }

    Rout->hasNegative = true;
    Rout->g  = G;
    Rout->c  = C;
    Rout->id = M->id;
    if (MERGE_TRACE) {
        char sM[256], sP[256], sR[256];
        outputcube_to_str(M, n, sM, sizeof(sM));
        outputcube_to_str(P, n, sP, sizeof(sP));
        outputcube_to_str(Rout, n, sR, sizeof(sR));
        printf("[TRACE] merge_mixed_pure: M=%s (i) P=%s (j) -> R=%s\n", sM, sP, sR);
    }
    return true;
}

static bool merge_pure_pure(const OutputCube *A,
                            const OutputCube *B,
                            int n,
                            OutputCube *Rout,
                            int *hdOut,
                            int *cdOut)
{
    if (A->hasNegative || B->hasNegative) return false;

    ContainmentResult cr = pure_cube_containment(&A->g, &B->g, n);
    if (cr == CONTAINS_NONE) return false;

    int mode = (cr == CONTAINS_A_B ? 1 : 2);

    Cube G = intersect_G(&A->g, &B->g, n);
    Cube C = diff_C(&A->g, &B->g, n, mode);

    int hd = hdist(&A->g, &B->g, n);
    int cd = cdiff(&C, n);

    *hdOut = hd;
    *cdOut = cd;

    Rout->hasNegative = true;
    Rout->g = G;
    Rout->c = C;
    Rout->id = (mode == 1 ? A->id : B->id);

    if (MERGE_TRACE) {
        char sA[128], sB[128], sR[128];
        outputcube_to_str(A, n, sA, sizeof(sA));
        outputcube_to_str(B, n, sB, sizeof(sB));
        outputcube_to_str(Rout, n, sR, sizeof(sR));
        int before = maslov_cost_outputcube(A, n) + maslov_cost_outputcube(B, n);
        int after  = maslov_cost_outputcube(Rout, n);
        printf("[TRACE] merge_pure_pure candidate: A=%s B=%s -> R=%s | hd=%d cd=%d cost_before=%d cost_after=%d delta=%d\n",
               sA, sB, sR, hd, cd, before, after, before - after);
    }

    return true;
}

static bool merge_special_dash(const OutputCube *A,
                               const OutputCube *B,
                               int n,
                               OutputCube *Rout)
{
    const OutputCube *dash = NULL;
    const OutputCube *mix  = NULL;

    uint32_t full = inputs_full_mask(n);

    if (!A->hasNegative && A->g.mask == full) { dash = A; mix = B; }
    else if (!B->hasNegative && B->g.mask == full) { dash = B; mix = A; }
    else return false;

    if (!mix->hasNegative) return false;
    if (!consistent_polarity(mix, n)) return false;

    Cube invG = invert_bits(&mix->g, n);
    Cube invC = invert_bits(&mix->c, n);

    Rout->hasNegative = true;
    Rout->g = invG;
    Rout->c = invC;
    Rout->id = mix->id;

    if (MERGE_TRACE) {
        char sdash[128], smix[256], sR[256];
        outputcube_to_str(dash, n, sdash, sizeof(sdash));
        outputcube_to_str(mix, n, smix, sizeof(smix));
        outputcube_to_str(Rout, n, sR, sizeof(sR));
        printf("[TRACE] merge_special_dash: dash=%s mix=%s -> R=%s\n", sdash, smix, sR);
    }
    return true;
}

/* ------------------------------------------------------------
   MASTER MERGE SELECTOR with tracing
   ------------------------------------------------------------ */
bool find_best_merge(OutputCube *arr,
                     int count,
                     int n,
                     int *outI,
                     int *outJ,
                     OutputCube *outCube)
{
    if (MERGE_TRACE) printf("[TRACE] find_best_merge: count=%d n=%d\n", count, n);

    /* PASS 1: mixed + pure, first one found (preserve behavior) */
    for (int i = 0; i < count; i++) {
        for (int j = 0; j < count; j++) {
            if (i == j) continue;
            OutputCube tmp;
            if (merge_mixed_pure(&arr[i], &arr[j], n, &tmp)) {
                if (MERGE_TRACE) {
                    char sI[256], sJ[256], sR[256];
                    outputcube_to_str(&arr[i], n, sI, sizeof(sI));
                    outputcube_to_str(&arr[j], n, sJ, sizeof(sJ));
                    outputcube_to_str(&tmp, n, sR, sizeof(sR));
                    printf("[TRACE] PASS1 select i=%d j=%d: %s XOR %s -> %s\n", i, j, sI, sJ, sR);
                }
                *outI = i; *outJ = j; *outCube = tmp;
                return true;
            }
        }
    }

    /* Triple-aware preference: look for dash d + pure p that enable a pure+pure
       merge (invPure + q) with positive net benefit. If found, prefer the
       dash->inv step (so dash is consumed first) even if a pure+pure candidate
       currently has larger immediate delta. */
    {
        int bestTD=-1, bestTP=-1;
        int bestNet = 0;
        OutputCube bestInvPure;

        uint32_t full = inputs_full_mask(n);

        for (int d = 0; d < count; ++d) {
            if (arr[d].hasNegative) continue;
            if (arr[d].g.mask != full) continue; /* need full-dash */

            for (int p = 0; p < count; ++p) {
                if (p == d) continue;
                if (arr[p].hasNegative) continue; /* invert only pure cubes */

                /* synthesize inverted PURE (so it can join pure+pure) */
                OutputCube invPure;
                invPure.hasNegative = false;
                invPure.g = invert_bits(&arr[p].g, n);
                invPure.c.mask = full; invPure.c.bits = 0;
                invPure.id = arr[p].id;

                /* try all q to see if invPure+q produces positive net */
                for (int q = 0; q < count; ++q) {
                    if (q == d || q == p) continue;
                    if (arr[q].hasNegative) continue;

                    OutputCube tmpR;
                    int hd2=0, cd2=0;
                    if (!merge_pure_pure(&invPure, &arr[q], n, &tmpR, &hd2, &cd2)) continue;

                    int before_total = maslov_cost_outputcube(&arr[d], n) +
                                       maslov_cost_outputcube(&arr[p], n) +
                                       maslov_cost_outputcube(&arr[q], n);

                    int after_total = maslov_cost_outputcube(&tmpR, n);

                    int net = before_total - after_total;
                    if (net > bestNet) {
                        bestNet = net;
                        bestTD = d; bestTP = p;
                        bestInvPure = invPure;
                    }
                }
            }
        }

        if (bestNet > 0) {
            if (MERGE_TRACE) {
                char sd[128], sp[128], si[128];
                outputcube_to_str(&arr[bestTD], n, sd, sizeof(sd));
                outputcube_to_str(&arr[bestTP], n, sp, sizeof(sp));
                outputcube_to_str(&bestInvPure, n, si, sizeof(si));
                printf("[TRACE] SELECT triple-pref dash->inv d=%d p=%d net=%d: %s + %s -> invPure=%s\n",
                       bestTD, bestTP, bestNet, sd, sp, si);
            }
            *outI = bestTD;
            *outJ = bestTP;
            *outCube = bestInvPure;
            return true;
        }
    }

    /* PASS 1.5: special dash + mixed — evaluate by Maslov QC reduction
       and select a positive reduction if any (keeps dash-use opportunistic). */
    {
        bool found_dash = false;
        int bestDI = -1, bestDJ = -1;
        OutputCube bestD;
        int bestDDelta = 0;

        for (int i = 0; i < count; ++i) {
            for (int j = 0; j < count; ++j) {
                if (i == j) continue;
                OutputCube tmp;
                if (!merge_special_dash(&arr[i], &arr[j], n, &tmp)) continue;

                /* Skip results that produce both a non-empty G and a non-empty C */
                if (cube_fixed_count(&tmp.g, n) > 0 && cube_fixed_count(&tmp.c, n) > 0) {
                    if (MERGE_TRACE) {
                        char sA[128], sB[256], sR[256];
                        outputcube_to_str(&arr[i], n, sA, sizeof(sA));
                        outputcube_to_str(&arr[j], n, sB, sizeof(sB));
                        outputcube_to_str(&tmp, n, sR, sizeof(sR));
                        printf("[TRACE] SKIP dash-mix (complex G+C): i=%d j=%d: %s XOR %s -> %s\n",
                            i, j, sA, sB, sR);
                    }
                    continue;
                }
                
                int before = maslov_cost_outputcube(&arr[i], n) + maslov_cost_outputcube(&arr[j], n);
                int after  = maslov_cost_outputcube(&tmp, n);
                int delta = before - after;

                if (MERGE_TRACE) {
                    char sA[128], sB[256], sR[256];
                    outputcube_to_str(&arr[i], n, sA, sizeof(sA));
                    outputcube_to_str(&arr[j], n, sB, sizeof(sB));
                    outputcube_to_str(&tmp, n, sR, sizeof(sR));
                    printf("[TRACE] EVAL dash-mix i=%d j=%d: A=%s B=%s -> R=%s | before=%d after=%d delta=%d\n",
                           i, j, sA, sB, sR, before, after, delta);
                }

                if (delta > bestDDelta) {
                    found_dash = true;
                    bestDDelta = delta;
                    bestDI = i; bestDJ = j; bestD = tmp;
                }
            }
        }

        if (found_dash && bestDDelta > 0) {
            if (MERGE_TRACE) {
                char sA[128], sB[256], sR[256];
                outputcube_to_str(&arr[bestDI], n, sA, sizeof(sA));
                outputcube_to_str(&arr[bestDJ], n, sB, sizeof(sB));
                outputcube_to_str(&bestD, n, sR, sizeof(sR));
                printf("[TRACE] SELECT dash-mix by QC reduction i=%d j=%d delta=%d: %s XOR %s -> %s\n",
                       bestDI, bestDJ, bestDDelta, sA, sB, sR);
            }
            *outI = bestDI; *outJ = bestDJ; *outCube = bestD;
            return true;
        }
    }

    /* PASS 2: pure + pure → choose best by Maslov QC reduction first,
       falling back to previous hd/cd metric if no positive reduction found. */
    bool found = false;
    int bestI = -1, bestJ = -1;
    int bestHD = 9999, bestCD = 9999;
    OutputCube bestR;
    int bestDelta = 0;

    /* First: search for best QC reduction */
    for (int i = 0; i < count; i++) {
        for (int j = i + 1; j < count; j++) {
            OutputCube tmp;
            int hd, cd;
            if (!merge_pure_pure(&arr[i], &arr[j], n, &tmp, &hd, &cd)) continue;

            int cost_before = maslov_cost_outputcube(&arr[i], n) + maslov_cost_outputcube(&arr[j], n);
            int cost_after  = maslov_cost_outputcube(&tmp, n);
            int delta = cost_before - cost_after;

            if (MERGE_TRACE) {
                char sA[128], sB[128], sR[128];
                outputcube_to_str(&arr[i], n, sA, sizeof(sA));
                outputcube_to_str(&arr[j], n, sB, sizeof(sB));
                outputcube_to_str(&tmp, n, sR, sizeof(sR));
                printf("[TRACE] EVAL pure i=%d j=%d: A=%s B=%s -> R=%s | before=%d after=%d delta=%d hd=%d cd=%d\n",
                       i, j, sA, sB, sR, cost_before, cost_after, delta, hd, cd);
            }

            if (delta > bestDelta ||
               (delta == bestDelta && (!found || hd < bestHD || (hd == bestHD && cd < bestCD)))) {
                found = true;
                bestDelta = delta;
                bestHD = hd;
                bestCD = cd;
                bestI = i; bestJ = j; bestR = tmp;
            }
        }
    }

    if (found && bestDelta > 0) {
        if (MERGE_TRACE) {
            char sA[128], sB[128], sR[256];
            outputcube_to_str(&arr[bestI], n, sA, sizeof(sA));
            outputcube_to_str(&arr[bestJ], n, sB, sizeof(sB));
            outputcube_to_str(&bestR, n, sR, sizeof(sR));
            printf("[TRACE] SELECT pure by QC reduction i=%d j=%d delta=%d: %s XOR %s -> %s\n",
                   bestI, bestJ, bestDelta, sA, sB, sR);
        }
        *outI = bestI; *outJ = bestJ; *outCube = bestR;
        return true;
    }

    /* Fallback: previous hd/cd selection */
    found = false;
    bestI = bestJ = -1;
    bestHD = bestCD = 9999;

    for (int i = 0; i < count; i++) {
        for (int j = i + 1; j < count; j++) {
            OutputCube tmp;
            int hd, cd;
            if (merge_pure_pure(&arr[i], &arr[j], n, &tmp, &hd, &cd)) {
                if (!found || hd < bestHD || (hd == bestHD && cd < bestCD)) {
                    found = true;
                    bestHD = hd;
                    bestCD = cd;
                    bestI = i; bestJ = j; bestR = tmp;
                }
            }
        }
    }

    if (found) {
        if (MERGE_TRACE) {
            char sA[128], sB[128], sR[256];
            outputcube_to_str(&arr[bestI], n, sA, sizeof(sA));
            outputcube_to_str(&arr[bestJ], n, sB, sizeof(sB));
            outputcube_to_str(&bestR, n, sR, sizeof(sR));
            printf("[TRACE] SELECT pure by hd/cd i=%d j=%d hd=%d cd=%d: %s XOR %s -> %s\n",
                   bestI, bestJ, bestHD, bestCD, sA, sB, sR);
        }
        *outI = bestI; *outJ = bestJ; *outCube = bestR;
        return true;
    }

    /* PASS 3: special mixed+dash (last resort) */
    for (int i = 0; i < count; i++) {
        for (int j = 0; j < count; j++) {
            if (i == j) continue;
            OutputCube tmp;
            if (merge_special_dash(&arr[i], &arr[j], n, &tmp)) {
                if (MERGE_TRACE) {
                    char sI[128], sJ[256], sR[256];
                    outputcube_to_str(&arr[i], n, sI, sizeof(sI));
                    outputcube_to_str(&arr[j], n, sJ, sizeof(sJ));
                    outputcube_to_str(&tmp, n, sR, sizeof(sR));
                    printf("[TRACE] PASS3 select i=%d j=%d: %s XOR %s -> %s\n", i, j, sI, sJ, sR);
                }
                *outI = i; *outJ = j; *outCube = tmp;
                return true;
            }
        }
    }

    if (MERGE_TRACE) printf("[TRACE] find_best_merge: no merge found\n");
    return false;
}