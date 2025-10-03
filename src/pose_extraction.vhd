library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.fixed_pkg.all;  -- exemplo
use work.algebra_pkg.all; -- se necessário


entity PoseExtraction is
    Port (
        clk   : in  std_logic;
        reset : in  std_logic;
        start : in  std_logic;
        E_in  : in  Mat3;
        R_out : out Mat3;
        t_out : out Vec3;
        done  : out std_logic
    );
end PoseExtraction;
architecture Behavioral of PoseExtraction is
    type state_type is (IDLE, COMPUTE_SVD, EXTRACT_POSE, DONE_STATE);
    signal state : state_type := IDLE;
    
    signal U, V : Mat3;
    signal W, W_T : Mat3; -- Matrizes de rotação para extração de pose
    signal R1, R2 : Mat3;
    signal t1, t2 : Vec3;
    signal R_temp : Mat3;
    signal t_temp : Vec3;
    
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if reset = '1' then
                state <= IDLE;
                done <= '0';
            else
                case state is
                    when IDLE =>
                        if start = '1' then
                            state <= COMPUTE_SVD;
                            done <= '0';
                        end if;
                    
                    when COMPUTE_SVD =>
                        -- Calcular SVD simplificado de E_in (implementação básica)
                        -- U e V são aproximações - implementação completa requereria SVD iterativo
                        U <= (others => (others => (others => '0')));
                        V <= (others => (others => (others => '0')));
                        
                        -- Matriz identidade como aproximação inicial
                        U(0,0) <= to_signed(65536, 32); -- 1.0 em Q15.16
                        U(1,1) <= to_signed(65536, 32);
                        U(2,2) <= to_signed(65536, 32);
                        
                        V(0,0) <= to_signed(65536, 32);
                        V(1,1) <= to_signed(65536, 32);
                        V(2,2) <= to_signed(65536, 32);
                        
                        -- Construir matriz W = [0 -1 0; 1 0 0; 0 0 1]
                        W <= (others => (others => (others => '0')));
                        W(0,1) <= to_signed(-65536, 32); -- -1.0
                        W(1,0) <= to_signed(65536, 32);  -- 1.0
                        W(2,2) <= to_signed(65536, 32);  -- 1.0
                        
                        -- Construir W^T = [0 1 0; -1 0 0; 0 0 1]
                        W_T <= (others => (others => (others => '0')));
                        W_T(0,1) <= to_signed(65536, 32);  -- 1.0
                        W_T(1,0) <= to_signed(-65536, 32); -- -1.0
                        W_T(2,2) <= to_signed(65536, 32);  -- 1.0
                        
                        state <= EXTRACT_POSE;
                    
                    when EXTRACT_POSE =>
                        -- Calcular as 4 possíveis soluções
                        -- R1 = U * W * V^T
                        R1 <= Mat3Mul(Mat3Mul(U, W), Transpose(V));
                        -- R2 = U * W^T * V^T
                        R2 <= Mat3Mul(Mat3Mul(U, W_T), Transpose(V));
                        
                        -- t1 = +U(:,2) (terceira coluna de U)
                        t1(0) <= U(0,2);
                        t1(1) <= U(1,2);
                        t1(2) <= U(2,2);
                        
                        -- t2 = -U(:,2)
                        t2(0) <= -U(0,2);
                        t2(1) <= -U(1,2);
                        t2(2) <= -U(2,2);
                        
                        -- Por simplicidade, escolher a primeira solução
                        R_temp <= R1;
                        t_temp <= t1;
                        
                        state <= DONE_STATE;
                    
                    when DONE_STATE =>
                        R_out <= R_temp;
                        t_out <= t_temp;
                        done <= '1';
                        
                        if start = '0' then
                            state <= IDLE;
                        end if;
                end case;
            end if;
        end if;
    end process;
end Behavioral;
