library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.fixed_pkg.all;

package body algebra_pkg is
  -- Multiplicação de matrizes 3×3 em Q15.16
  function Mat3Mul(A, B: Mat3) return Mat3 is
    variable C    : Mat3 := (others => (others => (others => '0')));
    variable temp : signed(63 downto 0);
  begin
    for i in 0 to 2 loop
      for j in 0 to 2 loop
        temp := (others => '0');
        for k in 0 to 2 loop
          temp := temp + resize(A(i,k) * B(k,j), 64);
        end loop;
        C(i,j) := signed(temp(47 downto 16));  -- converte de 64?32 bits Q15.16
      end loop;
    end loop;
    return C;
  end Mat3Mul;

  -- Produto vetorial de dois vetores 3×1
  function Cross3(u, v: Vec3) return Vec3 is
    variable result: Vec3 := (others => (others => '0'));
  begin
    result(0) := (u(1) * v(2)) - (u(2) * v(1));
    result(1) := (u(2) * v(0)) - (u(0) * v(2));
    result(2) := (u(0) * v(1)) - (u(1) * v(0));
    return result;
  end Cross3;

  -- Normalização de vetor 3×1 (aqui apenas retorna o vetor, implemente sqrt fixa se precisar)
  function Normalize3(v: Vec3) return Vec3 is
    variable outv: Vec3 := (others => (others => '0'));
  begin
    outv := v;  -- substitua por rotina de normalização se necessário
    return outv;
  end Normalize3;

  -- Transposição de matriz 3×3
  function Transpose(A: Mat3) return Mat3 is
    variable B: Mat3 := (others => (others => (others => '0')));
  begin
    for i in 0 to 2 loop
      for j in 0 to 2 loop
        B(i,j) := A(j,i);
      end loop;
    end loop;
    return B;
  end Transpose;

end package body algebra_pkg;
