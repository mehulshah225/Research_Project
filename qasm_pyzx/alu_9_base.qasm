OPENQASM 2.0;
include "qelib1.inc";
// source: results\esop\alu_9.esop
// 5 inputs, 1 output, 2 ancillas
// 2 additional MCX workspace ancillas
qreg q[10];
x q[2];
x q[3];
x q[4];
ccx q[2],q[3],q[8];
ccx q[8],q[4],q[5];
ccx q[2],q[3],q[8];
x q[2];
x q[3];
x q[4];
x q[0];
x q[4];
ccx q[0],q[4],q[5];
x q[0];
x q[4];
x q[0];
x q[3];
ccx q[0],q[3],q[5];
x q[0];
x q[3];
x q[1];
ccx q[1],q[3],q[9];
ccx q[9],q[4],q[5];
ccx q[1],q[3],q[9];
x q[1];
