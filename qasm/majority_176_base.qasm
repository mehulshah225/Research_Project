OPENQASM 2.0;
include "qelib1.inc";
// source: results/esop/majority_176.esop
// 5 inputs, 1 output, 2 ancillas
qreg q[8];
cx q[3],q[5];
x q[3];
mcx q[0],q[1],q[3],q[5];
x q[3];
x q[0];
x q[3];
mcx q[0],q[2],q[3],q[4],q[5];
x q[0];
x q[3];
x q[1];
x q[3];
mcx q[1],q[2],q[3],q[4],q[5];
x q[1];
x q[3];
x q[2];
x q[3];
x q[4];
mcx q[0],q[1],q[2],q[3],q[4],q[5];
x q[2];
x q[3];
x q[4];
