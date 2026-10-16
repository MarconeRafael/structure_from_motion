$ErrorActionPreference = "Continue"
$src = "C:\Users\Marcone\Documents\vhdl\structure_from_motion"
$base = "$env:TEMP\sfm_audit2"
$ghdlDir = "$env:TEMP\sfm_audit\ghdl\bin"
$bash = "C:\Program Files\Git\bin\bash.exe"
$env:PATH = "$ghdlDir;$env:PATH"
Remove-Item $base -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory "$base\logs" -Force | Out-Null
$r = "$base\repo"
New-Item -ItemType Directory $r | Out-Null
foreach ($i in "src", "tb", "images", "run.sh") { Copy-Item "$src\$i" $r -Recurse }
Copy-Item "$src\evidencias_testes\vhdl_probes\*.vhd" "$r\tb" -ErrorAction Stop
$summary = "$base\logs\resumo_reexecucao.txt"
function Log($m) { $m | Tee-Object -Append $summary }
function G($argLine, $log) {
    # cmd evita a quebra de linha/UTF-16 do redirecionamento do PowerShell
    $sw = [Diagnostics.Stopwatch]::StartNew()
    cmd /c "ghdl $argLine > `"$base\logs\$log`" 2>&1"
    $ec = $LASTEXITCODE; $sw.Stop()
    Log ("ghdl {0} | exit={1} | {2:N3}s" -f $argLine, $ec, $sw.Elapsed.TotalSeconds)
    return $ec
}
cd $r
Log "### inicio $(Get-Date -Format s)"
Log ((cmd /c "ghdl --version") -join " | ")
Log ("fontes em uso (SHA256 curtos): " + ((Get-ChildItem src\*.vhd, tb\tb_top.vhd, tb\tb_fundamental.vhd, run.sh | ForEach-Object { "$($_.Name)=$((Get-FileHash $_.FullName).Hash.Substring(0,8))" }) -join " "))

# 1) run.sh x3, sem modificacao
Log "### 1) run.sh (Git Bash) x3"
1..3 | ForEach-Object {
    Remove-Item work, wave.vcd -Recurse -Force -ErrorAction SilentlyContinue
    $sw = [Diagnostics.Stopwatch]::StartNew()
    cmd /c "`"$bash`" ./run.sh > `"$base\logs\runsh_$_.txt`" 2>&1"
    $ec = $LASTEXITCODE; $sw.Stop()
    Copy-Item wave.vcd "$base\logs\wave_run$_.vcd"
    Log ("run.sh #{0} exit={1} wall={2:N3}s vcd_bytes={3}" -f $_, $ec, $sw.Elapsed.TotalSeconds, (Get-Item wave.vcd).Length)
}
$v1 = Get-Content "$base\logs\wave_run1.vcd" | Select-Object -Skip 3
$v2 = Get-Content "$base\logs\wave_run2.vcd" | Select-Object -Skip 3
$v3 = Get-Content "$base\logs\wave_run3.vcd" | Select-Object -Skip 3
Log ("VCD identicos exceto cabecalho: 1==2 {0}; 2==3 {1}" -f (-not (Compare-Object $v1 $v2)), (-not (Compare-Object $v2 $v3)))
Log ("cabecalho \$date run1/run2/run3: " + ((1..3 | ForEach-Object { (Get-Content "$base\logs\wave_run$_.vcd" -TotalCount 3)[1].Trim() }) -join " | "))

# 2) arquivo a arquivo (VHDL-93 padrao), elaboracao e simulacao
Log "### 2) compilacao individual (padrao) + simulacao tb_top"
Remove-Item work -Recurse -Force; New-Item -ItemType Directory work | Out-Null
foreach ($f in "src/fixed_pkg.vhd", "src/algebra_pkg.vhd", "src/algebra_pkg_body.vhd", "src/projective_pkg.vhd", "src/fundamental_matrix.vhd", "src/essential_matrix.vhd", "src/pose_extraction.vhd", "src/triangulation.vhd", "src/top.vhd", "tb/tb_top.vhd") {
    [void](G "-a --workdir=work $f" ("an_" + (Split-Path $f -Leaf) + ".txt"))
}
[void](G "-e --workdir=work tb_top" "elab_tb_top.txt")
[void](G "-r --workdir=work tb_top --stop-time=10us --vcd=tb_top_direct.vcd" "run_tb_top.txt")

# 3) tb_fundamental
Log "### 3) tb_fundamental"
[void](G "-a --workdir=work tb/tb_fundamental.vhd" "tbfund_std93.txt")
New-Item -ItemType Directory work08 | Out-Null
foreach ($f in "src/fixed_pkg.vhd", "src/algebra_pkg.vhd", "src/algebra_pkg_body.vhd", "src/fundamental_matrix.vhd", "tb/tb_fundamental.vhd") { [void](G "-a --std=08 --workdir=work08 $f" ("an08_" + (Split-Path $f -Leaf) + ".txt")) }
[void](G "-e --std=08 --workdir=work08 tb_fundamental" "tbfund_elab08.txt")
[void](G "-r --std=08 --workdir=work08 tb_fundamental --stop-time=2us" "tbfund_run08.txt")

# 4) design completo em VHDL-2008 + synth
Log "### 4) VHDL-2008 completo e ghdl --synth"
New-Item -ItemType Directory work08b | Out-Null
foreach ($f in "src/fixed_pkg.vhd", "src/algebra_pkg.vhd", "src/algebra_pkg_body.vhd", "src/projective_pkg.vhd", "src/fundamental_matrix.vhd", "src/essential_matrix.vhd", "src/pose_extraction.vhd", "src/triangulation.vhd", "src/top.vhd", "tb/tb_top.vhd") { [void](G "-a --std=08 --workdir=work08b $f" ("a08b_" + (Split-Path $f -Leaf) + ".txt")) }
[void](G "-e --std=08 --workdir=work08b tb_top" "elab08b.txt")
[void](G "-r --std=08 --workdir=work08b tb_top --stop-time=10us" "run08b.txt")
foreach ($e in "EssentialMatrixCalculator", "FundamentalMatrixCalculator", "PoseExtraction", "Triangulation", "SfM_Top") {
    [void](G "--synth --std=08 --workdir=work08b $e" "synth_$e.txt")
    Log ("   netlist {0}: {1} bytes" -f $e, (Get-Item "$base\logs\synth_$e.txt").Length)
}

# 5) probes (exploratorios)
Log "### 5) probes"
foreach ($p in @(@("tb_probe", "10us"), @("tb_probe2", "20us"), @("tb_ess_probe", "2us"), @("tb_probe_real", "10us"), @("tb_probe_sim", "10us"))) {
    $n = $p[0]
    [void](G "-a --workdir=work tb/$n.vhd" "an_$n.txt")
    [void](G "-e --workdir=work $n" "elab_$n.txt")
    [void](G "-r --workdir=work $n --stop-time=$($p[1])" "run_$n.txt")
}
Log "### fim $(Get-Date -Format s)"
