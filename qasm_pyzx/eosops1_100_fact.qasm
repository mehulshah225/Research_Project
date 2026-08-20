OPENQASM 2.0;
include "qelib1.inc";
// source: results\final_parser\eosops1_100.final.eosops
// 5 inputs, 1 output, 2 ancillas
// 2 additional MCX workspace ancillas
qreg q[10];
ccx q[0],q[1],q[6];
x q[6];
ccx q[3],q[4],q[8];
ccx q[8],q[6],q[5];
ccx q[3],q[4],q[8];
x q[6];
ccx q[0],q[1],q[6];
ccx q[1],q[3],q[6];
x q[6];
ccx q[0],q[2],q[9];
ccx q[9],q[6],q[5];
ccx q[0],q[2],q[9];
x q[6];
ccx q[1],q[3],q[6];
