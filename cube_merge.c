#include "cube_merge.h"
#include "cube_containment.h"
#include <string.h>

// ------------------------------------------------------------
// Basic helpers
// ------------------------------------------------------------
static int cdiff(const Cube *C, int n)
{
    int k = 0;
    for (int i = 0; i < n; i++) {
        uint32_t bit = 1u << i;
        if (!(C->mask & bit))
            k++;
    }
    return k;
}

static int hdist(const Cube *A, const Cube *B, int n)
{
    int d = 0;
    for (int i = 0; i < n; i++) {
        uint32_t bit = 1u << i;

        bool aDash = (A->mask & bit) != 0;
        bool bDash = (B->mask & bit) != 0;
        if (aDash || bDash) continue;

        bool aVal = (A->bits & bit) != 0;
        bool bVal = (B->bits & bit) != 0;
        if (aVal != bVal) d++;
    }
    return d;
}

// Intersection G = shared fixed bits, else dash
static Cube intersect_G(const Cube *A, const Cube *B, int n)
{
    Cube G = {0,0};

    for (int i = 0; i < n; i++) {
        uint32_t bit = 1u << i;

        bool aDash = (A->mask & bit) != 0;
        bool bDash = (B->mask & bit) != 0;

        if (aDash || bDash) {
            G.mask |= bit;
            continue;
        }

        bool aVal = (A->bits & bit) != 0;
        bool bVal = (B->bits & bit) != 0;

        if (aVal == bVal) {
            if (aVal) G.bits |= bit;
        } else {
            G.mask |= bit;
        }
    }
    return G;
}

// diff_C takes fixed bits from the "more specific" side
// mode = 1 → A contains B, take from A
// mode = 2 → B contains A, take from B
static Cube diff_C(const Cube *A, const Cube *B, int n, int mode)
{
    const Cube *src = (mode == 1 ? A : B);
    Cube C = {0,0};

    for (int i = 0; i < n; i++) {
        uint32_t bit = 1u << i;

        bool aDash = (A->mask & bit) != 0;
        bool bDash = (B->mask & bit) != 0;

        if (!aDash && !bDash) {
            bool aVal = (A->bits & bit) != 0;
            bool bVal = (B->bits & bit) != 0;

            if (aVal == bVal) {
                // agreement → dash in C
                C.mask |= bit;
            } else {
                // disagreement → take from src
                if (!(src->mask & bit)) {
                    if (src->bits & bit)
                        C.bits |= bit;
                }
            }
        } else {
            // one/both dashes → copy fixed from src
            if (!(src->mask & bit)) {
                if (src->bits & bit)
                    C.bits |= bit;
            } else {
                C.mask |= bit;
            }
        }
    }

    return C;
}

static Cube overlay_diff_on_C(const Cube *Cold,
                              const Cube *Cdiff,
                              int n)
{
    Cube R = *Cold; // preserve old bits and only overwrite where Cdiff fixed

    for (int i = 0; i < n; i++) {
        uint32_t bit = 1u << i;

        if (!(Cdiff->mask & bit)) {
            // Cdiff fixed → overwrite
            R.mask &= ~bit;
            if (Cdiff->bits & bit)
                R.bits |= bit;
            else
                R.bits &= ~bit;
        }
        // if Cdiff dash → leave R as-is
    }
    return R;
}

static bool consistent_polarity(const OutputCube *oc, int n)
{
    bool seen0 = false, seen1 = false;

    // G
    for (int i = 0; i < n; i++) {
        uint32_t bit = 1u << i;
        if (oc->g.mask & bit) continue;

        if (oc->g.bits & bit) seen1 = true;
        else                  seen0 = true;
    }

    // C
    if (oc->hasNegative) {
        for (int i = 0; i < n; i++) {
            uint32_t bit = 1u << i;
            if (oc->c.mask & bit) continue;

            if (oc->c.bits & bit) seen1 = true;
            else                  seen0 = true;
        }
    }

    return !(seen0 && seen1);
}

static Cube invert_bits(const Cube *src, int n)
{
    Cube out = {0,0};
    for (int i = 0; i < n; i++) {
        uint32_t bit = 1u << i;

        if (src->mask & bit) {
            out.mask |= bit;  // dash stays dash
        } else {
            if (src->bits & bit) {
                // 1 -> 0
            } else {
                // 0 -> 1
                out.bits |= bit;
            }
        }
    }
    return out;
}

