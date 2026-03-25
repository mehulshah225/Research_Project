#ifndef CUBE_CONTAINMENT_H
#define CUBE_CONTAINMENT_H

#include <stdbool.h>
#include "cube_types.h"

typedef enum {
    CONTAINS_NONE = 0,
    CONTAINS_A_B,
    CONTAINS_B_A
} ContainmentResult;

// These are needed by merge code as well
bool is_all_zero_or_dash(const Cube *c, int numInputs);
bool is_all_one_or_dash(const Cube *c, int numInputs);

ContainmentResult pure_cube_containment(
    const Cube *A,
    const Cube *B,
    int numInputs);

ContainmentResult containment_relation(
    const OutputCube *A,
    const OutputCube *B,
    int numInputs);

#endif
