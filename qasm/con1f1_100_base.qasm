OPENQASM 2.0;
include "qelib1.inc";
// source: results/esop/con1f1_100.esop
// 7 inputs, 1 output, 2 ancillas
qreg q[10];
x q[1];
ccx q[1],q[3],q[7];
x q[1];
x q[0];
x q[1];
mcx q[0],q[1],q[2],q[3],q[7];
x q[0];
x q[1];
x q[4];
mcx q[0],q[1],q[2],q[3],q[4],q[7];
x q[4];
ccx q[1],q[4],q[7];
x q[0];
x q[4];
mcx q[0],q[1],q[4],q[5],q[7];
x q[0];
x q[4];
