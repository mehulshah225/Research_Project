#!/usr/bin/env python3
"""
Equivalence checker for the EXORCISM-5 pipeline.

Verifies that a factorized representation computes the same Boolean function
as the ESOP it was derived from. Nothing in the existing pipeline does this;
adding it would have caught both correctness bugs immediately.

Usage:
    python verify_equivalence.py results/esop/NAME.esop results/final/NAME.final.eosops
    python verify_equivalence.py --all          # sweep results/esop + results/final

Exhaustive for n <= 20; random-vector sampling above that (a failure is proof
of inequivalence, a pass is strong evidence, not proof).
"""
import sys, os, glob, random, itertools

def load(path):
    """Each row is a list of cube strings: [G] or [G, C] or [L, R1, R2]."""
    rows = []
    for line in open(path):
        line = line.strip()
        if not line or line[0] not in '01-':
            continue
        toks = [t for t in line.split() if t != '1']
        if toks:
            rows.append(toks)
    return rows

def cube_true(cube, x):
    return all(x[i] == int(ch) for i, ch in enumerate(cube) if ch != '-')

def evaluate(rows, x):
    """G -> G ; G C -> G.C' ; L R1 R2 -> L.(R1 xor R2)"""
    out = 0
    for toks in rows:
        if len(toks) == 1:
            if cube_true(toks[0], x):
                out ^= 1
        elif len(toks) == 2:
            if cube_true(toks[0], x) and not cube_true(toks[1], x):
                out ^= 1
        else:
            if cube_true(toks[0], x):
                acc = 0
                for r in toks[1:]:
                    if cube_true(r, x):
                        acc ^= 1
                if acc:
                    out ^= 1
    return out

def check(src_path, out_path, samples=20000, seed=0):
    a, b = load(src_path), load(out_path)
    if not a:
        return None, 'empty source'
    n = len(a[0][0])
    if n <= 20:
        space = itertools.product([0, 1], repeat=n)
        total = 2 ** n
        mode = 'exhaustive'
    else:
        rng = random.Random(seed)
        space = ([rng.randint(0, 1) for _ in range(n)] for _ in range(samples))
        total = samples
        mode = f'{samples} random vectors'
    bad = 0
    for x in space:
        x = list(x)
        if evaluate(a, x) != evaluate(b, x):
            bad += 1
    return bad, f'{n} vars, {mode}, {bad}/{total} mismatches'

def verify_qasm(esop_path, qasm_path):
    import re

    cubes = load(esop_path)

    if not cubes:
        return None, 'empty source'

    n = len(cubes[0][0])

    gates = []
    nq = None

    with open(qasm_path) as f:
        for line in f:
            line = line.strip()

            if line.startswith('qreg'):
                m = re.search(r'q\[(\d+)\]', line)
                nq = int(m.group(1))

            elif line.startswith('x '):
                qs = [int(x) for x in re.findall(r'q\[(\d+)\]', line)]
                gates.append(('x', qs))

            elif line.startswith('cx '):
                qs = [int(x) for x in re.findall(r'q\[(\d+)\]', line)]
                gates.append(('cx', qs))

            elif line.startswith('ccx '):
                qs = [int(x) for x in re.findall(r'q\[(\d+)\]', line)]
                gates.append(('ccx', qs))

            elif line.startswith('mcx '):
                return None, 'MCX found in supposedly decomposed QASM'

    if nq is None:
        return None, 'no qreg found'

    def simulate(state):
        state = state[:]

        for kind, qs in gates:
            if kind == 'x':
                state[qs[0]] ^= 1

            elif kind == 'cx':
                c, t = qs
                if state[c]:
                    state[t] ^= 1

            elif kind == 'ccx':
                c1, c2, t = qs
                if state[c1] and state[c2]:
                    state[t] ^= 1

        return state

    mismatches = 0
    garbage = 0

    for value in range(2 ** n):
        x = [
            (value >> i) & 1
            for i in range(n)
        ]

        state = [0] * nq
        state[:n] = x

        result = simulate(state)

        expected = evaluate(cubes, x)
        actual = result[n]

        if actual != expected:
            mismatches += 1

        if any(result[n + 1:]):
            garbage += 1

    return (
        mismatches,
        f'{n} vars, exhaustive, '
        f'{mismatches}/{2**n} function mismatches, '
        f'{garbage}/{2**n} garbage states'
    )

