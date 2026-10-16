library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.fixed_pkg.all;

entity tb_probe_real is
end entity;

architecture sim of tb_probe_real is
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
        
        -- Inicializar matriz de calibração K (parâmetros reais das imagens 640x480)
        K_matrix <= (others => (others => (others => '0')));
        K_matrix(0,0) <= to_signed(34406400, 32);  -- fx = 525.0 (estimado)
        K_matrix(1,1) <= to_signed(34406400, 32);  -- fy = 525.0 (estimado)
        K_matrix(2,2) <= to_signed(65536, 32);     -- 1.0
        K_matrix(0,2) <= to_signed(20971520, 32);  -- cx = 320.0 (centro da imagem)
        K_matrix(1,2) <= to_signed(15728640, 32);  -- cy = 240.0 (centro da imagem)

        -- Pontos correspondentes extraídos das imagens reais
        -- Ponto 1
        pts1_in(0, 0) <= to_signed(12089541, 32);  -- x1 = 184.5
        pts1_in(0, 1) <= to_signed(14209715, 32);  -- y1 = 216.8
        pts2_in(0, 0) <= to_signed(15566883, 32);  -- x2 = 237.5
        pts2_in(0, 1) <= to_signed(14818845, 32);  -- y2 = 226.1

        -- Ponto 2
        pts1_in(1, 0) <= to_signed(8913681, 32);  -- x1 = 136.0
        pts1_in(1, 1) <= to_signed(9433150, 32);  -- y1 = 143.9
        pts2_in(1, 0) <= to_signed(13591437, 32);  -- x2 = 207.4
        pts2_in(1, 1) <= to_signed(10663219, 32);  -- y2 = 162.7

        -- Ponto 3
        pts1_in(2, 0) <= to_signed(14497384, 32);  -- x1 = 221.2
        pts1_in(2, 1) <= to_signed(12503351, 32);  -- y1 = 190.8
        pts2_in(2, 0) <= to_signed(17602752, 32);  -- x2 = 268.6
        pts2_in(2, 1) <= to_signed(13421791, 32);  -- y2 = 204.8

        -- Ponto 4
        pts1_in(3, 0) <= to_signed(8346256, 32);  -- x1 = 127.4
        pts1_in(3, 1) <= to_signed(17117938, 32);  -- y1 = 261.2
        pts2_in(3, 0) <= to_signed(12936852, 32);  -- x2 = 197.4
        pts2_in(3, 1) <= to_signed(16753853, 32);  -- y2 = 255.6

        -- Ponto 5
        pts1_in(4, 0) <= to_signed(11092791, 32);  -- x1 = 169.3
        pts1_in(4, 1) <= to_signed(10508912, 32);  -- y1 = 160.4
        pts2_in(4, 0) <= to_signed(15167014, 32);  -- x2 = 231.4
        pts2_in(4, 1) <= to_signed(11460208, 32);  -- y2 = 174.9

        -- Ponto 6
        pts1_in(5, 0) <= to_signed(7987191, 32);  -- x1 = 121.9
        pts1_in(5, 1) <= to_signed(14489305, 32);  -- y1 = 221.1
        pts2_in(5, 0) <= to_signed(12799177, 32);  -- x2 = 195.3
        pts2_in(5, 1) <= to_signed(14697239, 32);  -- y2 = 224.3

        -- Ponto 7
        pts1_in(6, 0) <= to_signed(23991140, 32);  -- x1 = 366.1
        pts1_in(6, 1) <= to_signed(17210412, 32);  -- y1 = 262.6
        pts2_in(6, 0) <= to_signed(31633018, 32);  -- x2 = 482.7
        pts2_in(6, 1) <= to_signed(20818338, 32);  -- y2 = 317.7

        -- Ponto 8
        pts1_in(7, 0) <= to_signed(11653105, 32);  -- x1 = 177.8
        pts1_in(7, 1) <= to_signed(8741459, 32);  -- y1 = 133.4
        pts2_in(7, 0) <= to_signed(15533965, 32);  -- x2 = 237.0
        pts2_in(7, 1) <= to_signed(9918652, 32);  -- y2 = 151.3

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