#ifndef CUBE_MERGE_H
#define CUBE_MERGE_H

#include "cube_types.h"
#include <stdbool.h>

bool find_best_merge(OutputCube *arr,
                     int count,
                     int numInputs,
                     int *outI,
                     int *outJ,
                     OutputCube *outCube);

#endif

