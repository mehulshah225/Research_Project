OPENQASM 2.0;
include "qelib1.inc";
// source: results/esop/eosops1_100.esop
// 5 inputs, 1 output, 2 ancillas
qreg q[8];
ccx q[3],q[4],q[5];
mcx q[0],q[1],q[3],q[4],q[5];
ccx q[0],q[2],q[5];
mcx q[0],q[1],q[2],q[3],q[5];
