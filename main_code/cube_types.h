#ifndef CUBE_TYPES_H
#define CUBE_TYPES_H

#include <stdint.h>
#include <stdbool.h>

/* Use a 128-bit word for the cube bitfields so 100+ variable cases do not
 * wrap around the 32-bit mask and bit storage used in earlier revisions.
 */
typedef unsigned __int128 CubeWord;

static inline CubeWord cube_inputs_full_mask(int n)
{
    if (n <= 0) return 0;
    if (n >= 128) return ~((CubeWord)0);
    return (((CubeWord)1) << n) - 1;
}

static inline int cube_popcount(CubeWord x)
{
    int count = 0;
    while (x != 0) {
        x &= x - 1;
        count++;
    }
    return count;
}

/* Cube:
 * - `bits`: bit == 1 means the corresponding input is fixed to 1.
 * - `mask`: bit == 1 means the corresponding input is a dash (don't-care).
 * Only the lowest `n` bits are significant.
 */
typedef struct {
    CubeWord bits;
    CubeWord mask;
} Cube;

/* OutputCube: representation used by merge/containment routines. */
typedef struct {
    Cube g;
    Cube c;
    bool hasNegative;
    int id;
} OutputCube;

/* Containment relation results (moved here so it's available project-wide). */
typedef enum {
    CONTAINS_NONE = 0,
    CONTAINS_A_B  = 1, /* A contains B (A is more general) */
    CONTAINS_B_A  = 2  /* B contains A */
} ContainmentResult;

#endif /* CUBE_TYPES_H */