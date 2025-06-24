library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.fixed_pkg.all;  -- exemplo
use work.algebra_pkg.all; -- se necessário


-- Normalizar coordenadas homogêneas
function NormalizeHomogeneous(p: Vec4) return Vec3 is
    variable out : Vec3;
begin
    if p(3) /= 0 then  -- p(3) = W
        out(0) := p(0) / p(3);  -- X/W
        out(1) := p(1) / p(3);  -- Y/W
        out(2) := p(2) / p(3);  -- Z/W
    else
        out := (others => 0);   -- W = 0: ponto no infinito (caso raro)
    end if;
    return out;
end function;
