$enc = [Text.Encoding]::GetEncoding(28591)
$d = "$env:TEMP\sfm_audit"
$t = [IO.File]::ReadAllText("$d\tb_probe.vhd", $enc)
$endMarker = "        wait for 100 ns;`r`n        reset <= '0';"

function Build($newName, $dataFile, $startMarker, $tbStartMarker) {
    $data = [IO.File]::ReadAllText($dataFile, $enc)
    $i = $data.IndexOf($startMarker)
    $data = $data.Substring($i).Replace("`r`n", "`n").Replace("`n", "`r`n").TrimEnd() + "`r`n`r`n"
    $a = $t.IndexOf($tbStartMarker)
    $b = $t.IndexOf($endMarker)
    if ($a -lt 0 -or $b -lt 0) { throw "marcador nao encontrado ($a, $b)" }
    $o = $t.Substring(0, $a) + $data + $t.Substring($b)
    $o = $o.Replace("entity tb_probe is", "entity $newName is").Replace("architecture sim of tb_probe is", "architecture sim of $newName is")
    [IO.File]::WriteAllText("$d\$newName.vhd", $o, $enc)
}
# cenario A: pontos reais regenerados por extract_points.py (run 1); mantem K do tb_top
Build "tb_probe_real" "$d\run_points_1.txt" "        -- Ponto 1" "        -- Ponto 1"
# cenario B: dados simulados (generate_test_data.py), inclui K
Build "tb_probe_sim" "$d\run_tbdata_1.txt" "        -- Inicializar matriz de calibra" "        -- Inicializar matriz de calibra"
"ok"
