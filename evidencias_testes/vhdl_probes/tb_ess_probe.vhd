library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.fixed_pkg.all;

-- Probe temporario (fora do repositorio): testa EssentialMatrixCalculator isoladamente.
-- F = constantes de SOLVE_SVD (fundamental_matrix.vhd); K = valores de tb_top.vhd.
entity tb_ess_probe is
end entity;

architecture sim of tb_ess_probe is
    component EssentialMatrixCalculator
        port (
            clk     : in  std_logic;
            reset   : in  std_logic;
            start   : in  std_logic;
            F_in    : in  Mat3;
            K_const : in  Mat3;
            E_out   : out Mat3;
            ready   : out std_logic
        );
    end component;

    signal clk   : std_logic := '0';
    signal reset : std_logic := '1';
    signal start : std_logic := '0';
    signal F_in, K_const, E_out : Mat3;
    signal ready : std_logic;
begin
    UUT: EssentialMatrixCalculator port map (clk, reset, start, F_in, K_const, E_out, ready);

    clk <= not clk after 5 ns;

    process
    begin
        K_const <= (others => (others => (others => '0')));
        K_const(0,0) <= to_signed(34406400, 32);
        K_const(1,1) <= to_signed(34406400, 32);
        K_const(2,2) <= to_signed(65536, 32);
        K_const(0,2) <= to_signed(20971520, 32);
        K_const(1,2) <= to_signed(15728640, 32);
        F_in(0,0) <= to_signed(32768, 32); F_in(0,1) <= to_signed(16384, 32); F_in(0,2) <= to_signed(8192, 32);
        F_in(1,0) <= to_signed(4096, 32);  F_in(1,1) <= to_signed(2048, 32);  F_in(1,2) <= to_signed(1024, 32);
        F_in(2,0) <= to_signed(512, 32);   F_in(2,1) <= to_signed(256, 32);   F_in(2,2) <= to_signed(128, 32);
        wait for 30 ns;
        reset <= '0';
        wait for 20 ns;
        start <= '1';
        wait until ready = '1';
        wait for 20 ns;
        for i in 0 to 2 loop
            for j in 0 to 2 loop
                report "E(" & integer'image(i) & "," & integer'image(j) & ") = " & integer'image(to_integer(E_out(i,j)));
            end loop;
        end loop;
        wait;
    end process;
end architecture;
