#ifndef CUBE_MERGE_H
#define CUBE_MERGE_H

#include <stdint.h>
#include <stdbool.h>
#include "cube_containment.h"

/*

Public merge API for combining OutputCube entries.
find_best_merge:
Scans arr (length count) and selects the best pair to merge
according to existing rules (mixed+pure, best pure+pure, special dash case).
n is the number of inputs (only lowest n bits are significant).
On success, writes indices to outI and outJ and the merged cube to
outCube, and returns true. Returns false when no merge is possible.
Note: internal helpers used by cube_merge.c are intentionally not exposed.
*/
bool find_best_merge(OutputCube *arr,
int count,
int n,
int *outI,
int *outJ,
OutputCube *outCube);
#endif /* CUBE_MERGE_H */