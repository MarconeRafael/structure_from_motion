library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.fixed_pkg.all;  -- exemplo
use work.algebra_pkg.all; -- se necessário


entity PoseExtraction is
    Port (
        E_in  : in  Mat3;
        R_out : out Mat3;
        t_out : out Vec3;
        done  : out std_logic
    );
end PoseExtraction;
architecture Behavioral of PoseExtraction is
    signal U, Vt : Mat3;
    signal S      : Vector3;  -- ? diagonal (?1,?2,?3)
    signal R1, R2 : Mat3;
    signal t1, t2 : Vec3;
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if start = '1' then
                -- Calcular SVD de E_in: E = U * diag(S) * Vt
                -- (Usar sub-bloco de decomposição SVD em ponto fixo)
                -- Construir W e W^T
                -- R1 := U * W * Vt;
                -- R2 := U * W^T * Vt;
                -- t1 := +U(:,3);  -- terceira coluna de U
                -- t2 := -U(:,3);
                -- Selecionar (R_out,t_out) que satisfaz profundidade positiva
                done <= '1';
            end if;
        end if;
    end process;
end Behavioral;
