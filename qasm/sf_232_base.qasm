OPENQASM 2.0;
include "qelib1.inc";
// source: results/esop/sf_232.esop
// 4 inputs, 1 output, 2 ancillas
qreg q[7];
x q[1];
ccx q[1],q[3],q[4];
x q[1];
x q[1];
mcx q[0],q[1],q[2],q[4];
x q[1];
cx q[2],q[4];
x q[0];
x q[3];
mcx q[0],q[1],q[3],q[4];
x q[0];
x q[3];
