OPENQASM 2.0;
include "qelib1.inc";
// source: results/esop/rd53f1_100.esop
// 5 inputs, 1 output, 2 ancillas
qreg q[8];
x q[1];
x q[2];
mcx q[0],q[1],q[2],q[3],q[4],q[5];
x q[1];
x q[2];
mcx q[0],q[3],q[4],q[5];
mcx q[0],q[1],q[2],q[4],q[5];
mcx q[1],q[2],q[3],q[5];
x q[0];
x q[4];
mcx q[0],q[1],q[2],q[3],q[4],q[5];
x q[0];
x q[4];
