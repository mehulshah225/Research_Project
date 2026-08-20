OPENQASM 2.0;
include "qelib1.inc";
// source: results\esop\exam3_d_100.esop
// 4 inputs, 1 output, 2 ancillas
// 2 additional MCX workspace ancillas
qreg q[9];
x q[0];
x q[3];
ccx q[0],q[1],q[7];
ccx q[7],q[3],q[4];
ccx q[0],q[1],q[7];
x q[0];
x q[3];
x q[1];
ccx q[1],q[2],q[4];
x q[1];
x q[1];
ccx q[0],q[1],q[8];
ccx q[8],q[3],q[4];
ccx q[0],q[1],q[8];
x q[1];
