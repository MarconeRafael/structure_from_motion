# Relatório de testes — Structure from Motion (VHDL + Python)

Data da execução: 2026-10-16. Commit testado: `5b27e9f1462348b85fac274a71a1ecf28c9cfd31` (no início dos testes, o único arquivo modificado na árvore de trabalho era `README.md`, alteração da tarefa anterior de documentação).

Convenções deste relatório:

- **Medido**: valor obtido diretamente de uma execução (log em [evidencias_testes/logs](evidencias_testes/logs)).
- **Calculado**: derivado de valores medidos; a fórmula é indicada.
- **Informado por ferramenta**: impresso por GHDL/OpenCV/Python.
- Status dos testes: **Aprovado**, **Reprovado**, **Inconclusivo**, **Não executado**.
- "Aprovado" em testes operacionais significa apenas que o critério declarado foi atendido; não implica correção numérica ou científica.

## 1. Resumo executivo

1. **Fluxo operacional funciona nas duas imagens.** Os três scripts Python executaram sem erro. Todos os arquivos de `src/` e `tb/tb_top.vhd` compilaram (o `tb/tb_fundamental.vhd` só compila com `--std=08`), o testbench `tb_top` elaborou e simulou com GHDL 6.0.0, e o handshake `Fundamental → Essential → Pose → Triangulation` terminou em 1355 ns simulados (`ready='1'`).
2. **O VHDL não produz resultados geométricos válidos.** Em simulação, as saídas `fundamental_F`, `pose_R` e `pose_t` de `SfM_Top` ficaram **indefinidas (`'U'`)** e `essential_E` ficou **`'X'`** em todos os 9 elementos. Isso confirma a hipótese levantada por análise estática na tarefa anterior. As únicas saídas definidas são os pontos 3D, e estas são `X=(x1+x2)/2`, `Y=(y1+y2)/2`, `Z=W=1,0` (8/8 pontos conferidos), com erro de reprojeção médio de ≈1,74·10⁵ px.
3. **O testbench não detecta isso**: ele só espera `ready='1'` e imprime "sucesso". A mensagem de sucesso não tem valor de verificação.
4. **Python/OpenCV produz geometria epipolar coerente para este par**: 137 correspondências aceitas, 129 inliers RANSAC (94,16 %), erro de Sampson médio de 0,323 px nos inliers. Os resultados de pose e triangulação com K assumido e 8 pontos são de baixa confiança (7/8 pontos com profundidade positiva; reprojeção média 6,8–8,8 px). Não há ground truth, então a qualidade científica da reconstrução **não pôde ser comprovada**.
5. **As figuras `vhdl_*.png` não vêm do VHDL**: `visualize_vhdl_results.py` usa pontos fixos no código e OpenCV. Os rótulos "Processamento VHDL" nos títulos são enganosos.
6. **Não houve síntese para FPGA, relatório de recursos, medição de frequência/consumo nem execução em hardware.** `ghdl --synth` gerou netlists genéricas sem erros, mas isso não equivale a síntese mapeada para uma FPGA.

## 2. Ambiente

| Item | Valor | Fonte |
|---|---|---|
| SO | Windows 11 Home 10.0.26200; WSL2 Ubuntu 22.04 (kernel 6.6.87.2) | [ambiente.txt](evidencias_testes/logs/ambiente.txt) |
| CPU / RAM | AMD Ryzen 7 5700U, 9,8 GB | idem |
| GHDL | 6.0.0 (backend **mcode**, Windows MinGW64 portátil), baixado em pasta temporária, SHA-256 conferido com o publicado na release v6.0.0 (`C1562B2A…2CADFFE`) | idem |
| Shell para `run.sh` | GNU bash 5.2.37 (Git for Windows) | idem |
| Python (venv temporário) | 3.11.9; opencv-python 5.0.0.93; numpy 2.4.6; matplotlib 3.11.2; pillow 12.3.0 | idem |
| Python no WSL | 3.10.12 (sem OpenCV; usado apenas para executar o binário ELF `tb_top`) | idem |
| GTKWave, Yosys, ferramentas de síntese de fabricante | não instalados / não usados | — |

Limitações do ambiente:

- **Nenhum GHDL estava instalado**; foi usado um GHDL portátil do site oficial, em `%TEMP%`, sem instalação global. O autor provavelmente usou outro backend (o `tb_top` versionado é um executável ELF, típico de backend gcc/llvm). O resultado de simulação é comparável (mesmas mensagens, mesmos tempos), mas não é o mesmo binário.
- Interoperabilidade WSL→`.exe` estava desabilitada ("Exec format error"), então `run.sh` foi executado com Git Bash no Windows, não em Linux nativo.
- Todos os testes rodaram em **cópias em `%TEMP%`**; o repositório original não foi usado como diretório de trabalho. O repositório recebeu apenas este relatório e a pasta `evidencias_testes/`.
- Os nomes de arquivo dos probes nos logs têm sufixo `_audit` (ex.: `tb/tb_probe_audit.vhd`), porque na cópia temporária foram copiados com esse nome; em [vhdl_probes](evidencias_testes/vhdl_probes) estão sem o sufixo.

## 3. Imagens utilizadas

Fonte: [log_images.txt](evidencias_testes/logs/log_images.txt) (leitura, sem modificar os originais).

