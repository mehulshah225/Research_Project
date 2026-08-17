# Oracle benchmarks in PLA format

22 single-output Boolean oracles used to test EXORCISM-5 on functions that
quantum algorithms actually synthesize.

## Format

Standard PLA, identical in shape to the existing benchmark files:

    .i 8          <- 8 INPUT variables
    .o 1          <- 1 OUTPUT  (single-output, like every benchmark in the suite)
    .p 2          <- 2 product terms
    .type esop
    101110-0 1
    101-1011 1
    .e

`.i` is the oracle's input width (8-12 here). `.o` is always 1: an oracle
answers one yes/no question, so it has one output bit. Multi-bit results such
as a^x mod N are given as one file per output bit.

## Families

    grover_3sat_n{8,10,12}_{1,2,3}      random 3-SAT at ratio 4.26 (hard threshold)
    shor_modexp_{a}_mod{N}_bit{k}       bit k of a^x mod N
    adder{n}_bit{k}                     bit k of n-bit ripple-carry addition
    majority{n}                         n-input majority

## How these were run

    ./esop_min      oracle.esop      out.eosops     # stage 1: containment
    ./final_parser  out.eosops     > out.final      # stage 2: polarity
    ./maslov        oracle.esop                     # baseline cost
    ./maslov        out.final                       # factorized cost

`run_oracle.sh` does all four. The oracle .esop takes the place of what
EXORCISM-4 would normally emit, so the synthesis pipeline is unmodified.

## Note on two degenerate files

`grover_3sat_n10_3` and `grover_3sat_n12_1` have `.p 0` - those SAT instances
are unsatisfiable, so the oracle is the constant 0 and there is no circuit.
They are excluded from the reported medians.
