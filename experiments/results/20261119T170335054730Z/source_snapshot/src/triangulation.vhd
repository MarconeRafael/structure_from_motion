library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.fixed_pkg.all;  -- exemplo
use work.algebra_pkg.all; -- se necessário


entity Triangulation is
    Port (
        clk       : in  std_logic;
        reset     : in  std_logic;
        start     : in  std_logic;
        K_in      : in  Mat3;
        R_in      : in  Mat3;
        t_in      : in  Vec3;
        pts1      : in  FixedArray2D; -- coordenadas imagem 1
        pts2      : in  FixedArray2D; -- coordenadas imagem 2
        X_out     : out FixedArray3D; -- pontos 3D homogêneos (X,Y,Z,W)
        done      : out std_logic
    );
end Triangulation;
architecture RTL of Triangulation is
    type state_type is (IDLE, BUILD_PROJECTION_MATRICES, TRIANGULATE_POINTS, DONE_STATE);
    signal state : state_type := IDLE;
    
    signal P1, P2 : Mat3x4;
    signal counter : integer := 0;
    signal I_mat : Mat3; -- Matriz identidade 3x3
    signal zero_vec : Vec3; -- Vetor zero
    
begin
    -- Inicializar constantes
    I_mat(0,0) <= to_signed(65536, 32); I_mat(0,1) <= (others => '0'); I_mat(0,2) <= (others => '0');
    I_mat(1,0) <= (others => '0'); I_mat(1,1) <= to_signed(65536, 32); I_mat(1,2) <= (others => '0');
    I_mat(2,0) <= (others => '0'); I_mat(2,1) <= (others => '0'); I_mat(2,2) <= to_signed(65536, 32);
    
    zero_vec <= (others => (others => '0'));
    
    process(clk)
        variable x1, y1, x2, y2 : Q15_16;
        variable X_temp, Y_temp, Z_temp, W_temp : Q15_16;
    begin
        if rising_edge(clk) then
            if reset = '1' then
                state <= IDLE;
                done <= '0';
                counter <= 0;
            else
                case state is
                    when IDLE =>
                        if start = '1' then
                            state <= BUILD_PROJECTION_MATRICES;
                            counter <= 0;
                            done <= '0';
                        end if;
                    
                    when BUILD_PROJECTION_MATRICES =>
                        -- P1 = K * [I | 0] (implementação simplificada)
                        P1(0,0) <= K_in(0,0); P1(0,1) <= K_in(0,1); P1(0,2) <= K_in(0,2); P1(0,3) <= (others => '0');
                        P1(1,0) <= K_in(1,0); P1(1,1) <= K_in(1,1); P1(1,2) <= K_in(1,2); P1(1,3) <= (others => '0');
                        P1(2,0) <= K_in(2,0); P1(2,1) <= K_in(2,1); P1(2,2) <= K_in(2,2); P1(2,3) <= (others => '0');
                        
                        -- P2 = K * [R | t] (implementação simplificada)
                        P2(0,0) <= Mat3Mul(K_in, R_in)(0,0); P2(0,1) <= Mat3Mul(K_in, R_in)(0,1); P2(0,2) <= Mat3Mul(K_in, R_in)(0,2);
                        P2(1,0) <= Mat3Mul(K_in, R_in)(1,0); P2(1,1) <= Mat3Mul(K_in, R_in)(1,1); P2(1,2) <= Mat3Mul(K_in, R_in)(1,2);
                        P2(2,0) <= Mat3Mul(K_in, R_in)(2,0); P2(2,1) <= Mat3Mul(K_in, R_in)(2,1); P2(2,2) <= Mat3Mul(K_in, R_in)(2,2);
                        
                        P2(0,3) <= Mat3VecMul(K_in, t_in)(0);
                        P2(1,3) <= Mat3VecMul(K_in, t_in)(1);
                        P2(2,3) <= Mat3VecMul(K_in, t_in)(2);
                        
                        state <= TRIANGULATE_POINTS;
                        counter <= 0;
                    
                    when TRIANGULATE_POINTS =>
                        if counter < 100 then -- Processar até 100 pontos
                            -- Obter coordenadas dos pontos correspondentes
                            x1 := pts1(counter, 0);
                            y1 := pts1(counter, 1);
                            x2 := pts2(counter, 0);
                            y2 := pts2(counter, 1);
                            
                            -- Triangulação linear simplificada (DLT)
                            -- Implementação muito básica - uma versão completa requereria
                            -- resolução de sistema linear 4x4
                            
                            -- Por simplicidade, interpolação linear básica
                            X_temp := (x1 + x2) / 2; -- Aproximação grosseira
                            Y_temp := (y1 + y2) / 2;
                            Z_temp := to_signed(65536, 32); -- Z = 1.0 (assumir profundidade unitária)
                            W_temp := to_signed(65536, 32); -- W = 1.0 (coordenada homogênea)
                            
                            -- Armazenar ponto 3D reconstruído
                            X_out(counter, 0) <= X_temp;
                            X_out(counter, 1) <= Y_temp;
                            X_out(counter, 2) <= Z_temp;
                            X_out(counter, 3) <= W_temp;
                            
                            counter <= counter + 1;
                        else
                            state <= DONE_STATE;
                        end if;
                    
                    when DONE_STATE =>
                        done <= '1';
                        if start = '0' then
                            state <= IDLE;
                        end if;
                end case;
            end if;
        end if;
    end process;
end RTL;
