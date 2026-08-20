OPENQASM 2.0;
include "qelib1.inc";
// source: results\esop\con1f1_100.esop
// 7 inputs, 1 output, 2 ancillas
// 7 additional MCX workspace ancillas
qreg q[17];
x q[1];
ccx q[1],q[3],q[7];
x q[1];
x q[0];
x q[1];
ccx q[0],q[1],q[10];
ccx q[10],q[2],q[11];
ccx q[11],q[3],q[7];
ccx q[10],q[2],q[11];
ccx q[0],q[1],q[10];
x q[0];
x q[1];
x q[4];
ccx q[0],q[1],q[12];
ccx q[12],q[2],q[13];
ccx q[13],q[3],q[14];
ccx q[14],q[4],q[7];
ccx q[13],q[3],q[14];
ccx q[12],q[2],q[13];
ccx q[0],q[1],q[12];
x q[4];
ccx q[1],q[4],q[7];
x q[0];
x q[4];
ccx q[0],q[1],q[15];
ccx q[15],q[4],q[16];
ccx q[16],q[5],q[7];
ccx q[15],q[4],q[16];
ccx q[0],q[1],q[15];
x q[0];
x q[4];
