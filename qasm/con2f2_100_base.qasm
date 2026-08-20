OPENQASM 2.0;
include "qelib1.inc";
// source: results/esop/con2f2_100.esop
// 7 inputs, 1 output, 2 ancillas
qreg q[10];
x q[1];
x q[3];
mcx q[0],q[1],q[3],q[4],q[7];
x q[1];
x q[3];
x q[0];
x q[6];
mcx q[0],q[4],q[6],q[7];
x q[0];
x q[6];
x q[4];
cx q[4],q[7];
x q[4];
x q[0];
mcx q[0],q[1],q[6],q[7];
x q[0];
