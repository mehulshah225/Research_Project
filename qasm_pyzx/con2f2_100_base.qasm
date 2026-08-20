OPENQASM 2.0;
include "qelib1.inc";
// source: results\esop\con2f2_100.esop
// 7 inputs, 1 output, 2 ancillas
// 4 additional MCX workspace ancillas
qreg q[14];
x q[1];
x q[3];
ccx q[0],q[1],q[10];
ccx q[10],q[3],q[11];
ccx q[11],q[4],q[7];
ccx q[10],q[3],q[11];
ccx q[0],q[1],q[10];
x q[1];
x q[3];
x q[0];
x q[6];
ccx q[0],q[4],q[12];
ccx q[12],q[6],q[7];
ccx q[0],q[4],q[12];
x q[0];
x q[6];
x q[4];
cx q[4],q[7];
x q[4];
x q[0];
ccx q[0],q[1],q[13];
ccx q[13],q[6],q[7];
ccx q[0],q[1],q[13];
x q[0];
