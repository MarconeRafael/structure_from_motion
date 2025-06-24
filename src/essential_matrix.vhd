library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.fixed_pkg.all;  -- exemplo
use work.algebra_pkg.all; -- se necessário


entity EssentialMatrixCalculator is
    Port (
        F_in    : in  Mat3;
        K_const : in  Mat3;  -- matriz de calibração intrínseca (constante ou registrador)
        E_out   : out Mat3
    );
end EssentialMatrixCalculator;
architecture RTL of EssentialMatrixCalculator is
begin
    -- Computa E = K^T * F * K
    process(F_in, K_const)
        variable temp : Mat3;
    begin
        temp := Mat3Mul(F_in, K_const);     -- Função de multiplicação matricial 3x3
        E_out := Mat3Mul(Transpose(K_const), temp);
    end process;
end RTL;