| Propriedade | `images/img1.jpeg` | `images/img2.jpeg` |
|---|---|---|
| Formato / modo | JPEG (JFIF 1.01), RGB, 3 canais, uint8 | idem |
| Resolução (L×A) | 640×480 | 640×480 |
| Tamanho | 66 999 B | 61 545 B |
| SHA-256 | `cff9731c…83c6e13d` | `180f201f…ec0cde66` |
| DPI / EXIF | 96 / nenhum | 96 / nenhum |
| Cinza: média / desvio / mín–máx | 55,39 / 48,29 / 0–255 | 43,49 / 48,51 / 0–250 |
| Variância do Laplaciano (nitidez, valor relativo) | 682,56 | 437,02 |

Comparação (calculada): mesmas dimensões; erro absoluto médio pixel a pixel (cinza) 44,67; correlação de histogramas 0,647.

**Adequação ao fluxo (inspeção visual + medições):**

- As imagens mostram a mesma cena (duas caixas de DVD sobre uma prateleira) com mudança de ponto de vista considerável (img2 é mais próxima e deslocada). O projeto exige apenas dois arquivos em `images/img1.jpeg` e `images/img2.jpeg`; os scripts leem em escala de cinza e não impõem resolução (o `K` do testbench assume 640×480).
- O par é **compatível com correspondência por SIFT** (137 correspondências, 129 inliers). Porém: ambas são escuras (média de cinza 43–55/255); **73,6 % dos inliers (95/129) são explicados por uma única homografia** (3 px), indicando cena com forte componente planar, que é uma condição pouco favorável à estimação robusta de F/E; o `K` (525/525/320/240) é **estimado**, não calibrado; não há ground truth de pose ou de estrutura.
- Não foram criadas versões convertidas/redimensionadas das imagens.

## 4. Arquitetura testada

Conforme o código lido (detalhes em [README.md](README.md)):

| Componente | Exercitado? | Como |
|---|---|---|
| `extract_points.py` (SIFT + FLANN + razão 0,7 + RANSAC → texto VHDL) | Sim | 5 execuções reais |
| `generate_test_data.py` (pontos sintéticos, seed 42) | Sim | 2 execuções |
| `visualize_vhdl_results.py` | Sim | 2 execuções (`MPLBACKEND=Agg`) |
| `Epipolar_Geometry.ipynb`, `SfM.txt` | Não | ver seção 11 |
| `fixed_pkg`, `algebra_pkg(+body)`, `projective_pkg` | Compilação; `Mat3Mul`/`Transpose` exercitadas via simulação | `run.sh` e probe isolado |
| `FundamentalMatrixCalculator`, `PoseExtraction`, `Triangulation`, `EssentialMatrixCalculator`, `SfM_Top` | Compilação, simulação (integrada em `tb_top`), `ghdl --synth` | seções 5–8 |
| `tb_top`, `tb_fundamental` | Sim | `run.sh`; `tb_fundamental` isolado |
| Transferência Python → VHDL | Sim, manual | texto gerado colado num probe do testbench (ver T22) |
| Execução em FPGA / síntese de fabricante | **Não** | — |

## 5. Procedimentos executados

Todos em cópia temporária do repositório (sem `.git`), PowerShell no Windows. Os comandos abaixo são os efetivamente executados (via os scripts listados em [scripts](evidencias_testes/scripts)).

```powershell
# GHDL portátil
Invoke-WebRequest -Uri https://github.com/ghdl/ghdl/releases/download/v6.0.0/ghdl-mcode-6.0.0-mingw64.zip -OutFile ghdl.zip
Expand-Archive ghdl.zip -DestinationPath ghdl;  $env:PATH = "$PWD\ghdl\bin;$env:PATH"

# Fluxo VHDL documentado (3 repetições, 'run.sh' sem modificação)
& "C:\Program Files\Git\bin\bash.exe" ./run.sh

# Compilação de tb_fundamental
ghdl -a --workdir=work tb/tb_fundamental.vhd                       # padrão do run.sh
ghdl -a --std=08 --workdir=work08 <fixed_pkg algebra_pkg algebra_pkg_body fundamental_matrix tb_fundamental>
ghdl -e --std=08 --workdir=work08 tb_fundamental
ghdl -r --std=08 --workdir=work08 tb_fundamental --vcd=fund.vcd --stop-time=2us

# Tudo em VHDL-2008, depois síntese lógica genérica por entidade
ghdl -a --std=08 --workdir=work08b <todos os src/*.vhd + tb/tb_top.vhd>;  ghdl -e ... tb_top;  ghdl -r ... tb_top --stop-time=10us
ghdl --synth --std=08 --workdir=work08b <EssentialMatrixCalculator|FundamentalMatrixCalculator|PoseExtraction|Triangulation|SfM_Top>

# Probes (testbenches temporários, não alteram o repositório)
ghdl -a --workdir=work tb/<probe>.vhd;  ghdl -e --workdir=work <entidade>;  ghdl -r --workdir=work <entidade> --stop-time=10us
#   tb_probe      = tb_top + impressão de F, E, R, t e pontos 3D
#   tb_probe2     = idem, com segundo pulso de 'start'
#   tb_ess_probe  = EssentialMatrixCalculator isolado (F = constantes de SOLVE_SVD; K do tb_top)
#   tb_probe_real / tb_probe_sim = tb_top com pontos gerados por extract_points.py / generate_test_data.py colados

# Python (venv temporário; $env:MPLBACKEND='Agg')
python extract_points.py            # 5x
python generate_test_data.py        # 2x
python visualize_vhdl_results.py    # 2x
python t_images.py; python t_geometry.py; python t_compare.py; python t_x3d_check.py   # análises (scripts/)
# controles negativos: extract_points.py com img2 = img1; com img2 ausente  (t_controls.ps1)
```

