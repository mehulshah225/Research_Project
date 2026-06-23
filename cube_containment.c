#include "cube_containment.h"
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

// Helper: mask with lowest `numInputs` bits set.
static inline uint32_t inputs_full_mask(int numInputs)
{
    if (numInputs >= 32) return 0xFFFFFFFFu;
    return ((1u << numInputs) - 1u);
}

// Fully-dash cube: every input is a dash.
static inline bool is_full_dash(const Cube *c, int numInputs)
{
    return c->mask == inputs_full_mask(numInputs);
}

// True when every fixed literal (non-dash) is 0.
// (bits & ~mask) == 0 restricted to relevant inputs.
bool is_all_zero_or_dash(const Cube *c, int numInputs)
{
    uint32_t full = inputs_full_mask(numInputs);
    return (c->bits & ~c->mask & full) == 0u;
}

// True when every fixed literal (non-dash) is 1.
bool is_all_one_or_dash(const Cube *c, int numInputs)
{
    uint32_t full = inputs_full_mask(numInputs);
    return ((~c->bits) & ~c->mask & full) == 0u;
}

// Number of fixed literals (non-dash).
static inline int literal_count(const Cube *c, int numInputs)
{
    uint32_t full = inputs_full_mask(numInputs);
    uint32_t fixed = (~c->mask) & full;
#if defined(__GNUC__) || defined(__clang__)
    return __builtin_popcount(fixed);
#else
    int cnt = 0;
    while (fixed) { cnt += (fixed & 1u); fixed >>= 1; }
    return cnt;
#endif
}

// Check whether every literal fixed in `small` is fixed in `large`
// and their values match. Uses bit ops (no loops).
static inline bool literals_match(const Cube *large,
                                  const Cube *small,
                                  int numInputs)
{
    uint32_t full = inputs_full_mask(numInputs);
    uint32_t s_fixed = (~small->mask) & full; // positions small fixes

    // If large leaves any of those positions dashed, fail.
    if (s_fixed & large->mask) return false;

    // Values must agree on the fixed positions.
    return (((large->bits ^ small->bits) & s_fixed) == 0u);
}

// --------------------------------------------------------
// PURE CUBE CONTAINMENT — original semantics retained
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
    // FULL-DASH BEHAVIOR (semantics: more specific contains)
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
    // and merges only add C; containment debugging focuses on pure-only.
    if (!Aneg && !Bneg) {
        return pure_cube_containment(AG, BG, numInputs);
    }

    // If you later want full mixed containment, extend here.
    return CONTAINS_NONE;
}