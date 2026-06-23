#ifndef CUBE_TYPES_H
#define CUBE_TYPES_H

#include <stdint.h>
#include <stdbool.h>

/* Cube:
 * - `bits`: bit == 1 means the corresponding input is fixed to 1.
 * - `mask`: bit == 1 means the corresponding input is a dash (don't-care).
 * Only the lowest `n` bits are significant.
 */
typedef struct {
    uint32_t bits;
    uint32_t mask;
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


