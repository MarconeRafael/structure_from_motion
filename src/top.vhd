library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.fixed_pkg.all;
use work.algebra_pkg.all;

entity SfM_Top is
    Port (
        clk           : in  std_logic;
        reset         : in  std_logic;
        start         : in  std_logic;
        
        -- Entrada: pontos correspondentes
        pts1_in       : in  FixedArray2D; -- Pontos da imagem 1
        pts2_in       : in  FixedArray2D; -- Pontos da imagem 2
        
        -- Entrada: matriz de calibração
        K_matrix      : in  Mat3;
        
        -- Saídas
        points_3D     : out FixedArray3D; -- Pontos 3D reconstruídos
        pose_R        : out Mat3;         -- Matriz de rotação da câmera
        pose_t        : out Vec3;         -- Vetor de translação da câmera
        fundamental_F : out Mat3;         -- Matriz fundamental
        essential_E   : out Mat3;         -- Matriz essencial
        ready         : out std_logic     -- Sinal de conclusão
    );
end SfM_Top;

architecture Behavioral of SfM_Top is
    -- Estados do pipeline
    type state_type is (IDLE, CALC_FUNDAMENTAL, CALC_ESSENTIAL, EXTRACT_POSE, TRIANGULATE, DONE);
    signal state : state_type := IDLE;
    
    -- Sinais de controle dos módulos
    signal fund_start, fund_ready : std_logic := '0';
    signal ess_start, ess_ready : std_logic := '0';
    signal pose_start, pose_done : std_logic := '0';
    signal tri_start, tri_done : std_logic := '0';
    
    -- Sinais intermediários
    signal F_matrix : Mat3;
    signal E_matrix : Mat3;
    signal R_matrix : Mat3;
    signal t_vector : Vec3;
    
    -- Componentes
    component FundamentalMatrixCalculator
        Port (
            clk     : in  std_logic;
            reset   : in  std_logic;
            start   : in  std_logic;
            pts1_x  : in  FixedArray2D;
            pts2_x  : in  FixedArray2D;
            F_out   : out Mat3;
            ready   : out std_logic
        );
    end component;
    
    component EssentialMatrixCalculator
        Port (
            clk     : in  std_logic;
            reset   : in  std_logic;
            start   : in  std_logic;
            F_in    : in  Mat3;
            K_const : in  Mat3;
            E_out   : out Mat3;
            ready   : out std_logic
        );
    end component;
    
    component PoseExtraction
        Port (
            clk   : in  std_logic;
            reset : in  std_logic;
            start : in  std_logic;
            E_in  : in  Mat3;
            R_out : out Mat3;
            t_out : out Vec3;
            done  : out std_logic
        );
    end component;
    
    component Triangulation
        Port (
            clk       : in  std_logic;
            reset     : in  std_logic;
            start     : in  std_logic;
            K_in      : in  Mat3;
            R_in      : in  Mat3;
            t_in      : in  Vec3;
            pts1      : in  FixedArray2D;
            pts2      : in  FixedArray2D;
            X_out     : out FixedArray3D;
            done      : out std_logic
        );
    end component;

begin
    -- Instanciar módulos
    fund_calc: FundamentalMatrixCalculator
        port map (
            clk     => clk,
            reset   => reset,
            start   => fund_start,
            pts1_x  => pts1_in,
            pts2_x  => pts2_in,
            F_out   => F_matrix,
            ready   => fund_ready
        );
    
    ess_calc: EssentialMatrixCalculator
        port map (
            clk     => clk,
            reset   => reset,
            start   => ess_start,
            F_in    => F_matrix,
            K_const => K_matrix,
            E_out   => E_matrix,
            ready   => ess_ready
        );
    
    pose_ext: PoseExtraction
        port map (
            clk   => clk,
            reset => reset,
            start => pose_start,
            E_in  => E_matrix,
            R_out => R_matrix,
            t_out => t_vector,
            done  => pose_done
        );
    
    triangulator: Triangulation
        port map (
            clk       => clk,
            reset     => reset,
            start     => tri_start,
            K_in      => K_matrix,
            R_in      => R_matrix,
            t_in      => t_vector,
            pts1      => pts1_in,
            pts2      => pts2_in,
            X_out     => points_3D,
            done      => tri_done
        );
    
    -- Máquina de estado principal
    process(clk)
    begin
        if rising_edge(clk) then
            if reset = '1' then
                state <= IDLE;
                ready <= '0';
                fund_start <= '0';
                ess_start <= '0';
                pose_start <= '0';
                tri_start <= '0';
            else
                case state is
                    when IDLE =>
                        if start = '1' then
                            state <= CALC_FUNDAMENTAL;
                            fund_start <= '1';
                            ready <= '0';
                        end if;
                    
                    when CALC_FUNDAMENTAL =>
                        fund_start <= '0';
                        if fund_ready = '1' then
                            state <= CALC_ESSENTIAL;
                            ess_start <= '1';
                        end if;
                    
                    when CALC_ESSENTIAL =>
                        ess_start <= '0';
                        if ess_ready = '1' then
                            state <= EXTRACT_POSE;
                            pose_start <= '1';
                        end if;
                    
                    when EXTRACT_POSE =>
                        pose_start <= '0';
                        if pose_done = '1' then
                            state <= TRIANGULATE;
                            tri_start <= '1';
                        end if;
                    
                    when TRIANGULATE =>
                        tri_start <= '0';
                        if tri_done = '1' then
                            state <= DONE;
                        end if;
                    
                    when DONE =>
                        -- Atribuir saídas
                        fundamental_F <= F_matrix;
                        essential_E <= E_matrix;
                        pose_R <= R_matrix;
                        pose_t <= t_vector;
                        ready <= '1';
                        
                        if start = '0' then
                            state <= IDLE;
                        end if;
                end case;
            end if;
        end if;
    end process;

end Behavioral;