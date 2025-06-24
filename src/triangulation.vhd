library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.fixed_pkg.all;  -- exemplo
use work.algebra_pkg.all; -- se necessário


entity Triangulation is
    Port (
        clk       : in  std_logic;
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
    -- Variáveis temporárias
    signal P1, P2 : Mat3x4;
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if start = '1' then
                -- Construir matrizes de projeção P1, P2
                -- P1 := K_in * [I|0];
                -- P2 := K_in * [R_in | t_in];
                -- Para cada correspondência i:
                --   Montar sistema linear L * X = 0 (4 equações) derivado de y1 ? P1*X, y2 ? P2*X.
                --   Resolver por SVD ou eliminação (4×4).
                --   Armazenar X_out(i) = [X,Y,Z,W].
                done <= '1';
            end if;
        end if;
    end process;
end RTL;