Binário versionado, no WSL: `cp tb_top /tmp/sfm; ./tb_top --stop-time=10us --vcd=/tmp/sfm/w.vcd`.

Parâmetros: relógio do testbench 10 ns (clk alternando a cada 5 ns); `reset` por 100 ns; `start` de 120 a 140 ns; `--stop-time=10us`. Sementes: `generate_test_data.py` usa `np.random.seed(42)`; `extract_points.py` **não** usa semente (seleção dos 8 pontos aleatória).

## 6. Tabela de testes

| ID | Componente | Descrição / critério de aprovação | Resultado | Observações |
|---|---|---|---|---|
| T01 | Entrada | Ler as 2 imagens com OpenCV e PIL; critério: leitura sem erro, 3 canais, dimensões iguais | **Aprovado** | 640×480, JPEG RGB (seção 3) |
| T02 | Entrada | Par adequado ao fluxo (correspondências suficientes) | **Aprovado com ressalvas** | 129 inliers; cena predominantemente planar; K estimado |
| T03 | VHDL | `run.sh` sem modificação: compilar 9 arquivos + tb, elaborar, simular; critério: exit 0 e mensagens finais | **Aprovado** | 3/3 execuções, exit 0; `wave.vcd` gerado. Backend mcode no Windows (ver seção 2) |
| T04 | VHDL | Handshake completo em `tb_top`; critério: `ready='1'` antes de 10 µs | **Aprovado** | `ready` em 1355 ns; reports em 1455 ns |
| T05 | VHDL | Executar o binário ELF `tb_top` versionado (WSL) | **Aprovado (limitado)** | Mesmas mensagens/tempos; procedência do binário não verificável |
| T06 | VHDL | `tb_fundamental` compilado com o padrão do `run.sh` (VHDL-93) | **Reprovado** | `unit "env" not found in library "std"` (usa `std.env.stop`, VHDL-2008) |
| T07 | VHDL | `tb_fundamental` com `--std=08`; critério: compila, elabora, termina | **Aprovado (limitado)** | Terminou em 1020 ns com report; o testbench não confere `F_out` nem `ready` |
| T08 | VHDL | Todo o design e `tb_top` com `--std=08` | **Aprovado** | 10/10 análises, elaboração e simulação exit 0 |
| T09 | VHDL | `ghdl --synth` em 5 entidades; critério: exit 0 | **Aprovado (limitado)** | Netlist VHDL genérica; **sem** relatório de recursos, sem mapeamento para FPGA |
| T10 | `EssentialMatrixCalculator` | Isolado, F = constantes de `SOLVE_SVD`, K do `tb_top`; critério: E = emulação inteira bit a bit de `Mat3Mul` | **Aprovado** (aritmética) | 9/9 elementos idênticos à emulação |
| T11 | `EssentialMatrixCalculator` | Mesmo teste; critério: valores dentro da faixa Q15.16 (±32768) | **Reprovado** | 6 de 9 elementos do E ideal excedem a faixa → *wrap-around* (ex.: E(0,0): 137 812,5 ideal vs 6 740,5 no VHDL) |
| T12 | `SfM_Top` | Saídas `fundamental_F`, `pose_R`, `pose_t`, `essential_E` definidas (sem `U`/`X`) ao final | **Reprovado** | F, R, t: 100 % `'U'`; E: 100 % `'X'` (exploratório) |
| T13 | `Triangulation` | `points_3D(i) == ((x1+x2)/2, (y1+y2)/2, 1,0, 1,0)` | **Aprovado** (comportamento do código) | 8/8 pontos, em 3 conjuntos de dados (tb_top, real regenerado, simulado) |
| T14 | `Triangulation` | Validade geométrica dos 3D (erro de reprojeção) | **Reprovado** | ≈1,74·10⁵ px médio; Z constante |
| T15 | `SfM_Top` | Segundo pulso de `start` (reuso); critério: `ready` só após conclusão real dos módulos | **Reprovado** (exploratório) | `ready` volta a 1 em 1515 ns (≈60 ns após o início); `pose_done` 1525, `fund_ready` 1555, `tri_done` 2535 ns; saídas continuam `U`/`X` |
| T16 | `extract_points.py` | 5 execuções; critério: exit 0, 8 pontos emitidos | **Aprovado** | Contagens idênticas nas 5 execuções; **pontos emitidos diferem** (5 hashes distintos) |
| T17 | `generate_test_data.py` | Determinismo e igualdade com `simulated_data.npz` versionado | **Aprovado** | `pts1`, `pts2`, `K` idênticos; texto difere só na codificação dos comentários (cp1252 no Windows vs UTF-8 no arquivo versionado) |
| T18 | `visualize_vhdl_results.py` | Exit 0, gera 2 PNG, conteúdo legível | **Aprovado** (operacional) | Ver T19 |
| T19 | `visualize_vhdl_results.py` | Usa saídas do VHDL (como sugerem nome e mensagens) | **Reprovado** | Pontos fixos no código; F/E/pose/triangulação por OpenCV |
| T20 | Controle negativo | `extract_points.py` com img2 = img1; deveria rejeitar par degenerado | **Reprovado** | exit 0; 1199 correspondências e 1199 inliers; gera pontos com x1 = x2 |
| T21 | Controle negativo | `extract_points.py` sem `img2.jpeg` | **Aprovado (limitado)** | Mensagem de erro, exit code 0 (o script retorna normalmente) |
| T22 | Integração Python→VHDL (manual) | Colar texto gerado no estímulo e simular; critério: compila, roda, `X3D` acompanha a nova entrada | **Aprovado** | Procedimento manual funciona (probes `real` e `sim`); F/R/t/E seguem indefinidos |
| T23 | `run.sh` em Linux/WSL | Executar `run.sh` (cópia com CRLF) em bash Linux | **Inconclusivo** | Observado `$'\r': command not found`; GHDL Linux não disponível. No índice git o arquivo é LF (CRLF vem de `core.autocrlf=true` no Windows) |
| T24 | Qualidade científica VHDL vs OpenCV | Comparar F/E/R/t/3D do VHDL com OpenCV | **Inconclusivo** | Saídas do VHDL indefinidas; só os 3D são comparáveis (T14) |
| T25 | Hardware | Síntese FPGA, recursos, Fmax, consumo, execução física | **Não executado** | Sem ferramentas/placa; sem arquivos de projeto no repositório |

