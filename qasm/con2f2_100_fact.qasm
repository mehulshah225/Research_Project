OPENQASM 2.0;
include "qelib1.inc";
// source: results/final_parser/con2f2_100.final.eosops
// 7 inputs, 1 output, 2 ancillas
qreg q[10];
x q[6];
ccx q[4],q[6],q[8];
x q[6];
ccx q[1],q[6],q[8];
x q[0];
cx q[0],q[9];
x q[0];
ccx q[8],q[9],q[7];
x q[0];
cx q[0],q[9];
x q[0];
ccx q[1],q[6],q[8];
x q[6];
ccx q[4],q[6],q[8];
x q[6];
x q[1];
x q[3];
mcx q[0],q[1],q[3],q[4],q[7];
x q[1];
x q[3];
x q[4];
cx q[4],q[7];
x q[4];
