library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.fixed_pkg.all;  -- exemplo
use work.algebra_pkg.all; -- se necessário


entity EssentialMatrixCalculator is
    Port (
        clk     : in  std_logic;
        reset   : in  std_logic;
        start   : in  std_logic;
        F_in    : in  Mat3;
        K_const : in  Mat3;  -- matriz de calibração intrínseca (constante ou registrador)
        E_out   : out Mat3;
        ready   : out std_logic
    );
end EssentialMatrixCalculator;
architecture RTL of EssentialMatrixCalculator is
    signal E_temp : Mat3;
begin
    -- Computa E = K^T * F * K
    process(clk)
        variable temp : Mat3;
    begin
        if rising_edge(clk) then
            if reset = '1' then
                ready <= '0';
                E_temp <= (others => (others => (others => '0')));
            elsif start = '1' then
                temp := Mat3Mul(F_in, K_const);     -- F * K
                E_temp <= Mat3Mul(Transpose(K_const), temp); -- K^T * (F * K)
                ready <= '1';
            end if;
        end if;
    end process;
    
    E_out <= E_temp;
end RTL;