## 7. Tabela de métricas

### 7.1 Visão computacional (Python/OpenCV)

| Métrica | Valor | Unidade | Método / fonte |
|---|---|---|---|
| Pontos-chave SIFT img1 / img2 | 1199 / 1494 | — | Medido; `extract_points.py` (5/5 execuções) e `t_geometry.py`; [log_extract_1.txt](evidencias_testes/logs/log_extract_1.txt) |
| Tempo SIFT (detect+compute) img1 / img2 | 0,053 / 0,047 | s | Medido, 1 execução cada (`t_geometry.py`) |
| Pares kNN avaliados / tempo FLANN | 1199 / 0,067 | — / s | Medido, 1 execução |
| Correspondências aceitas (razão 0,7; script do projeto) | 137 | — | Medido (5/5 execuções) |
| Taxa de aceitação razão 0,7 | 11,43 | % | Calculado: 137/1199 |
| Correspondências aceitas (razão 0,8; valor do notebook) | 218 | — | Medido (`t_geometry.py`); 218/1199 = 18,18 % |
| Inliers RANSAC (`FM_RANSAC`, parâmetros padrão) | 129 (10/10 repetições; 5/5 no script) | — | Medido |
| Taxa de inliers | 94,16 | % | Calculado: 129/137 |
| Erro de Sampson, inliers sob F_ransac (média / mediana / máx) | 0,323 / 0,223 / 1,806 | px | Calculado a partir de F e pontos (`t_geometry.py`) |
| Erro de Sampson, 8 outliers (média / mediana / máx) | 43,838 / 29,885 / 108,029 | px | Calculado |
| Deslocamento 2D dos inliers (média / mediana / máx) | 67,985 / 63,840 / 233,871 | px | Calculado |
| Inliers explicados por homografia (3 px) | 95 de 129 (73,6) | — / % | Medido (`cv2.findHomography`) |
| 8 pontos do testbench: erro de Sampson sob F_ransac (média / mediana / máx) | 0,238 / 0,141 / 0,614 | px | Calculado; os 8 pontos coincidem com inliers SIFT (distância ≤ 0,1 px) |
| 8 pontos: resíduo sob a F de 8 pontos (própria) | 0,508 / 0,049 / 3,300 | px | Calculado |
| 129 inliers sob a F de 8 pontos | 1,202 / 0,670 / 8,713 | px | Calculado |
| `recoverPose` (8 pontos, K assumido): pontos com cheirality | 7 de 8 | — | Informado por OpenCV |
| Rotação estimada / t | 15,94° / (−0,403; 0,173; −0,899) | ° / — | Informado por OpenCV (K estimado) |
| Profundidade Z (câm. 1) dos 8 pontos | 3,602; −0,559; 3,005; 2,860; 3,352; 3,299; 3,894; 2,814 | unid. de t | Informado por OpenCV (escala arbitrária) |
| Erro de reprojeção OpenCV img1 / img2 (média) | 6,829 / 8,839 | px | Calculado |
| Erro de conversão Q15.16 dos 516 valores de coordenada | máx. 7,63·10⁻⁶ | px | Calculado (limite teórico 2⁻¹⁶ = 1,53·10⁻⁵) |

### 7.2 VHDL (simulação GHDL)

