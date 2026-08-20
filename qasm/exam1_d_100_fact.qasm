OPENQASM 2.0;
include "qelib1.inc";
// source: results/final_parser/exam1_d_100.final.eosops
// 3 inputs, 1 output, 2 ancillas
qreg q[6];
cx q[2],q[3];
cx q[1],q[3];
x q[0];
cx q[0],q[3];
x q[0];