def check_qasm(esop_path, qasm_path):
    """
    Exhaustively verify that a decomposed X/CX/CCX QASM circuit
    computes the same Boolean function as the source ESOP.

    q[0..n-1] = inputs
    q[n]       = output
    q[n+1:]    = ancillas/workspace, which must return to zero.
    """
    import re

    cubes = load(esop_path)

    if not cubes:
        return None, 'empty source'

    n = len(cubes[0][0])

    gates = []
    nq = None

    with open(qasm_path) as f:
        for line in f:
            line = line.strip()

            if line.startswith('qreg'):
                m = re.search(r'q\[(\d+)\]', line)
                if m:
                    nq = int(m.group(1))

            elif line.startswith('x '):
                qs = [
                    int(x)
                    for x in re.findall(r'q\[(\d+)\]', line)
                ]
                gates.append(('x', qs))

            elif line.startswith('cx '):
                qs = [
                    int(x)
                    for x in re.findall(r'q\[(\d+)\]', line)
                ]
                gates.append(('cx', qs))

            elif line.startswith('ccx '):
                qs = [
                    int(x)
                    for x in re.findall(r'q\[(\d+)\]', line)
                ]
                gates.append(('ccx', qs))

            elif line.startswith('mcx '):
                return (
                    None,
                    'MCX found in decomposed QASM'
                )

    if nq is None:
        return None, 'no qreg found'

    if nq <= n:
        return (
            None,
            f'QASM has {nq} qubits but needs at least {n + 1}'
        )

    def simulate(state):
        state = state[:]

        for kind, qs in gates:

            if kind == 'x':
                state[qs[0]] ^= 1

            elif kind == 'cx':
                control, target = qs

                if state[control]:
                    state[target] ^= 1

            elif kind == 'ccx':
                c1, c2, target = qs

                if state[c1] and state[c2]:
                    state[target] ^= 1

        return state

    mismatches = 0
    garbage_errors = 0

    total = 2 ** n

    for value in range(total):

        # Inputs q[0] ... q[n-1].
        x = [
            (value >> i) & 1
            for i in range(n)
        ]

        # Everything else starts at |0>.
        state = [0] * nq
        state[:n] = x

        result = simulate(state)

        expected = evaluate(cubes, x)
        actual = result[n]

        if actual != expected:
            mismatches += 1

        # Output is q[n].
        # Everything after q[n] must be restored to zero.
        if any(result[n + 1:]):
            garbage_errors += 1

    return (
        mismatches,
        f'{n} vars, exhaustive, '
        f'{mismatches}/{total} function mismatches, '
        f'{garbage_errors}/{total} garbage states'
    )

def main():

    if len(sys.argv) == 4 and sys.argv[1] == '--qasm':
        bad, msg = check_qasm(
            sys.argv[2],
            sys.argv[3]
        )

        if bad is None:
            print('ERROR  ' + msg)
            sys.exit(2)

        print(
            ('PASS  ' if bad == 0 else 'FAIL  ') + msg
        )

        sys.exit(0 if bad == 0 else 1)

    if len(sys.argv) == 3:
        bad, msg = check(
            sys.argv[1],
            sys.argv[2]
        )

        print(
            ('PASS  ' if bad == 0 else 'FAIL  ') + msg
        )

        sys.exit(0 if bad == 0 else 1)

    if len(sys.argv) == 2 and sys.argv[1] == '--all':
        fails = 0

        for e in sorted(
            glob.glob('results/esop/*.esop')
        ):
            name = os.path.basename(e)[:-5]

            for cand in (
                f'results/final/{name}.final.eosops',
                f'results/final_parser/{name}.final.eosops',
                f'results/eosops/{name}.eosops'
            ):
                if os.path.exists(cand):
                    bad, msg = check(e, cand)

                    tag = (
                        'PASS'
                        if bad == 0
                        else 'FAIL'
                    )

                    if bad:
                        fails += 1

                    print(
                        f'{tag}  {name:24s} {msg}'
                    )

                    break

        print(
            f'\n{fails} benchmark(s) failed equivalence'
        )

        sys.exit(1 if fails else 0)

    print(__doc__)
    sys.exit(2)

if __name__ == '__main__':
    main()