// ------------------------------------------------------------
// 1) Mixed + Pure
//    - only if M contains P
//    - only if cdiff(M.c) <= 1
//    - G = intersection
//    - C = overlay(M.c, diff)
// ------------------------------------------------------------
static bool merge_mixed_pure(const OutputCube *M,
                             const OutputCube *P,
                             int n,
                             OutputCube *Rout)
{
    if (!M->hasNegative || P->hasNegative)
        return false;

    // M must contain P
    ContainmentResult cr = pure_cube_containment(&M->g, &P->g, n);
    if (cr != CONTAINS_A_B)
        return false;

    if (cdiff(&M->c, n) > 1)
        return false;

    Cube G    = intersect_G(&M->g, &P->g, n);
    Cube diff = diff_C(&M->g, &P->g, n, 1);          // take from M
    Cube C    = overlay_diff_on_C(&M->c, &diff, n);  // preserve old C

    Rout->hasNegative = true;
    Rout->g  = G;
    Rout->c  = C;
    // keep M's id as representative
    Rout->id = M->id;
    return true;
}

// ------------------------------------------------------------
// 2) Pure + Pure
//    - only if one contains the other
//    - result is always G + C (mixed)
//    - we compute hd, cd (for "best" choice)
// ------------------------------------------------------------
static bool merge_pure_pure(const OutputCube *A,
                            const OutputCube *B,
                            int n,
                            OutputCube *Rout,
                            int *hdOut,
                            int *cdOut)
{
    if (A->hasNegative || B->hasNegative)
        return false;

    ContainmentResult cr = pure_cube_containment(&A->g, &B->g, n);
    if (cr == CONTAINS_NONE)
        return false;

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
    // keep the more specific's id
    Rout->id = (mode == 1 ? A->id : B->id);
    return true;
}

// ------------------------------------------------------------
// 3) Special mixed + dash
//    - Only mixed + PURE full dash
//    - Only if mixed has consistent polarity
//    - Invert G and C
// ------------------------------------------------------------
static bool merge_special_dash(const OutputCube *A,
                               const OutputCube *B,
                               int n,
                               OutputCube *Rout)
{
    const OutputCube *dash = NULL;
    const OutputCube *mix  = NULL;

    // full dash cube must be pure
    uint32_t full = (n == 32 ? 0xFFFFFFFFu : ((1u << n) - 1u));

    if (!A->hasNegative && A->g.mask == full) {
        dash = A;
        mix  = B;
    } else if (!B->hasNegative && B->g.mask == full) {
        dash = B;
        mix  = A;
    } else {
        return false;
    }

    // must be mixed (no pure+dash explosions)
    if (!mix->hasNegative)
        return false;

    if (!consistent_polarity(mix, n))
        return false;

    Cube invG = invert_bits(&mix->g, n);
    Cube invC = invert_bits(&mix->c, n);

    Rout->hasNegative = true;
    Rout->g = invG;
    Rout->c = invC;
    Rout->id = mix->id;
    (void)dash; // unused logically
    return true;
}

// ------------------------------------------------------------
// MASTER MERGE SELECTOR
// ------------------------------------------------------------
bool find_best_merge(OutputCube *arr,
                     int count,
                     int n,
                     int *outI,
                     int *outJ,
                     OutputCube *outCube)
{
    // PASS 1: mixed + pure, first one found
    for (int i = 0; i < count; i++) {
        for (int j = 0; j < count; j++) {
            if (i == j) continue;

            OutputCube tmp;
            if (merge_mixed_pure(&arr[i], &arr[j], n, &tmp)) {
                *outI = i;
                *outJ = j;
                *outCube = tmp;
                return true;
            }
        }
    }

    // PASS 2: pure + pure → choose best (hd, then cd)
    bool found    = false;
    int  bestI    = -1;
    int  bestJ    = -1;
    int  bestHD   = 9999;
    int  bestCD   = 9999;
    OutputCube bestR;

    for (int i = 0; i < count; i++) {
        for (int j = i + 1; j < count; j++) {
            OutputCube tmp;
            int hd, cd;
            if (merge_pure_pure(&arr[i], &arr[j], n, &tmp, &hd, &cd)) {
                if (!found || hd < bestHD || (hd == bestHD && cd < bestCD)) {
                    found  = true;
                    bestHD = hd;
                    bestCD = cd;
                    bestI  = i;
                    bestJ  = j;
                    bestR  = tmp;
                }
            }
        }
    }

    if (found) {
        *outI = bestI;
        *outJ = bestJ;
        *outCube = bestR;
        return true;
    }

    // PASS 3: special mixed+dash
    for (int i = 0; i < count; i++) {
        for (int j = 0; j < count; j++) {
            if (i == j) continue;

            OutputCube tmp;
            if (merge_special_dash(&arr[i], &arr[j], n, &tmp)) {
                *outI = i;
                *outJ = j;
                *outCube = tmp;
                return true;
            }
        }
    }

    return false;
}
