#!/bin/bash

mkdir -p work
echo "Compilando pacotes base..."
ghdl -a --workdir=work src/fixed_pkg.vhd
ghdl -a --workdir=work src/algebra_pkg.vhd
ghdl -a --workdir=work src/algebra_pkg_body.vhd
ghdl -a --workdir=work src/projective_pkg.vhd

echo "Compilando módulos principais..."
ghdl -a --workdir=work src/fundamental_matrix.vhd
ghdl -a --workdir=work src/essential_matrix.vhd
ghdl -a --workdir=work src/pose_extraction.vhd
ghdl -a --workdir=work src/triangulation.vhd
ghdl -a --workdir=work src/top.vhd

echo "Compilando testbench..."
ghdl -a --workdir=work tb/tb_top.vhd

echo "Elaborando design..."
ghdl -e --workdir=work tb_top

echo "Executando simulação..."
ghdl -r --workdir=work tb_top --vcd=wave.vcd --stop-time=10us

echo "Simulação concluída. Arquivo wave.vcd gerado."
