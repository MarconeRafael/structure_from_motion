$enc = [Text.Encoding]::GetEncoding(28591)
$r = "$env:TEMP\sfm_audit\repo"
$t = [IO.File]::ReadAllText("$r\tb\tb_top.vhd", $enc)
$t = $t.Replace("entity tb_top is", "entity tb_probe is").Replace("architecture sim of tb_top is", "architecture sim of tb_probe is")

$funcs = @'

    function s2str(v : signed) return string is
        variable r  : string(1 to 32);
        variable lv : std_logic_vector(31 downto 0) := std_logic_vector(v);
    begin
        if Is_X(lv) then
            for i in 0 to 31 loop
                r(i+1) := std_logic'image(lv(31-i))(2);
            end loop;
            return "META[" & r & "]";
        else
            return integer'image(to_integer(v));
        end if;
    end function;

    function ismeta(v : signed) return boolean is
    begin
        return Is_X(std_logic_vector(v));
    end function;
'@
$t = $t.Replace("architecture sim of tb_probe is", "architecture sim of tb_probe is" + $funcs)

$dump = @'
        for i in 0 to 2 loop
            for j in 0 to 2 loop
                report "F(" & integer'image(i) & "," & integer'image(j) & ") = " & s2str(fundamental_F(i,j));
            end loop;
        end loop;
        for i in 0 to 2 loop
            for j in 0 to 2 loop
                report "E(" & integer'image(i) & "," & integer'image(j) & ") = " & s2str(essential_E(i,j));
            end loop;
        end loop;
        for i in 0 to 2 loop
            for j in 0 to 2 loop
                report "R(" & integer'image(i) & "," & integer'image(j) & ") = " & s2str(pose_R(i,j));
            end loop;
        end loop;
        for i in 0 to 2 loop
            report "t(" & integer'image(i) & ") = " & s2str(pose_t(i));
        end loop;
        for p in 0 to 8 loop
            report "X3D(" & integer'image(p) & ") = [" & s2str(points_3D(p,0)) & ", " & s2str(points_3D(p,1)) & ", " & s2str(points_3D(p,2)) & ", " & s2str(points_3D(p,3)) & "]";
        end loop;
        report "X3D(99) = [" & s2str(points_3D(99,0)) & ", " & s2str(points_3D(99,1)) & ", " & s2str(points_3D(99,2)) & ", " & s2str(points_3D(99,3)) & "]";
        wait for 1 ns;
'@
$marker = 'report "Teste SfM completo executado com sucesso!";'
$t = $t.Replace($marker, $dump + "`r`n        " + $marker)
[IO.File]::WriteAllText("$env:TEMP\sfm_audit\tb_probe.vhd", $t, $enc)
"ok"
