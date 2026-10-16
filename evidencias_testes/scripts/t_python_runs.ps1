$d = "$env:TEMP\sfm_audit"
$py = "$d\venv\Scripts\python.exe"
$r = "$d\repo"
cd $r
$env:MPLBACKEND = "Agg"
$env:PYTHONIOENCODING = "utf-8"
Copy-Item vhdl_points_data.txt "$d\orig_vhdl_points_data.txt" -Force
Copy-Item vhdl_testbench_data.txt "$d\orig_vhdl_testbench_data.txt" -Force
Copy-Item simulated_data.npz "$d\orig_simulated_data.npz" -Force
Copy-Item vhdl_sfm_results.png "$d\orig_vhdl_sfm_results.png" -Force
Copy-Item vhdl_3d_reconstruction.png "$d\orig_vhdl_3d_reconstruction.png" -Force

# extract_points.py x5
for ($i = 1; $i -le 5; $i++) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $py extract_points.py *> "$d\log_extract_$i.txt"
    $ec = $LASTEXITCODE
    $sw.Stop()
    Copy-Item vhdl_points_data.txt "$d\run_points_$i.txt" -Force
    "extract_points run=$i exit=$ec elapsed_s=$([math]::Round($sw.Elapsed.TotalSeconds,2)) sha256=$((Get-FileHash vhdl_points_data.txt).Hash.Substring(0,12)) bytes=$((Get-Item vhdl_points_data.txt).Length)"
}
# generate_test_data.py x2
for ($i = 1; $i -le 2; $i++) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $py generate_test_data.py *> "$d\log_gen_$i.txt"
    $ec = $LASTEXITCODE
    $sw.Stop()
    Copy-Item vhdl_testbench_data.txt "$d\run_tbdata_$i.txt" -Force
    Copy-Item simulated_data.npz "$d\run_sim_$i.npz" -Force
    "generate_test_data run=$i exit=$ec elapsed_s=$([math]::Round($sw.Elapsed.TotalSeconds,2)) sha_txt=$((Get-FileHash vhdl_testbench_data.txt).Hash.Substring(0,12)) sha_npz=$((Get-FileHash simulated_data.npz).Hash.Substring(0,12))"
}
"orig tbdata sha=$((Get-FileHash "$d\orig_vhdl_testbench_data.txt").Hash.Substring(0,12)) orig npz sha=$((Get-FileHash "$d\orig_simulated_data.npz").Hash.Substring(0,12))"
# visualize x2
for ($i = 1; $i -le 2; $i++) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $py visualize_vhdl_results.py *> "$d\log_vis_$i.txt"
    $ec = $LASTEXITCODE
    $sw.Stop()
    Copy-Item vhdl_sfm_results.png "$d\run_vis_sfm_$i.png" -Force
    Copy-Item vhdl_3d_reconstruction.png "$d\run_vis_3d_$i.png" -Force
    "visualize run=$i exit=$ec elapsed_s=$([math]::Round($sw.Elapsed.TotalSeconds,2)) sfm_png=$((Get-Item vhdl_sfm_results.png).Length) 3d_png=$((Get-Item vhdl_3d_reconstruction.png).Length)"
}
"orig png sizes: $((Get-Item "$d\orig_vhdl_sfm_results.png").Length) $((Get-Item "$d\orig_vhdl_3d_reconstruction.png").Length)"
