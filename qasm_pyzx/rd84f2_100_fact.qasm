OPENQASM 2.0;
include "qelib1.inc";
// source: results\final_parser\rd84f2_100.final.eosops
// 8 inputs, 1 output, 2 ancillas
// 0 additional MCX workspace ancillas
qreg q[11];
x q[6];
cx q[6],q[8];
x q[6];
x q[1];
cx q[1],q[8];
x q[1];
x q[7];
cx q[7],q[8];
x q[7];
x q[0];
cx q[0],q[8];
x q[0];
x q[5];
cx q[5],q[8];
x q[5];
x q[2];
cx q[2],q[8];
x q[2];
x q[4];
cx q[4],q[8];
x q[4];
x q[3];
cx q[3],q[8];
x q[3];
