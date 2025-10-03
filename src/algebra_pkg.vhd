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

  -- Produto matriz-vetor 3x3 * 3x1
  function Mat3VecMul(A: Mat3; v: Vec3) return Vec3;
  
  -- Construir matriz antissimétrica (skew-symmetric) a partir de vetor
  function Skew(v: Vec3) return Mat3;
  
  -- SVD simplificada 3x3 (retorna apenas U e V, assume ? conhecida)
  procedure SVD3x3(E: in Mat3; U: out Mat3; V: out Mat3);

end package algebra_pkg;
