$enc = [Text.Encoding]::GetEncoding(28591)
$d = "$env:TEMP\sfm_audit"
$t = [IO.File]::ReadAllText("$d\tb_probe.vhd", $enc)
# extrai o bloco de dump do probe 1
$start = $t.IndexOf("        for i in 0 to 2 loop")
$end = $t.IndexOf("        wait for 1 ns;") + "        wait for 1 ns;".Length
$dump = $t.Substring($start, $end - $start)
$dump2 = $dump.Replace('report "', 'report "RUN2 ')
$second = @'

        start <= '1';
        wait for 20 ns;
        start <= '0';
        wait for 3 us;
'@
$t = $t.Replace($dump, $dump + $second + $dump2)
$t = $t.Replace("entity tb_probe is", "entity tb_probe2 is").Replace("architecture sim of tb_probe is", "architecture sim of tb_probe2 is")
[IO.File]::WriteAllText("$d\tb_probe2.vhd", $t, $enc)
"ok"
