OPENQASM 2.0;
include "qelib1.inc";
// source: results\esop\xor5_d_100.esop
// 5 inputs, 1 output, 2 ancillas
// 0 additional MCX workspace ancillas
qreg q[8];
cx q[4],q[5];
x q[1];
cx q[1],q[5];
x q[1];
x q[0];
cx q[0],q[5];
x q[0];
x q[3];
cx q[3],q[5];
x q[3];
x q[2];
cx q[2],q[5];
x q[2];
