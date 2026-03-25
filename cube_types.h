#ifndef CUBE_TYPES_H
#define CUBE_TYPES_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint32_t bits;  // 1 where literal is fixed 1
    uint32_t mask;  // 1 where literal is '-'
} Cube;

typedef struct {
    Cube g;          // positive part
    Cube c;          // negative offset part (for mixed cubes)
    bool hasNegative;
    int  id;         // original cube index from input
} OutputCube;

#endif


