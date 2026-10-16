library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.fixed_pkg.all;

entity tb_probe_sim is
end entity;

architecture sim of tb_probe_sim is
    function s2str(v : signed) return string is
        variable r  : string(1 to 32);
        variable lv : std_logic_vector(31 downto 0) := std_logic_vector(v);
    begin
        if Is_X(lv) then
            for i in 0 to 31 loop
                r(i+1) := std_logic'image(lv(31-i))(2);
            end loop;
            return "META[" & r & "]";
        else
            return integer'image(to_integer(v));
        end if;
    end function;

    function ismeta(v : signed) return boolean is
    begin
        return Is_X(std_logic_vector(v));
    end function;
    component SfM_Top
        port (
            clk           : in  std_logic;
            reset         : in  std_logic;
            start         : in  std_logic;
            pts1_in       : in  FixedArray2D;
            pts2_in       : in  FixedArray2D;
            K_matrix      : in  Mat3;
            points_3D     : out FixedArray3D;
            pose_R        : out Mat3;
            pose_t        : out Vec3;
            fundamental_F : out Mat3;
            essential_E   : out Mat3;
            ready         : out std_logic
        );
    end component;

    signal clk           : std_logic := '0';
    signal reset         : std_logic := '1';
    signal start         : std_logic := '0';
    signal pts1_in       : FixedArray2D := (others => (others => (others => '0')));
    signal pts2_in       : FixedArray2D := (others => (others => (others => '0')));
    signal K_matrix      : Mat3;
    signal points_3D     : FixedArray3D;
    signal pose_R        : Mat3;
    signal pose_t        : Vec3;
    signal fundamental_F : Mat3;
    signal essential_E   : Mat3;
    signal ready         : std_logic;

