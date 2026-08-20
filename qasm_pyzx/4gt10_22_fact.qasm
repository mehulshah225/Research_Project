OPENQASM 2.0;
include "qelib1.inc";
// source: results\final_parser\4gt10_22.final.eosops
// 4 inputs, 1 output, 2 ancillas
// 2 additional MCX workspace ancillas
qreg q[9];
cx q[1],q[5];
x q[1];
ccx q[1],q[2],q[7];
ccx q[7],q[3],q[5];
ccx q[1],q[2],q[7];
x q[1];
cx q[0],q[6];
ccx q[5],q[6],q[4];
cx q[0],q[6];
x q[1];
ccx q[1],q[2],q[8];
ccx q[8],q[3],q[5];
ccx q[1],q[2],q[8];
x q[1];
cx q[1],q[5];
