$d = "$env:TEMP\sfm_audit"
$py = "$d\venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"
$src = "C:\Users\Marcone\Documents\vhdl\structure_from_motion"

# Controle 1: mesma imagem duas vezes
$c1 = "$d\ctrl_same"; Remove-Item $c1 -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory "$c1\images" -Force | Out-Null
Copy-Item "$src\images\img1.jpeg" "$c1\images\img1.jpeg"; Copy-Item "$src\images\img1.jpeg" "$c1\images\img2.jpeg"; Copy-Item "$src\extract_points.py" $c1
cd $c1
"=== controle 1: img1 == img2 ==="
& $py extract_points.py 2>&1 | Out-String -Width 200 | ForEach-Object { $_.Split("`n") | Select-Object -First 14 }
"exit=$LASTEXITCODE"
$pts = Select-String -Path "$c1\vhdl_points_data.txt" -Pattern "x1 =|x2 =" | Select-Object -First 4 | ForEach-Object { $_.Line.Trim() }; $pts

# Controle 2: imagem ausente
$c2 = "$d\ctrl_missing"; Remove-Item $c2 -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory "$c2\images" -Force | Out-Null
Copy-Item "$src\images\img1.jpeg" "$c2\images\img1.jpeg"; Copy-Item "$src\extract_points.py" $c2
cd $c2
"=== controle 2: img2 ausente ==="
& $py extract_points.py 2>&1 | Out-String -Width 200
"exit=$LASTEXITCODE"
