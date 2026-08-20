OPENQASM 2.0;
include "qelib1.inc";
// source: results\esop\rd73f2_100.esop
// 7 inputs, 1 output, 2 ancillas
// 0 additional MCX workspace ancillas
qreg q[10];
x q[3];
cx q[3],q[7];
x q[3];
cx q[5],q[7];
x q[0];
cx q[0],q[7];
x q[0];
x q[1];
cx q[1],q[7];
x q[1];
x q[4];
cx q[4],q[7];
x q[4];
x q[6];
cx q[6],q[7];
x q[6];
x q[2];
cx q[2],q[7];
x q[2];
