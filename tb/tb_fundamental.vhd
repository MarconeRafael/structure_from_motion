library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.fixed_pkg.all;

entity tb_fundamental is
end entity;

architecture sim of tb_fundamental is
    component FundamentalMatrixCalculator
        port (
            clk     : in std_logic;
            reset   : in std_logic;
            start   : in std_logic;
            pts1_x  : in FixedArray2D;
            pts2_x  : in FixedArray2D;
            F_out   : out Mat3;
            ready   : out std_logic
        );
    end component;

    signal clk     : std_logic := '0';
    signal reset   : std_logic := '1';
    signal start   : std_logic := '0';
    signal pts1_x, pts2_x : FixedArray2D := (others => (others => (others => '0')));
    signal F_out   : Mat3;
    signal ready   : std_logic;

begin
    UUT: FundamentalMatrixCalculator port map (
        clk => clk,
        reset => reset,
        start => start,
        pts1_x => pts1_x,
        pts2_x => pts2_x,
        F_out => F_out,
        ready => ready
    );

    -- Clock 10ns
    clk_process: process
    begin
        wait for 5 ns;
        clk <= not clk;
    end process;

    stimulus: process
    begin
        wait for 20 ns;
        reset <= '0';
        start <= '1';
        wait for 1000 ns; -- tempo de simulação
        wait;
    end process;
end architecture;
