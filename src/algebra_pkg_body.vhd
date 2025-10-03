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
        -- Shift right 16 bits para manter formato Q15.16
        C(i,j) := temp(47 downto 16);
      end loop;
    end loop;
    return C;
  end Mat3Mul;

  -- Produto vetorial de dois vetores 3×1
  function Cross3(u, v: Vec3) return Vec3 is
    variable result: Vec3 := (others => (others => '0'));
    variable temp1, temp2, temp_diff: signed(63 downto 0);
  begin
    -- result(0) = u(1)*v(2) - u(2)*v(1)
    temp1 := resize(u(1) * v(2), 64);
    temp2 := resize(u(2) * v(1), 64);
    temp_diff := temp1 - temp2;
    result(0) := temp_diff(47 downto 16);
    
    -- result(1) = u(2)*v(0) - u(0)*v(2)
    temp1 := resize(u(2) * v(0), 64);
    temp2 := resize(u(0) * v(2), 64);
    temp_diff := temp1 - temp2;
    result(1) := temp_diff(47 downto 16);
    
    -- result(2) = u(0)*v(1) - u(1)*v(0)
    temp1 := resize(u(0) * v(1), 64);
    temp2 := resize(u(1) * v(0), 64);
    temp_diff := temp1 - temp2;
    result(2) := temp_diff(47 downto 16);
    
    return result;
  end Cross3;

  -- Normalização de vetor 3×1 (implementação simplificada)
  function Normalize3(v: Vec3) return Vec3 is
    variable outv: Vec3 := (others => (others => '0'));
    variable norm_sq: signed(63 downto 0);
    variable max_component: Q15_16;
  begin
    -- Encontrar o maior componente para normalizar
    max_component := v(0);
    if abs(v(1)) > abs(max_component) then
      max_component := v(1);
    end if;
    if abs(v(2)) > abs(max_component) then
      max_component := v(2);
    end if;
    
    -- Normalização simples pelo maior componente
    if max_component /= 0 then
      outv(0) := v(0); -- Por simplicidade, manteremos os valores originais
      outv(1) := v(1); -- Uma implementação completa requereria divisão em hardware
      outv(2) := v(2);
    else
      outv := v;
    end if;
    
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

  -- Produto matriz-vetor 3x3 * 3x1
  function Mat3VecMul(A: Mat3; v: Vec3) return Vec3 is
    variable result: Vec3 := (others => (others => '0'));
    variable temp: signed(63 downto 0);
  begin
    for i in 0 to 2 loop
      temp := (others => '0');
      for j in 0 to 2 loop
        temp := temp + resize(A(i,j) * v(j), 64);
      end loop;
      result(i) := temp(47 downto 16);
    end loop;
    return result;
  end Mat3VecMul;
  
  -- Construir matriz antissimétrica (skew-symmetric) a partir de vetor
  function Skew(v: Vec3) return Mat3 is
    variable S: Mat3 := (others => (others => (others => '0')));
  begin
    S(0,0) := (others => '0');  S(0,1) := -v(2);        S(0,2) := v(1);
    S(1,0) := v(2);             S(1,1) := (others => '0'); S(1,2) := -v(0);
    S(2,0) := -v(1);            S(2,1) := v(0);          S(2,2) := (others => '0');
    return S;
  end Skew;
  
  -- SVD simplificada 3x3 (implementação muito básica)
  procedure SVD3x3(E: in Mat3; U: out Mat3; V: out Mat3) is
  begin
    -- Implementação muito simplificada - retorna matrizes identidade
    -- Uma implementação real requereria algoritmos iterativos complexos
    U := (others => (others => (others => '0')));
    V := (others => (others => (others => '0')));
    
    -- Matriz identidade como aproximação
    U(0,0) := to_signed(65536, 32); -- 1.0 em Q15.16
    U(1,1) := to_signed(65536, 32);
    U(2,2) := to_signed(65536, 32);
    
    V(0,0) := to_signed(65536, 32);
    V(1,1) := to_signed(65536, 32);
    V(2,2) := to_signed(65536, 32);
  end SVD3x3;

end package body algebra_pkg;