begin
    UUT: SfM_Top port map (
        clk           => clk,
        reset         => reset,
        start         => start,
        pts1_in       => pts1_in,
        pts2_in       => pts2_in,
        K_matrix      => K_matrix,
        points_3D     => points_3D,
        pose_R        => pose_R,
        pose_t        => pose_t,
        fundamental_F => fundamental_F,
        essential_E   => essential_E,
        ready         => ready
    );

    -- Clock de 10 ns (100 MHz)
    clk_process: process
    begin
        while true loop
            wait for 5 ns;
            clk <= not clk;
        end loop;
    end process;

    -- Processo de estímulos
    stimulus: process
    begin
        -- Dados extraídos das imagens locais img1.jpeg e img2.jpeg
        -- Pontos correspondentes encontrados via SIFT + RANSAC processados em VHDL
        
        -- Inicializar matriz de calibração K (parâmetros típicos VGA)
        K_matrix <= (others => (others => (others => '0')));
        K_matrix(0,0) <= to_signed(34406400, 32);  -- fx = 525.0
        K_matrix(1,1) <= to_signed(34406400, 32);  -- fy = 525.0
        K_matrix(2,2) <= to_signed(65536, 32);  -- 1.0
        K_matrix(0,2) <= to_signed(20971520, 32);  -- cx = 320.0
        K_matrix(1,2) <= to_signed(15728640, 32);  -- cy = 240.0

        -- Pontos correspondentes simulados
        -- Ponto 1
        pts1_in(0, 0) <= to_signed(16531565, 32);  -- x1 = 252.3
        pts1_in(0, 1) <= to_signed(26953084, 32);  -- y1 = 411.3
        pts2_in(0, 0) <= to_signed(16795943, 32);  -- x2 = 256.3
        pts2_in(0, 1) <= to_signed(26973984, 32);  -- y2 = 411.6

        -- Ponto 2
        pts1_in(1, 0) <= to_signed(8797358, 32);  -- x1 = 134.2
        pts1_in(1, 1) <= to_signed(4723295, 32);  -- y1 = 72.1
        pts2_in(1, 0) <= to_signed(9368587, 32);  -- x2 = 143.0
        pts2_in(1, 1) <= to_signed(4773590, 32);  -- y2 = 72.8

        -- Ponto 3
        pts1_in(2, 0) <= to_signed(4005273, 32);  -- x1 = 61.1
        pts1_in(2, 1) <= to_signed(27431124, 32);  -- y1 = 418.6
        pts2_in(2, 0) <= to_signed(4303914, 32);  -- x2 = 65.7
        pts2_in(2, 1) <= to_signed(27396707, 32);  -- y2 = 418.0

        -- Ponto 4
        pts1_in(3, 0) <= to_signed(9767382, 32);  -- x1 = 149.0
        pts1_in(3, 1) <= to_signed(10853551, 32);  -- y1 = 165.6
        pts2_in(3, 0) <= to_signed(10050456, 32);  -- x2 = 153.4
        pts2_in(3, 1) <= to_signed(10816701, 32);  -- y2 = 165.0

        -- Ponto 5
        pts1_in(4, 0) <= to_signed(24929931, 32);  -- x1 = 380.4
        pts1_in(4, 1) <= to_signed(6750710, 32);  -- y1 = 103.0
        pts2_in(4, 0) <= to_signed(25536259, 32);  -- x2 = 389.7
        pts2_in(4, 1) <= to_signed(6610488, 32);  -- y2 = 100.9

        -- Ponto 6
        pts1_in(5, 0) <= to_signed(31063737, 32);  -- x1 = 474.0
        pts1_in(5, 1) <= to_signed(8249411, 32);  -- y1 = 125.9
        pts2_in(5, 0) <= to_signed(31507867, 32);  -- x2 = 480.8
        pts2_in(5, 1) <= to_signed(8256681, 32);  -- y2 = 126.0

        -- Ponto 7
        pts1_in(6, 0) <= to_signed(24777472, 32);  -- x1 = 378.1
        pts1_in(6, 1) <= to_signed(7523478, 32);  -- y1 = 114.8
        pts2_in(6, 0) <= to_signed(25795490, 32);  -- x2 = 393.6
        pts2_in(6, 1) <= to_signed(7585569, 32);  -- y2 = 115.7

        -- Ponto 8
        pts1_in(7, 0) <= to_signed(6733361, 32);  -- x1 = 102.7
        pts1_in(7, 1) <= to_signed(20316720, 32);  -- y1 = 310.0
        pts2_in(7, 0) <= to_signed(7296446, 32);  -- x2 = 111.3
        pts2_in(7, 1) <= to_signed(20247402, 32);  -- y2 = 309.0

        wait for 100 ns;
        reset <= '0';
        wait for 20 ns;
        
        -- Iniciar processamento
        start <= '1';
        wait for 20 ns;
        start <= '0';
        
        -- Aguardar conclusão
        wait until ready = '1';
        wait for 100 ns;
        
                for i in 0 to 2 loop
            for j in 0 to 2 loop
                report "F(" & integer'image(i) & "," & integer'image(j) & ") = " & s2str(fundamental_F(i,j));
            end loop;
        end loop;
        for i in 0 to 2 loop
            for j in 0 to 2 loop
                report "E(" & integer'image(i) & "," & integer'image(j) & ") = " & s2str(essential_E(i,j));
            end loop;
        end loop;
        for i in 0 to 2 loop
            for j in 0 to 2 loop
                report "R(" & integer'image(i) & "," & integer'image(j) & ") = " & s2str(pose_R(i,j));
            end loop;
        end loop;
        for i in 0 to 2 loop
            report "t(" & integer'image(i) & ") = " & s2str(pose_t(i));
        end loop;
        for p in 0 to 8 loop
            report "X3D(" & integer'image(p) & ") = [" & s2str(points_3D(p,0)) & ", " & s2str(points_3D(p,1)) & ", " & s2str(points_3D(p,2)) & ", " & s2str(points_3D(p,3)) & "]";
        end loop;
        report "X3D(99) = [" & s2str(points_3D(99,0)) & ", " & s2str(points_3D(99,1)) & ", " & s2str(points_3D(99,2)) & ", " & s2str(points_3D(99,3)) & "]";
        wait for 1 ns;
        report "Teste SfM completo executado com sucesso!";
        report "Pipeline executado: Fundamental -> Essential -> Pose -> Triangulation";
        wait; -- Para a simulação
    end process;
end architecture;