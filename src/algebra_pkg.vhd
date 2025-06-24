library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.fixed_pkg.all;

package algebra_pkg is

  -- Multiplicação de matrizes 3×3 em Q15.16
  function Mat3Mul(A, B: Mat3) return Mat3;

  -- Produto vetorial de dois vetores 3×1
  function Cross3(u, v: Vec3) return Vec3;

  -- Normalização de vetor 3×1
  function Normalize3(v: Vec3) return Vec3;

  -- Transposição de matriz 3×3
  function Transpose(A: Mat3) return Mat3;

end package algebra_pkg;
