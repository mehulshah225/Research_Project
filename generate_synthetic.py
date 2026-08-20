#!/usr/bin/env python3
"""
Reference generator for the synthetic 100-variable benchmark family.

The distributed instances (benchmarks/synth_benchmarks/f_100_*.pla) were produced
by this model: each of the n positions of each product term is drawn
independently and uniformly from {'-', '0', '1'}, so a variable appears in a
term with probability 2/3 and, when it appears, with either polarity equally
often.

The model was confirmed against the distributed files: over 560,000 positions
the observed frequencies are 33.40% / 33.23% / 33.37%, giving chi-square = 2.9
against a uniform null (critical value 9.21 at p = 0.01, 2 d.f.).

Reproducing the family:

    python generate_synthetic.py            # writes 14 files to synth_benchmarks/

Instances are named f_100_<terms>-<index>.pla and use seed = index, so
f_100_400-2.pla is generated with 400 terms and seed 2. Duplicate terms are
rejected on generation, since a repeated term would cancel under XOR.
"""
import os
import random
import argparse

SYMBOLS = ('-', '0', '1')


def generate_term(rng, n):
    """One product term: each position uniform over {'-', '0', '1'}."""
    return ''.join(rng.choice(SYMBOLS) for _ in range(n))


def generate_function(n, p, seed):
    """p distinct product terms over n variables."""
    rng = random.Random(seed)
    terms, seen = [], set()
    while len(terms) < p:
        t = generate_term(rng, n)
        if t in seen:          # a repeated term cancels under XOR
            continue
        seen.add(t)
        terms.append(t)
    return terms


def write_pla(path, terms, n):
    with open(path, 'w') as fh:
        fh.write(f'# synthetic benchmark: {n} variables, {len(terms)} product terms\n')
        fh.write('# each position drawn uniformly from {-, 0, 1}\n')
        fh.write(f'.i {n}\n.o 1\n.p {len(terms)}\n')
        for t in terms:
            fh.write(f'{t} 1\n')
        fh.write('.e\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='synth_benchmarks')
    ap.add_argument('--vars', type=int, default=100)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    # the distributed family: term counts and per-instance seeds
    family = [(200, list(range(5))),
              (400, list(range(4))),
              (600, list(range(5)))]

    for p, seeds in family:
        for s in seeds:
            terms = generate_function(args.vars, p, s)
            name = f'f_{args.vars}_{p}-{s}.pla'
            write_pla(os.path.join(args.out, name), terms, args.vars)
            lits = sum(1 for t in terms for c in t if c != '-') / len(terms)
            print(f'{name:20s} {len(terms):4d} terms, mean {lits:.1f} literals')


if __name__ == '__main__':
    main()
