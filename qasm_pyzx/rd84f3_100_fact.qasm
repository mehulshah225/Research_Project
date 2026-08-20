OPENQASM 2.0;
include "qelib1.inc";
// source: results\final_parser\rd84f3_100.final.eosops
// 8 inputs, 1 output, 2 ancillas
// 6 additional MCX workspace ancillas
qreg q[17];
ccx q[0],q[1],q[11];
ccx q[11],q[2],q[12];
ccx q[12],q[3],q[13];
ccx q[13],q[4],q[14];
ccx q[14],q[5],q[15];
ccx q[15],q[6],q[16];
ccx q[16],q[7],q[8];
ccx q[15],q[6],q[16];
ccx q[14],q[5],q[15];
ccx q[13],q[4],q[14];
ccx q[12],q[3],q[13];
ccx q[11],q[2],q[12];
ccx q[0],q[1],q[11];
