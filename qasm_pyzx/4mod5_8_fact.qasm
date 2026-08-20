OPENQASM 2.0;
include "qelib1.inc";
// source: results\final_parser\4mod5_8.final.eosops
// 4 inputs, 1 output, 2 ancillas
// 0 additional MCX workspace ancillas
qreg q[7];
x q[0];
cx q[0],q[5];
x q[0];
cx q[2],q[5];
cx q[3],q[6];
ccx q[5],q[6],q[4];
cx q[3],q[6];
cx q[2],q[5];
x q[0];
cx q[0],q[5];
x q[0];
x q[0];
cx q[0],q[5];
x q[0];
cx q[2],q[5];
x q[1];
cx q[1],q[6];
x q[1];
ccx q[5],q[6],q[4];
x q[1];
cx q[1],q[6];
x q[1];
cx q[2],q[5];
x q[0];
cx q[0],q[5];
x q[0];
