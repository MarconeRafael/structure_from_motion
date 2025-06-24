library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.fixed_pkg.all;  -- exemplo
use work.algebra_pkg.all; -- se necessário


package projective_pkg is
  function Skew(v: Vec3) return Mat3;  -- retorna [v]_x (skew-sym)
  -- Outras operações (por ex., converter vetores para matriz P)
end projective_pkg;
