library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use std.env.finish;
use work.fixed_pkg.all;

entity tb_essential_io is
    generic (
        input_file : string := "matrices.in";
        output_file : string := "matrices.out";
        max_cycles : positive := 10
    );
end entity;

architecture sim of tb_essential_io is
    signal clk : std_logic := '0';
    signal reset, start : std_logic := '0';
    signal F, K : Mat3 := (others => (others => (others => '0')));
    signal E : Mat3;
    signal ready : std_logic;

    function defined(value : Mat3) return boolean is
    begin
        for i in 0 to 2 loop
            for j in 0 to 2 loop
                for bit_index in 31 downto 0 loop
                    if value(i,j)(bit_index) /= '0' and value(i,j)(bit_index) /= '1' then
                        return false;
                    end if;
                end loop;
            end loop;
        end loop;
        return true;
    end function;

    procedure read_integer(file source : text; variable value : out integer) is
        variable row : line;
        variable good : boolean;
    begin
        assert not endfile(source) report "Incomplete input" severity failure;
        readline(source, row);
        read(row, value, good);
        assert good report "Invalid signed integer input" severity failure;
    end procedure;
begin
    clk <= not clk after 5 ns;
    dut : entity work.EssentialMatrixCalculator
        port map (clk => clk, reset => reset, start => start,
                  F_in => F, K_const => K, E_out => E, ready => ready);

    stimulus : process
        file source : text;
        file destination : text;
        variable row : line;
        variable count, reset_flag, value, cycles : integer;
        variable previous : Mat3 := (others => (others => (others => '0')));
        variable previous_ready : std_logic := '0';
    begin
        file_open(source, input_file, read_mode);
        file_open(destination, output_file, write_mode);
        read_integer(source, count);
        assert count > 0 report "Empty input batch" severity failure;
        write(row, string'("essential-q15.16-v1"));
        writeline(destination, row);
        for case_index in 0 to count - 1 loop
            read_integer(source, reset_flag);
            assert reset_flag = 0 or reset_flag = 1 report "Invalid reset flag" severity failure;
            assert case_index /= 0 or reset_flag = 1 report "First case requires reset" severity failure;
            for i in 0 to 2 loop
                for j in 0 to 2 loop
                    read_integer(source, value);
                    F(i,j) <= to_signed(value, 32);
                end loop;
            end loop;
            for i in 0 to 2 loop
                for j in 0 to 2 loop
                    read_integer(source, value);
                    K(i,j) <= to_signed(value, 32);
                end loop;
            end loop;
            wait until falling_edge(clk);
            if reset_flag = 1 then
                reset <= '1';
                start <= '1'; -- Confere prioridade do reset sobre start.
                wait until rising_edge(clk);
                wait for 1 ns;
                assert ready = '0' report "Reset did not clear ready" severity failure;
                assert defined(E) report "Undefined output after reset" severity failure;
                for i in 0 to 2 loop
                    for j in 0 to 2 loop
                        assert E(i,j) = to_signed(0, 32) report "Reset did not clear E" severity failure;
                    end loop;
                end loop;
                previous := E;
                previous_ready := '0';
                wait until falling_edge(clk);
                reset <= '0';
            end if;
            start <= '0';
            wait until rising_edge(clk);
            wait for 1 ns;
            assert defined(E) report "Undefined idle output" severity failure;
            assert E = previous and ready = previous_ready
                report "Output/ready changed without start" severity failure;
            wait until falling_edge(clk);
            start <= '1';
            cycles := 0;
            loop
                wait until rising_edge(clk);
                wait for 1 ns; -- E_out recebe E_temp em outro delta cycle.
                cycles := cycles + 1;
                assert ready = '0' or ready = '1' report "Undefined ready" severity failure;
                exit when ready = '1';
                assert cycles < max_cycles report "Kernel cycle timeout" severity failure;
            end loop;
            assert defined(E) report "Undefined kernel output" severity failure;
            write(row, case_index);
            write(row, string'(" "));
            write(row, cycles);
            for i in 0 to 2 loop
                for j in 0 to 2 loop
                    write(row, string'(" "));
                    write(row, to_integer(E(i,j)));
                end loop;
            end loop;
            writeline(destination, row);
            previous := E;
            previous_ready := '1';
            wait until falling_edge(clk);
            start <= '0';
        end loop;
        assert endfile(source) report "Unexpected extra input" severity failure;
        file_close(destination);
        finish;
        wait;
    end process;
end architecture;
