OPENQASM 2.0;
include "qelib1.inc";
// source: results/esop\4mod5_8.esop
// 4 inputs, 1 output, 2 ancillas
// 0 additional MCX workspace ancillas
qreg q[7];
x q[0];
ccx q[0],q[3],q[4];
x q[0];
x q[0];
x q[1];
ccx q[0],q[1],q[4];
x q[0];
x q[1];
ccx q[2],q[3],q[4];
x q[1];
ccx q[1],q[2],q[4];
x q[1];
