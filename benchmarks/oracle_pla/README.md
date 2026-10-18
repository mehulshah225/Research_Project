# Oracle benchmarks in PLA format

13 single-output Boolean oracles used to test EXORCISM-5 on functions that
quantum algorithms actually synthesize. Each file was generated from the
definition of its function and checked exhaustively against it.

## Format

Standard PLA, identical in shape to the other benchmark files:

    .i 8          <- 8 INPUT variables
    .o 1          <- 1 OUTPUT  (single-output, like every benchmark in the suite)
    .p 2          <- 2 product terms
    .type esop
    ------11 1
    ------0- 1
    .e

`.i` is the oracle's input width (7-11 here). `.o` is always 1: an oracle
answers one yes/no question, so it has one output bit. Multi-bit results such
as a^x mod N are given as one file per output bit. Inputs are most significant
bit first; adder inputs are the two operands concatenated, a then b.

## Families

    shor_modexp_{a}_mod{N}_bit{k}   bit k of a^x mod N, (a,N) in {(7,15),(2,21),(5,33)}   6 files
    adder{n}_bit{k}                 high-order sum and carry bits of n-bit addition, n in {4,5}   4 files
    majority{n}                     n-input majority, n in {7,9,11}                       3 files

## How these were run

The oracles go through the same pipeline as every other benchmark:
`run_all.py` minimizes each file with EXORCISM-4 and then applies both
factorization stages. Their EXORCISM-4 output is in `results/esop/`.