| Métrica | Valor | Unidade | Método / fonte |
|---|---|---|---|
| Latência `start`→`ready` (simulada) | 1235 | ns | Calculado: 1355 − 120 ns, do VCD ([log_vcd_handshake.txt](evidencias_testes/logs/log_vcd_handshake.txt)); ≈123 ciclos de 10 ns |
| `fund_ready` / `ess_ready` / `pose_done` / `tri_done` / `ready` | 215 / 235 / 285 / 1335 / 1355 | ns | Medido (VCD) |
| Duração da triangulação | 1050 | ns | Calculado: 1335 − 285 (100 iterações) |
| Tempo de parede de `run.sh` (compila+elabora+simula, Git Bash/Windows, GHDL mcode) | 1ª rodada: 0,785 / 0,723 / 0,729 (média 0,746) e 0,818; reexecução: 1,274 / 1,168 / 1,218 (média 1,220) | s | Medido, 7 execuções. A diferença entre rodadas (≈ +64 %) não foi investigada (carga da máquina não foi controlada) |
| Tempo só de simulação (probe) / do binário ELF em WSL | 0,104 / 0,051 | s | Medido, 1 execução cada |
| Tamanho de `wave.vcd` (GHDL mcode / binário ELF) | 78 943 / 64 631 | B | Medido; contém só sinais escalares (arrays marcados "not handled") |
| Pontos 3D observados | posições 0–7 = função dos 8 pontos de entrada; posições 8 e 99 = `(0,0,1,1)` (as posições 9–98 não foram impressas) | — | Medido (`points_3D`) |
| Erro de reprojeção em img1 dos 3D do VHDL (média / mediana / máx) | 174 117,9 / 152 178,6 / 245 748,9 | px | Calculado com `P1 = K[I|0]` e Q15.16/65536 |
| Ângulo entre R do OpenCV e `W` (R que o código geraria com U=V=I) | 90,52 | ° | Calculado; `R` do VHDL **não é observável** (é `'U'`) |
| Erro de Sampson dos 129 inliers sob a F constante do VHDL (média / máx) | 208,296 / 361,309 | px | Calculado com os valores de `SOLVE_SVD`; F constante tem posto 1 (valores singulares 0,577; 0; 0) |
| Elementos de E fora da faixa Q15.16 | 6 de 9 | — | Calculado (E ideal) vs medido (GHDL) |
| Tamanho das netlists `--synth` (VHDL gerado) | Essential 54 209; Fundamental 30 255; Pose 69 488; Triangulation 271 109; SfM_Top 424 742 | B | Medido na reexecução (seção 8.6); **não** é métrica de recursos. Os valores da 1ª execução (108 420; 60 512; 138 978; 542 220; 849 486) estavam inflados ≈ 2× porque o redirecionamento do PowerShell gravou os arquivos em UTF-16; foram substituídos |

### 7.3 Operacionais (Python)

| Métrica | Valor | Unidade | Fonte |
|---|---|---|---|
| `extract_points.py` (5 execuções) | 0,81 / 0,52 / 0,49 / 0,57 / 0,57 (média 0,592) | s | Medido ([log_python_runs.txt](evidencias_testes/logs/log_python_runs.txt)) |
| `generate_test_data.py` (2 execuções) | 0,38 / 0,33 | s | idem |
| `visualize_vhdl_results.py` (2 execuções) | 4,75 / 4,20 | s | idem |
| `vhdl_points_data.txt` gerado | 2418–2419 | B | idem |
| PNG gerados (`vhdl_sfm_results.png` / `vhdl_3d_reconstruction.png`) | 5 497 386 / 348 562 (idênticos nas 2 execuções) | B | idem; os versionados têm 5 590 932 / 413 623 B (causa da diferença não investigada) |

### 7.4 Indisponíveis

| Métrica | Motivo |
|---|---|
| LUTs, flip-flops, DSPs, BRAM | Sem síntese mapeada para FPGA; `ghdl --synth` não emite relatório de recursos; não há Yosys/ferramentas de fabricante nem alvo definido |
| Frequência máxima, consumo de energia | Exigem síntese + análise de tempo/potência; indisponíveis. O relógio de 10 ns do testbench é parâmetro de simulação, não medição de Fmax |
| Aceleração (speedup) | Não há implementação VHDL equivalente funcional nem linha de base comparável |
| Erro VHDL vs OpenCV para F, E, R, t | Saídas do VHDL indefinidas (`'U'`/`'X'`) |
| Cobertura de testes | Não há suíte automatizada; testbenches sem `assert` de valores |

## 8. Resultados das execuções

### 8.1 `run.sh` (T03, T04)

Saída (mensagens com acentos corrompidas apenas pelo redirecionamento de codificação do PowerShell):

```
Compilando pacotes base... / Compilando módulos principais... / Compilando testbench...
Elaborando design... / Executando simulação...
tb/tb_top.vhd:142:9:@1455ns:(report note): Teste SfM completo executado com sucesso!
tb/tb_top.vhd:143:9:@1455ns:(report note): Pipeline executado: Fundamental -> Essential -> Pose -> Triangulation
ghdl:info: simulation stopped by --stop-time @10us
```

Nenhum aviso ou erro do GHDL. As três repetições cronometradas da 1ª rodada geraram `wave.vcd` com o mesmo tamanho (78 943 B); os hashes das execuções 1 e 2 coincidem e o da 3ª difere. Nessa rodada o conteúdo não foi comparado; na reexecução (seção 8.6) os três VCDs foram comparados e são idênticos exceto pelo cabeçalho `$date`.

### 8.2 Saídas de `SfM_Top` em simulação (T12, T13)

Probe [tb_probe.vhd](evidencias_testes/vhdl_probes/tb_probe.vhd) após `ready='1'` (log: [log_probe.txt](evidencias_testes/logs/log_probe.txt)):

| Sinal | Valor observado |
|---|---|
| `fundamental_F` (9 elementos) | `UUUU…U` (32 bits `'U'`) |
| `essential_E` (9 elementos) | `XXXX…X` |
| `pose_R` (9) / `pose_t` (3) | `UUUU…U` |
| `points_3D(0)` | `[28509634, 8830239, 65536, 65536]` (= 435,02; 134,74; 1,0; 1,0 em Q15.16) |
| `points_3D(8)`, `points_3D(99)` | `[0, 0, 65536, 65536]` |

