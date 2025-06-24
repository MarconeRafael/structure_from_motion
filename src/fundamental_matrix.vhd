library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.fixed_pkg.all;  -- exemplo
use work.algebra_pkg.all; -- se necessário


entity FundamentalMatrixCalculator is
    Port (
        clk       : in  std_logic;
        reset     : in  std_logic;
        start     : in  std_logic;
        pts1_x    : in  FixedArray2D; -- Matriz 100×2 com coordenadas (x,y) da imagem 1
        pts2_x    : in  FixedArray2D; -- Matriz 100×2 com coordenadas (x',y') da imagem 2
        F_out     : out Mat3;         -- Matriz fundamental 3×3 em ponto fixo
        ready     : out std_logic     -- Sinal que indica conclusão
    );
end FundamentalMatrixCalculator;

architecture Behavioral of FundamentalMatrixCalculator is
    -- Definição de sinais internos, por exemplo:
    signal A : MatNx9;      -- matriz de coeficientes (até N=100 linhas, 9 colunas)
    signal f_vec : Vector9; -- vetor solução (9x1)
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if reset = '1' then
                ready <= '0';
            elsif start = '1' then
                -- Passo 1: normalizar pontos (centro em 0, escala média ?2)
                -- (Implementar normalização em ponto fixo)
                -- Passo 2: montar matriz A a partir de cada correspondência (x,y,x',y')
                -- A(i,:) = [x_i'*x_i, x_i'*y_i, x_i', y_i'*x_i, y_i'*y_i, y_i', x_i, y_i, 1]
                -- Passo 3: calcular SVD ou auto-valores de A para obter vetor f (menor singular)
                -- (Em hardware, pode-se usar método iterativo ou chamadas a submódulo de EVD/SVD)
                -- Passo 4: reshaping f_vec (9 elementos) em F_temp 3×3
                -- Passo 5: ajustar posto 2: fatorar F_temp = U ? V^T, definir ? = diag(?1,?2,0), recompor F = U ? V^T
                -- Passo 6: converter para formato fixo e atribuir à saída F_out
                ready <= '1';
            end if;
        end if;
    end process;
end Behavioral;
