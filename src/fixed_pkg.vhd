library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;  -- Necessário para o tipo "signed"

package fixed_pkg is
  subtype Q15_16 is signed(31 downto 0);  -- 1 bit sinal, 15 int, 16 frac

  type Vec2    is array(0 to 1) of Q15_16;
  type Vec3    is array(0 to 2) of Q15_16;
  type Vec4    is array(0 to 3) of Q15_16;
  type Mat3    is array(0 to 2, 0 to 2) of Q15_16;
  type Mat3x4  is array(0 to 2, 0 to 3) of Q15_16;
  type Vector9 is array(0 to 8) of Q15_16;
  type MatNx9  is array(0 to 99, 0 to 8) of Q15_16;
  type FixedArray2D is array(0 to 99, 0 to 1) of Q15_16;
  type FixedArray3D is array(0 to 99, 0 to 3) of Q15_16;
end package;
