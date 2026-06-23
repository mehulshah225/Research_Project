#ifndef CUBE_CONTAINMENT_H
#define CUBE_CONTAINMENT_H

#include <stdint.h>
#include <stdbool.h>
#include "cube_types.h"

/* Public APIs (behavior-preserving) */
ContainmentResult pure_cube_containment(const Cube *A, const Cube *B, int numInputs);
ContainmentResult containment_relation(const OutputCube *A, const OutputCube *B, int numInputs);

#endif /* CUBE_CONTAINMENT_H */