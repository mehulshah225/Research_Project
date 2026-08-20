OPENQASM 2.0;
include "qelib1.inc";
// source: results\final_parser\exam3_d_100.final.eosops
// 4 inputs, 1 output, 2 ancillas
// 1 additional MCX workspace ancillas
qreg q[8];
cx q[2],q[5];
ccx q[0],q[3],q[5];
x q[1];
cx q[1],q[6];
x q[1];
ccx q[5],q[6],q[4];
x q[1];
cx q[1],q[6];
x q[1];
ccx q[0],q[3],q[5];
cx q[2],q[5];
x q[0];
x q[3];
ccx q[0],q[1],q[7];
ccx q[7],q[3],q[4];
ccx q[0],q[1],q[7];
x q[0];
x q[3];
