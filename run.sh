#!/bin/bash

mkdir -p work
ghdl -a --workdir=work src/fixed_pkg.vhd
ghdl -a --workdir=work src/algebra_pkg.vhd
ghdl -a --workdir=work src/projective_pkg.vhd
ghdl -a --workdir=work src/fundamental_matrix.vhd
ghdl -a --workdir=work src/essential_matrix.vhd
ghdl -a --workdir=work src/pose_extraction.vhd
ghdl -a --workdir=work src/triangulation.vhd
ghdl -a --workdir=work src/top.vhd
ghdl -a --workdir=work tb/tb_top.vhd
ghdl -e --workdir=work tb_top
ghdl -r --workdir=work tb_top --vcd=wave.vcd
gtkwave wave.vcd
