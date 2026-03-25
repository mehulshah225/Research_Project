#include "cube_containment.h"
#include <stdint.h>

// --------------------------------------------------------
// Helpers
// --------------------------------------------------------

static bool is_full_dash(const Cube *c, int numInputs)
{
    uint32_t full = (numInputs == 32) ? 0xFFFFFFFFu : ((1u << numInputs) - 1u);
    return (c->mask == full);
}

bool is_all_zero_or_dash(const Cube *c, int numInputs)
{
    for (int i = 0; i < numInputs; i++) {
        uint32_t bit = 1u << i;
        if (c->mask & bit) continue;      // dash
        if (c->bits & bit) return false;  // fixed 1 → not all 0/dash
    }
    return true;
}

bool is_all_one_or_dash(const Cube *c, int numInputs)
{
    for (int i = 0; i < numInputs; i++) {
        uint32_t bit = 1u << i;
        if (c->mask & bit) continue;        // dash
        if (!(c->bits & bit)) return false; // fixed 0 → not all 1/dash
    }
    return true;
}

static int literal_count(const Cube *c, int numInputs)
{
    int cnt = 0;
    for (int i = 0; i < numInputs; i++) {
        if (!(c->mask & (1u << i)))
            cnt++;
    }
    return cnt;
}

static bool literals_match(const Cube *large,
                           const Cube *small,
                           int numInputs)
{
    for (int i = 0; i < numInputs; i++) {
        uint32_t bit = 1u << i;

        bool sDash = (small->mask & bit);
        if (sDash) continue;

        bool sVal  = (small->bits & bit) != 0;
        bool lDash = (large->mask & bit) != 0;
        bool lVal  = (large->bits & bit) != 0;

        if (lDash) return false;
        if (lVal != sVal) return false;
    }
    return true;
}

// --------------------------------------------------------
// PURE CUBE CONTAINMENT — your original semantics
// --------------------------------------------------------

ContainmentResult pure_cube_containment(
    const Cube *A, const Cube *B, int numInputs)
{
    bool A_dash = is_full_dash(A, numInputs);
    bool B_dash = is_full_dash(B, numInputs);

    bool A_zero = is_all_zero_or_dash(A, numInputs);
    bool A_one  = is_all_one_or_dash(A, numInputs);
    bool B_zero = is_all_zero_or_dash(B, numInputs);
    bool B_one  = is_all_one_or_dash(B, numInputs);

    // --------------------------------------------------------
    // FULL-DASH BEHAVIOR (your semantics: more specific contains)
    // --------------------------------------------------------

    // A is full dash: only "contains" B if B is also full dash.
    if (A_dash) {
        if (B_dash)
            return CONTAINS_A_B;   // ---- contains ----
        return CONTAINS_NONE;      // ---- does NOT contain a more specific cube
    }

    // B is full dash: A may contain B ONLY if A is uniform (0/dash or 1/dash)
    if (B_dash) {
        if (A_zero || A_one)
            return CONTAINS_A_B;   // e.g. 000-, 11-- contain ----
        return CONTAINS_NONE;      // mixed polarity cannot contain ----
    }

    // --------------------------------------------------------
    // Neither full dash → literal-based containment
    // --------------------------------------------------------

    int litA = literal_count(A, numInputs);
    int litB = literal_count(B, numInputs);

    if (litA == litB)
        return CONTAINS_NONE;

    if (litA > litB) {
        // A more specific → may contain B
        return literals_match(A, B, numInputs)
               ? CONTAINS_A_B
               : CONTAINS_NONE;
    } else {
        // B more specific → may contain A
        return literals_match(B, A, numInputs)
               ? CONTAINS_B_A
               : CONTAINS_NONE;
    }
}

// --------------------------------------------------------
// FULL CONTAINMENT LOGIC (PURE & (future) MIXED)
// For now: mixed parts are ignored; base relation on G-only.
// --------------------------------------------------------

ContainmentResult containment_relation(
    const OutputCube *A,
    const OutputCube *B,
    int numInputs)
{
    const Cube *AG = &A->g;
    const Cube *BG = &B->g;

    bool Aneg = A->hasNegative;
    bool Bneg = B->hasNegative;

    // For the current flow all input cubes are PURE,
    // and merges only add C; you asked containment for
    // PURE+PURE debugging, so we keep it simple:
    if (!Aneg && !Bneg) {
        return pure_cube_containment(AG, BG, numInputs);
    }

    // If you later want full mixed containment, we can
    // extend here, but right now we return NONE so
    // debug output is on pure-only part.
    return CONTAINS_NONE;
}
