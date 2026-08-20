OPENQASM 2.0;
include "qelib1.inc";
// source: results\esop\eosops1_100.esop
// 5 inputs, 1 output, 2 ancillas
// 4 additional MCX workspace ancillas
qreg q[12];
ccx q[3],q[4],q[5];
ccx q[0],q[1],q[8];
ccx q[8],q[3],q[9];
ccx q[9],q[4],q[5];
ccx q[8],q[3],q[9];
ccx q[0],q[1],q[8];
ccx q[0],q[2],q[5];
ccx q[0],q[1],q[10];
ccx q[10],q[2],q[11];
ccx q[11],q[3],q[5];
ccx q[10],q[2],q[11];
ccx q[0],q[1],q[10];
