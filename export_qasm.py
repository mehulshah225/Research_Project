#!/usr/bin/env python3
"""
Export ESOP / factorized representations to OpenQASM 2.0.

Two modes are supported:

    python export_qasm.py input.esop
    python export_qasm.py --decompose input.esop

Default mode emits multi-controlled X gates as `mcx`.

--decompose mode lowers every MCX with >2 controls into only:
    x
    cx
    ccx

The decomposition uses additional clean ancillas that are separate from
the two ancillas belonging to the ESOP/factorized representation.

Qubit layout:

    q[0 .. n-1]       input variables
    q[n]              output
    q[n+1]            ESOP residual ancilla
    q[n+2]            ESOP shared-factor ancilla
    q[n+3 ..]         MCX decomposition workspace (--decompose only)

The decomposition is applied identically to baseline and factorized
representations, so the PyZX comparison uses the same circuit-lowering
procedure in all four conditions A/B/C/D.

Negative literals are handled by flipping the input before the controlled
operation and restoring it afterward.
"""

import sys
import argparse


def load(path):
    rows = []

    with open(path) as fh:
        for line in fh:
            line = line.strip()

            if not line or line[0] not in '01-':
                continue

            toks = [t for t in line.split() if t != '1']

            if toks:
                rows.append(toks)

    return rows


def fixed(cube):
    """Return [(index, '0'|'1'), ...] for every fixed literal."""
    return [
        (i, ch)
        for i, ch in enumerate(cube)
        if ch != '-'
    ]


class Emitter:
    def __init__(self, n, decompose=False, workspace_start=None):
        self.n = n
        self.decompose = decompose
        self.lines = []

        # Representation-level gate/control statistics.
        self.tcount_gates = []

        # MCX decomposition workspace.
        self.workspace_start = workspace_start
        self.workspace_used = 0

    def q(self, i):
        return f'q[{i}]'

    def x(self, i):
        self.lines.append(f'x {self.q(i)};')

    def cx(self, control, target):
        self.lines.append(
            f'cx {self.q(control)},{self.q(target)};'
        )

    def ccx(self, c1, c2, target):
        self.lines.append(
            f'ccx {self.q(c1)},{self.q(c2)},{self.q(target)};'
        )

    def _workspace(self, count):
        """
        Return `count` fresh workspace qubit indices.

        Workspace is allocated monotonically. It is never used as an
        input, output, or ESOP representation ancilla.
        """
        if count <= 0:
            return []

        start = self.workspace_start + self.workspace_used

        result = list(range(start, start + count))

        self.workspace_used += count

        return result

    def mcx_decomposed(self, controls, target):
        """
        Exact MCX decomposition using clean ancillas.

        For k controls:

            c0,c1 -> a0
            a0,c2 -> a1
            ...
            last_ancilla,last_control -> target
            ...
            uncompute ancillas

        Requires k-2 clean ancillas for k >= 3.

        The ancillas are returned to |0>.
        """

        k = len(controls)

        if k == 0:
            self.x(target)
            return

        if k == 1:
            self.cx(controls[0], target)
            return

        if k == 2:
            self.ccx(controls[0], controls[1], target)
            return

        # k >= 3
        workspace = self._workspace(k - 2)

        # Compute prefix ANDs.
        #
        # a0 = c0 & c1
        # a1 = a0 & c2
        # ...
        self.ccx(controls[0], controls[1], workspace[0])

        for i in range(2, k - 1):
            self.ccx(
                workspace[i - 2],
                controls[i],
                workspace[i - 1]
            )

        # Apply final controlled operation.
        self.ccx(
            workspace[-1],
            controls[-1],
            target
        )

        # Uncompute prefix ANDs in reverse order.
        for i in range(k - 2, 1, -1):
            self.ccx(
                workspace[i - 2],
                controls[i],
                workspace[i - 1]
            )

        self.ccx(
            controls[0],
            controls[1],
            workspace[0]
        )

    def mcx(self, controls, target):
        """
        Emit a multi-controlled X.

        Representation-level statistics record the original ESOP term
        exactly once, regardless of whether the circuit is decomposed.
        """

        controls = list(controls)

        # This is the representation-level control count.
        self.tcount_gates.append(len(controls))

        if not self.decompose:
            if not controls:
                self.x(target)

            elif len(controls) == 1:
                self.cx(controls[0], target)

            elif len(controls) == 2:
                self.ccx(
                    controls[0],
                    controls[1],
                    target
                )

            else:
                args = ','.join(
                    self.q(c) for c in controls
                ) + f',{self.q(target)}'

                self.lines.append(f'mcx {args};')

            return

        # Decomposed mode.
        self.mcx_decomposed(controls, target)

    def term(self, cube, target):
        """
        Apply the product cube onto target.

        Negative literals are implemented by:
            X
            controlled-X
            X
        """

        lits = fixed(cube)

        negs = [
            i
            for i, ch in lits
            if ch == '0'
        ]

        # Convert negative controls to positive controls.
        for i in negs:
            self.x(i)

        self.mcx(
            [i for i, _ in lits],
            target
        )

        # Restore original input polarity.
        for i in negs:
            self.x(i)