Interpretação (causa provável, com base nos fontes): em `ENFORCE_RANK2` (`F_out <= F_temp`, [src/fundamental_matrix.vhd](src/fundamental_matrix.vhd#L125)) e em `EXTRACT_POSE` (`R_temp <= R1`, [src/pose_extraction.vhd](src/pose_extraction.vhd#L94)) o sinal lido recebe a atribuição no mesmo ciclo; o valor lido é o anterior (`'U'`). Esse mecanismo não foi isolado por teste dedicado (por exemplo, trocando sinais por variáveis), pois isso exigiria alterar o código.

### 8.3 `EssentialMatrixCalculator` isolado (T10, T11)

Com F = (0,5; 0,25; 0,125; …) e K do testbench: E(GHDL) = `[[441745408, 220872704, −1016225792], [1128960000, 564480000, 946713600], [1726421504, −1284272896, 754397312]]` (inteiros Q15.16), idêntico à emulação em Python (`Mat3Mul`: soma de produtos de 64 bits, `>>16`, truncagem a 32 bits). Em reais: E(0,0) = 6 740,5 contra 137 812,5 esperado; E(0,2) = −15 506,4 contra +115 565,6. Isto é overflow do formato Q15.16 (K contém fx=525; `K ᵀ F K` cresce ≈ 525²).

### 8.4 Reuso do `SfM_Top` (T15)

Segundo `start` em 1456 ns: `ready` cai em 1465 ns e retorna a `'1'` em 1515 ns, antes de `pose_done` (1525), `fund_ready` (1555) e `tri_done` (2535). Causa provável: os sinais `*_ready/done` de cada módulo permanecem em `'1'` da execução anterior e o `top` os consome como se fossem novos. Evidência: ordem das transições no VCD ([log_vcd_probe2_handshake.txt](evidencias_testes/logs/log_vcd_probe2_handshake.txt)); saídas do 2º ciclo em [log_probe2.txt](evidencias_testes/logs/log_probe2.txt) (linhas `RUN2`).

### 8.5 Python

- `extract_points.py` (5×): saídas idênticas nas contagens; 5 conteúdos diferentes de `vhdl_points_data.txt` (seleção aleatória sem semente). Controle com img2 = img1: 1199 correspondências e 1199 inliers, exit 0, pontos com x1 = x2 (nenhum aviso de par degenerado).
- `generate_test_data.py` (2×): determinístico e igual ao `.npz` versionado.
- `visualize_vhdl_results.py` (2×): `plt.show()` emite aviso de backend não interativo em `Agg` (esperado). Inspeção visual das figuras: as epilinhas passam pelos pontos marcados e convergem para um ponto comum dentro da imagem 1 (epipolo próximo à caixa vermelha); o gráfico 3D mostra P2 com Z < 0 (profundidade negativa, consistente com `7/8` na checagem de cheirality). A mensagem final do script ("Processamento: 100% VHDL", "validado com sucesso") não é sustentada por seu código (T19).

### 8.6 Reexecução completa com GHDL (2026-10-16, 14:48)

Todos os testes de VHDL foram refeitos do zero em uma nova cópia temporária do repositório, com o mesmo GHDL 6.0.0 (mcode) e o script [reexecucao_ghdl.ps1](evidencias_testes/reexecucao_ghdl/reexecucao_ghdl.ps1) (logs e resumo em [reexecucao_ghdl](evidencias_testes/reexecucao_ghdl); GHDL chamado via `cmd /c` para evitar a quebra de linha e a codificação UTF-16 do PowerShell). Fontes `.vhd` e `run.sh` não modificados; os probes de [vhdl_probes](evidencias_testes/vhdl_probes) foram copiados para `tb/` apenas na cópia temporária.

| Verificação | Resultado da reexecução | Igual à 1ª rodada? |
|---|---|---|
| `run.sh` ×3 | exit 0 nas 3; mensagens em 1455 ns; `wave.vcd` 78 943 B | Sim |
| VCDs das 3 execuções, ignorando as 3 primeiras linhas (cabeçalho) | idênticos (1=2 e 2=3, comparação linha a linha); apenas `$date` difere | Novo (não havia sido comparado) |
| Análise individual (VHDL-93) dos 10 arquivos, elaboração e simulação direta de `tb_top` | 12/12 comandos com exit 0 | Sim |
| `tb_fundamental` em VHDL-93 | exit 1: `unit "env" not found in library "std"` | Sim |
| `tb_fundamental` com `--std=08` | 7/7 comandos exit 0; termina em 1020 ns | Sim |
| Design completo + `tb_top` em `--std=08` | 12/12 exit 0 | Sim |
| `ghdl --synth` (5 entidades) | 5/5 exit 0; netlists 54 209 / 30 255 / 69 488 / 271 109 / 424 742 B | Contagem de bytes diferente (correção de codificação, ver 7.2) |
| Handshake no VCD de `tb_top` | `fund_ready` 215, `ess_ready` 235, `pose_done` 285, `tri_done` 1335, `ready` 1355 ns | Sim, idêntico |
| `SfM_Top`: F / E / R / t | F: 9/9 `'U'`; E: 9/9 `'X'`; R: 9/9 `'U'`; t: 3/3 `'U'` | Sim |
| `points_3D` com os dados do `tb_top`, pontos reais regenerados e dados simulados | `((x1+x2)/2, (y1+y2)/2, 1, 1)` em 8/8 pontos em cada conjunto; `points_3D(8)` = `(0,0,1,1)` | Sim |
| `EssentialMatrixCalculator` isolado | 9/9 elementos iguais à emulação inteira; E(0,0) = 441 745 408 (6 740,5 em Q15.16) contra 137 812,5 ideal; 6 de 9 elementos fora da faixa | Sim |
| Reuso (2º `start`) | `ready` 0 em 1465 ns e 1 em 1515 ns; `pose_done` 1525, `fund_ready` 1555, `tri_done` 2535 ns; F/E/R/t do 2º ciclo continuam `'U'`/`'X'` | Sim, idêntico |

Conclusão da reexecução: nenhum resultado funcional mudou. A única diferença de medição foi o tempo de parede do `run.sh` (maior nesta rodada) e a correção dos tamanhos das netlists. Continuam não executados: GHDL em Linux nativo, backends gcc/llvm, síntese mapeada para FPGA e execução em hardware.

## 9. Análise

**Funcionamento operacional.** Compilação, elaboração, simulação e scripts Python rodam de forma estável e reprodutível para este par de imagens (com a exceção da seleção aleatória de pontos). O `run.sh` concluiu em ≈0,75 s no ambiente descrito.

**Validade científica.**

- *Lado Python/OpenCV:* para as 137 correspondências aceitas, a F estimada por RANSAC explica 129 com erro de Sampson médio < 0,33 px, e os 8 pontos do testbench são inliers legítimos (erro 0,24 px). Isto sustenta que as correspondências são geometricamente coerentes entre si. Já a pose e a triangulação dependem de K **assumido** e de F estimada com apenas 8 pontos (erro médio de 1,2 px nos 129 inliers); o resultado (7/8 com profundidade positiva, reprojeção 6,8–8,8 px) é de baixa confiança. Sem ground truth, a correção da pose/estrutura **não foi comprovada**. A forte componente planar (73,6 %) aumenta a incerteza.
- *Lado VHDL:* a única etapa com aritmética dependente da entrada que foi verificada é `E = KᵀFK` (bit-exata em relação à emulação), mas com F constante, com overflow Q15.16 em 6/9 elementos e, no sistema integrado, com `F='U'` e `E='X'`. Os pontos 3D são médias de pixels com Z = 1 e não representam estrutura 3D (reprojeção ≈ 10⁵ px). Logo, o resultado "VHDL" **não é cientificamente válido** como reconstrução.
- *Risco de falso positivo:* execução com exit 0, mensagem "sucesso" do testbench, PNG gerados e mensagem "validado com sucesso" do script de visualização coexistem com saídas indefinidas no VHDL. Nenhum desses sinais é evidência de correção.

**Desempenho.** Tempos de parede são de ferramentas diferentes e não são comparáveis entre si; não há base para falar em aceleração. A latência de 1235 ns é de tempo **simulado** de um modelo comportamental, com valores placeholder.

**Variabilidade.** Contagens do pipeline Python foram idênticas nas 5 execuções (incluindo RANSAC, 10/10); o que varia é a escolha dos 8 pontos (sem semente). O mesmo conjunto de contagens (1199/1494/137/129) foi obtido numa execução prévia com OpenCV 5.0.0 headless no WSL durante a auditoria anterior.

## 10. Problemas identificados (sem correções aplicadas)

| # | Problema | Evidência | Causa provável | Possível correção (futura) |
|---|---|---|---|---|
| P1 | F, R, t indefinidos (`'U'`) e E `'X'` na saída do `SfM_Top` | T12, 8.2 | Leitura de sinal atribuído no mesmo ciclo (`F_out <= F_temp`, `R_temp <= R1`) | Usar variáveis ou estado adicional; inicializar saídas |
| P2 | Algoritmos placeholder (F constante, SVD identidade, E ignorada na pose, triangulação por média) | Leitura dos fontes; T13/T14/T19 | Protótipo incompleto | Implementar etapas; validar contra OpenCV |
| P3 | Overflow Q15.16 em `K ᵀ F K` com `fx=525` | T10/T11 | Faixa ±32768 insuficiente sem normalização | Normalizar coordenadas (K⁻¹) ou ampliar o formato |
| P4 | `ready` prematuro em reuso | T15 | Flags `ready/done` nunca limpas pelos módulos | Limpar flags ao receber `start`; handshake de 4 fases |
| P5 | Testbenches sem verificação de valores | Leitura; T04 | Só `report` incondicional | `assert` com valores esperados e checagem de metavalores |
| P6 | `tb_fundamental` não compila com o padrão do `run.sh` e não está em `run.sh` | T06 | `use std.env.stop` exige VHDL-2008 | Compilar com `--std=08` ou usar `assert false … severity failure` |
| P7 | Script de visualização rotulado "VHDL" não usa saídas do VHDL | T19 | Pontos fixos + OpenCV | Renomear/rotular ou ler resultados reais (exigem exportação dos arrays) |
| P8 | Seleção aleatória sem semente; par degenerado aceito; ausência de imagem retorna exit 0 | T16, T20, T21 | `np.random.choice` sem seed; sem validação | Semente configurável, verificação de paralaxe/homografia, `sys.exit(1)` |
| P9 | VCD do GHDL não contém arrays | `wave.vcd` ("not handled") | Limitação do GHDL para tipos array | Expor sinais escalares por elemento ou imprimir via `report`/arquivo |
| P10 | Árvore de trabalho com CRLF no Windows quebra scripts bash em Linux/WSL | T23; `git ls-files --eol`: índice LF, árvore CRLF | `core.autocrlf=true` | `.gitattributes` com `*.sh text eol=lf` |
| P11 | Codificação de comentários difere conforme a plataforma (cp1252 no Windows) | T17 | `open()` sem `encoding` | `open(..., encoding='utf-8')` |

Observação: o item "Possíveis valores indefinidos" do README (seção "Limitações") foi **confirmado** por simulação neste relatório; o README não foi alterado nesta tarefa.

## 11. Testes não realizados

| Item | Motivo |
|---|---|
| `Epipolar_Geometry.ipynb` | Baixa outras imagens via `gdown` (Google Drive) e instala pacotes com `!pip`; não usa `images/`; fora do escopo das duas imagens fornecidas |
| `setup_env.sh` | Criaria/removeria `.venv` na raiz do projeto; substituído por venv temporário com os mesmos pacotes (`opencv-python numpy matplotlib`), **sem** pinos de versão (o script também não os define) |
| `run.sh` em Linux nativo com GHDL Linux; outros backends (gcc/llvm) | GHDL Linux não disponível; instalação exigiria `sudo` |
| GTKWave | Não instalado; o VCD não contém as matrizes de qualquer forma |
| Síntese para FPGA, recursos, Fmax, consumo, execução física | Sem ferramentas/dispositivo/arquivos de projeto |
| Comparação VHDL × OpenCV de F, E, R, t | Saídas do VHDL indefinidas |
| Testes com outros pares de imagens, com ground truth, ou com outro K | Fora do escopo (duas imagens fornecidas) |
| Teste dedicado da causa de P1 (variáveis em vez de sinais) | Exigiria modificar o código |

## 12. Conclusão

- **Demonstrado:** (a) as duas imagens são legíveis e compatíveis com correspondência SIFT; (b) o código VHDL compila e simula com GHDL (VHDL-93 e VHDL-2008, exceto `tb_fundamental` em VHDL-93) e o handshake da cadeia de quatro módulos termina em 1355 ns simulados; (c) `Mat3Mul`/`EssentialMatrixCalculator` reproduzem bit a bit a aritmética inteira esperada; (d) os scripts Python executam e geram os arquivos esperados; (e) `ghdl --synth` aceita as cinco entidades.
- **Falhou:** saídas F, E, R, t indefinidas; overflow de E em Q15.16; triangulação sem significado geométrico; `ready` prematuro em reuso; `tb_fundamental` em VHDL-93; ausência de validação em `extract_points.py`.
- **Não validado:** qualquer qualidade de reconstrução 3D (VHDL ou OpenCV) sem ground truth e com K assumido; síntese real, recursos, frequência, consumo e execução em hardware.
- O projeto **não** pode ser considerado funcional como pipeline SfM em VHDL; ele funciona como esqueleto de simulação (FSM + handshake) e como pipeline Python de extração de pontos e visualização.

## 13. Reprodução dos testes

Pré-requisitos verificados: GHDL (versão acima ou outra com suporte a VHDL-93/08), bash, Python 3 com `opencv-python numpy matplotlib`.

```powershell
# 1) Cópia de trabalho (não usar o repositório diretamente)
Copy-Item <repo> $env:TEMP\sfm_audit\repo -Recurse

# 2) VHDL
cd $env:TEMP\sfm_audit\repo
& "C:\Program Files\Git\bin\bash.exe" ./run.sh        # GHDL no PATH; em Linux: ./run.sh
# Espera-se: reports em 1455 ns; wave.vcd (≈78 KB com mcode)

# 3) Python (venv temporário)
python -m venv venv; .\venv\Scripts\python -m pip install opencv-python numpy matplotlib
$env:MPLBACKEND='Agg'
.\venv\Scripts\python extract_points.py
.\venv\Scripts\python generate_test_data.py
.\venv\Scripts\python visualize_vhdl_results.py
```

Para repetir os probes e análises, use os arquivos de [evidencias_testes](evidencias_testes): os `.vhd` em `vhdl_probes/` são analisados após `run.sh` (copiar para `tb/`, `ghdl -a --workdir=work tb/<arquivo>.vhd`, `ghdl -e --workdir=work <entidade>`, `ghdl -r --workdir=work <entidade> --stop-time=10us`). Os scripts em `scripts/` têm caminhos absolutos para `%TEMP%\sfm_audit` e precisam ser ajustados; `make_probe*.ps1` regeneram os probes a partir de `tb/tb_top.vhd`. Todos os logs, em UTF-8, estão em `evidencias_testes/logs/` (linhas longas podem estar quebradas pelo redirecionamento do PowerShell).

Nota de verificação: o comando `./run.sh` e os scripts Python foram executados como descrito. Os comandos de probes e de `--std=08`/`--synth` foram executados com os nomes de arquivo `*_audit.vhd` na cópia temporária; os nomes em `vhdl_probes/` diferem apenas pelo sufixo.

## 14. Arquivos gerados no repositório

- `RELATORIO_TESTES.md` (este arquivo).
- `evidencias_testes/logs/` — logs das execuções e [ambiente.txt](evidencias_testes/logs/ambiente.txt).
- `evidencias_testes/scripts/` — scripts de análise e geração de probes (usados nesta sessão).
- `evidencias_testes/vhdl_probes/` — testbenches temporários usados nos testes exploratórios.
- `evidencias_testes/reexecucao_ghdl/` — logs, resumo e script da reexecução completa com GHDL (seção 8.6).

Código-fonte (`src/`, `tb/`, `*.py`, `*.sh`), imagens e demais arquivos do projeto não foram modificados nesta tarefa.
