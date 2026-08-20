OPENQASM 2.0;
include "qelib1.inc";
// source: results/final_parser/shor_modexp_7_mod15_bit0.final.eosops
// 8 inputs, 1 output, 2 ancillas
qreg q[11];
x q[6];
cx q[6],q[8];
x q[6];
ccx q[6],q[7],q[8];
