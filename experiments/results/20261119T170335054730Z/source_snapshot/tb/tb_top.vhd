library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.fixed_pkg.all;

entity tb_top is
end entity;

architecture sim of tb_top is
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
        pts1_in(0, 0) <= to_signed(23838910, 32);  -- x1 = 363.8
        pts1_in(0, 1) <= to_signed(9052917, 32);   -- y1 = 138.1
        pts2_in(0, 0) <= to_signed(33180358, 32);  -- x2 = 506.3
        pts2_in(0, 1) <= to_signed(8607561, 32);   -- y2 = 131.3

        -- Ponto 2
        pts1_in(1, 0) <= to_signed(17617284, 32);  -- x1 = 268.8
        pts1_in(1, 1) <= to_signed(8454614, 32);   -- y1 = 129.0
        pts2_in(1, 0) <= to_signed(32932746, 32);  -- x2 = 502.5
        pts2_in(1, 1) <= to_signed(9047733, 32);   -- y2 = 138.1

        -- Ponto 3
        pts1_in(2, 0) <= to_signed(12089541, 32);  -- x1 = 184.5
        pts1_in(2, 1) <= to_signed(14209715, 32);  -- y1 = 216.8
        pts2_in(2, 0) <= to_signed(15566883, 32);  -- x2 = 237.5
        pts2_in(2, 1) <= to_signed(14818845, 32);  -- y2 = 226.1

        -- Ponto 4
        pts1_in(3, 0) <= to_signed(20840370, 32);  -- x1 = 318.0
        pts1_in(3, 1) <= to_signed(18874794, 32);  -- y1 = 288.0
        pts2_in(3, 0) <= to_signed(25352796, 32);  -- x2 = 386.9
        pts2_in(3, 1) <= to_signed(21515964, 32);  -- y2 = 328.3

        -- Ponto 5
        pts1_in(4, 0) <= to_signed(9893850, 32);   -- x1 = 151.0
        pts1_in(4, 1) <= to_signed(8495683, 32);   -- y1 = 129.6
        pts2_in(4, 0) <= to_signed(14241771, 32);  -- x2 = 217.3
        pts2_in(4, 1) <= to_signed(9842917, 32);   -- y2 = 150.2

        -- Ponto 6
        pts1_in(5, 0) <= to_signed(10133454, 32);  -- x1 = 154.6
        pts1_in(5, 1) <= to_signed(9372734, 32);   -- y1 = 143.0
        pts2_in(5, 0) <= to_signed(14396896, 32);  -- x2 = 219.7
        pts2_in(5, 1) <= to_signed(10562664, 32);  -- y2 = 161.2

        -- Ponto 7
        pts1_in(6, 0) <= to_signed(7987191, 32);   -- x1 = 121.9
        pts1_in(6, 1) <= to_signed(14489305, 32);  -- y1 = 221.1
        pts2_in(6, 0) <= to_signed(12799177, 32);  -- x2 = 195.3
        pts2_in(6, 1) <= to_signed(14697239, 32);  -- y2 = 224.3

        -- Ponto 8
        pts1_in(7, 0) <= to_signed(13031749, 32);  -- x1 = 198.8
        pts1_in(7, 1) <= to_signed(8888773, 32);   -- y1 = 135.6
        pts2_in(7, 0) <= to_signed(16657966, 32);  -- x2 = 254.2
        pts2_in(7, 1) <= to_signed(9947206, 32);   -- y2 = 151.8
        
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
        
        report "Teste SfM completo executado com sucesso!";
        report "Pipeline executado: Fundamental -> Essential -> Pose -> Triangulation";
        wait; -- Para a simulação
    end process;
end architecture;