def build(rows, n, decompose=False):
    out = n

    # These two are the existing representation-level ancillas.
    anc1 = n + 1
    anc2 = n + 2

    # Additional workspace starts AFTER the representation ancillas.
    workspace_start = n + 3

    em = Emitter(
        n,
        decompose=decompose,
        workspace_start=workspace_start
    )

    for toks in rows:

        # --------------------------------------------------------------
        # Plain ESOP term
        # --------------------------------------------------------------
        if len(toks) == 1:
            em.term(
                toks[0],
                out
            )

        # --------------------------------------------------------------
        # Containment:
        #
        #     G . C'
        #
        # C onto ancilla, complement, then G + ancilla.
        # --------------------------------------------------------------
        elif len(toks) == 2:

            G, Cc = toks

            # Compute C onto ancilla.
            em.term(
                Cc,
                anc1
            )

            # Complement ancilla.
            em.x(anc1)

            # Apply G AND ancilla to output.
            lits = fixed(G)

            negs = [
                i
                for i, ch in lits
                if ch == '0'
            ]

            for i in negs:
                em.x(i)

            em.mcx(
                [i for i, _ in lits] + [anc1],
                out
            )

            for i in negs:
                em.x(i)

            # Restore ancilla.
            em.x(anc1)

            # Uncompute C.
            em.term(
                Cc,
                anc1
            )

        # --------------------------------------------------------------
        # Factorized expression:
        #
        #     L . (R1 (+) R2 ...)
        #
        # Residuals accumulate on anc1.
        # L goes onto anc2.
        # Combine onto output.
        # Then uncompute.
        # --------------------------------------------------------------
        else:

            L = toks[0]
            residuals = toks[1:]

            # Compute residual XOR terms.
            for R in residuals:
                em.term(
                    R,
                    anc1
                )

            # Compute shared factor.
            em.term(
                L,
                anc2
            )

            # Combine.
            em.mcx(
                [anc1, anc2],
                out
            )

            # Uncompute shared factor.
            em.term(
                L,
                anc2
            )

            # Uncompute residuals in reverse order.
            for R in reversed(residuals):
                em.term(
                    R,
                    anc1
                )

    return em


def main():

    ap = argparse.ArgumentParser()

    ap.add_argument(
        'path',
        help='ESOP or factorized representation'
    )

    ap.add_argument(
        '--name',
        default='circuit'
    )

    ap.add_argument(
        '--decompose',
        action='store_true',
        help='decompose MCX gates into X/CX/CCX'
    )

    args = ap.parse_args()

    rows = load(args.path)

    if not rows:
        sys.exit('no cubes found')

    n = len(rows[0][0])

    em = build(
        rows,
        n,
        decompose=args.decompose
    )

    # Inputs + output + two representation ancillas.
    base_qubits = n + 3

    if args.decompose:
        # Number of workspace qubits actually allocated.
        workspace_qubits = em.workspace_used
    else:
        workspace_qubits = 0

    total = base_qubits + workspace_qubits

    print('OPENQASM 2.0;')
    print('include "qelib1.inc";')
    print(f'// source: {args.path}')
    print(
        f'// {n} inputs, 1 output, 2 ancillas'
    )

    if args.decompose:
        print(
            f'// {workspace_qubits} additional MCX workspace ancillas'
        )

    print(f'qreg q[{total}];')

    for line in em.lines:
        print(line)

    # Representation-level statistics.
    hist = {}

    for c in em.tcount_gates:
        hist[c] = hist.get(c, 0) + 1

    print(
        f'// representation gates: {len(em.tcount_gates)}',
        file=sys.stderr
    )

    print(
        f'// controls histogram: {dict(sorted(hist.items()))}',
        file=sys.stderr
    )

    print(
        f'// emitted circuit gates: {len(em.lines)}',
        file=sys.stderr
    )

    print(
        f'// decomposition workspace: {workspace_qubits}',
        file=sys.stderr
    )


if __name__ == '__main__':
    main()