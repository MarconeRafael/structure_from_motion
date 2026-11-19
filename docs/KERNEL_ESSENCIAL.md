# Kernel essencial isolado — Etapa 1

Esta etapa valida `E = Kᵀ F K` sem executar os placeholders do restante de SfM.
O gerenciador posterior está documentado em [GERENCIADOR.md](GERENCIADOR.md).
O escopo solicitado está na Tarefa 1/3. `objective.md` descreve o trabalho maior;
gerenciador, políticas de seleção e benchmarks finais permanecem para outras etapas.

## Instalação e execução

Use Python 3.10 ou superior compatível com NumPy 2.2.6 e GHDL com VHDL-2008.
O pacote não requer OpenCV, GUI, FPGA ou acesso à rede depois da instalação.
Os scripts legados continuam com suas dependências em `setup_env.sh`.

Linux/WSL (instale GHDL na própria distribuição):

```bash
sudo apt install ghdl python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
ghdl --version
REQUIRE_GHDL=1 python -m unittest discover -s tests -v
python -m hybrid_sfm --input examples/essential_identity.json --output resultado.json
```

Windows/PowerShell, com GHDL já instalado ou descompactado:

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
$env:GHDL = 'C:\caminho\ghdl\bin\ghdl.exe'
$env:REQUIRE_GHDL = '1'
& ./.venv/Scripts/python.exe -m unittest discover -s tests -v
& ./.venv/Scripts/python.exe -m hybrid_sfm --input examples/essential_identity.json --output resultado.json
```

`GHDL` designa um executável, sem argumentos de shell. Também há `--ghdl` e
`--timeout` na CLI. Códigos de saída: 0 para correspondência com o modelo sem
overflow; 1 para entrada inválida, ferramenta ausente, erro de compilação,
simulação, parsing ou discrepância; 2 para resultado bit-exato com overflow.

Sem GHDL, os testes Python executam e o grupo RTL fica explicitamente marcado
como ignorado. `REQUIRE_GHDL=1` transforma a ausência em falha da suíte e deve
ser usado para validar a entrega completa.

## API e resultados

```python
import numpy as np
from hybrid_sfm.ghdl_backend import GhdlBackend

backend = GhdlBackend(timeout=30)
F = np.array([[0, -1, 0.5], [1, 0, -0.25], [-0.5, 0.25, 0]])
K = np.eye(3)
result = backend.run(F, K)
print(result["E"], result["bit_exact"], result["overflow_events"])

batch = backend.run_batch(
    [(F, K), (2 * F, K), (F, K)],
    reset_before=[True, False, True],
)
```

`run_batch` executa os casos na mesma simulação. Por padrão, reseta somente
antes do primeiro; o primeiro reset é obrigatório. As matrizes são sempre 3×3,
reais e finitas. A referência aceita qualquer matriz desse formato para permitir
testes controlados; não valida posto 2 nem propriedades de uma calibração física.

Cada resultado contém:

| Campo | Significado |
|---|---|
| `E`, `E_raw` | Saída real exportada pelo GHDL, convertida para float64 e como signed32 |
| `reference_float64` | NumPy `K.T @ F @ K`, sem ponto fixo |
| `reference_integer_raw` | Modelo inteiro independente do simulador |
| `reference_quantized_float64` | NumPy aplicado às entradas já quantizadas |
| `bit_exact` | Igualdade dos nove inteiros; divergência causa exceção |
| `overflow_events` | Estágio, posição e tipo: acumulador64 ou resultado32 |
| `valid`, `status` | `ok` sem overflow; `numeric_overflow` com `valid=false` |
| `max_abs_error` | Maior diferença absoluta entre GHDL e referência original |
| `input_quantization_max_abs_error` | Diferença da referência quantizada contra a original |
| `arithmetic_max_abs_error` | Diferença do RTL contra a referência quantizada |
| `cycles` | Bordas de clock até observar conclusão depois de start |
| `execution` | Tempos, estado do cache, versão, comandos, stdout/stderr e exit codes |

`valid=true` atesta correspondência com o modelo e ausência de overflow; não
atesta tolerância de erro geométrico. A quantização pode eliminar componentes
pequenos de F. Os erros numéricos precisam ser avaliados pelo consumidor.
Os três máximos de erro não são parcelas escalares aditivas.

Erros geram `BackendError` com `stage` e, quando disponível, `process`, contendo
comando, stdout, stderr, código de saída e tempo. Não há fallback que esconda falhas.

## Contrato numérico verificado

- Q15.16: inteiros signed32 divididos por 65536. Faixa inclusiva
  `[-32768, 32767.99998474121]` e resolução `0.0000152587890625`.
- A interface quantiza como o gerador existente: `int(x * 65536)`, em direção
  a zero. Rejeita valores fora da faixa **antes** da quantização, inclusive
  valores ligeiramente além de um extremo que truncariam para um inteiro válido.
- `Mat3Mul` acumula três produtos signed32×signed32 em signed64, com wrap
  a cada adição. Depois extrai `(47 downto 16)`: deslocamento aritmético de 16
  seguido de wrap signed32. Para negativos, o descarte de bits corresponde ao
  piso, não ao truncamento em direção a zero usado na conversão de entrada.
- O kernel primeiro calcula `F*K`, trunca essa matriz, e então calcula
  `K.T*(F*K)`, truncando novamente. Alterar a associação das multiplicações
  no modelo inteiro alteraria o contrato.
- O modelo usa inteiros Python para os produtos e para detectar overflow antes
  de aplicar os wraps explícitos; não depende do overflow implícito do NumPy.
  Registra até overflow transitório de acumulador que possa desaparecer depois.
- Não há saturação, escalonamento automático, normalização nem alargamento do RTL.
  Correspondência bit a bit com overflow não demonstra correção matemática.

Exemplo analítico de overflow: `F=I`, `K=200I`. NumPy retorna `40000I`, enquanto
o RTL retorna `-25536I`. A interface devolve os nove valores, `bit_exact=true`,
`numeric_overflow` e `valid=false`. O exemplo de F constante e K=525 do relatório
histórico também possui overflow; o teste mantém esse caso explicitamente inválido.

## Controle e protocolo VHDL

O RTL original foi preservado. Seu reset é síncrono, prioritário a start, e zera
E e ready. Cada borda com start alto calcula E; ready permanece alto até reset.
Não existe pulso de conclusão para cada pedido. O testbench espera uma nova borda
de clock após start, em vez de aguardar uma transição de ready que pode não ocorrer.
Com o RTL atual, cada pedido conclui em uma borda observada; as saídas são
amostradas 1 ns após a borda para permitir a propagação por delta cycles.

O testbench verifica prioridade do reset, E=0 após reset, estabilidade durante
idle e valores estritamente binários. `U`, `X`, `Z`, `W`, `L`, `H` e `-` são
rejeitados antes de converter qualquer elemento para inteiro.

`tb/tb_essential_io.vhd` usa `textio` e genéricos `input_file`, `output_file`,
`max_cycles` (padrão 10). Entrada ASCII: quantidade de casos na primeira linha;
por caso, flag de reset (0/1), nove inteiros de F e nove de K, um por linha,
em ordem de linhas. Saída: cabeçalho `essential-q15.16-v1`, seguido de uma
linha por caso: índice a partir de zero, ciclos e nove inteiros E separados por
espaços. O parser exige cabeçalho, contagem, índices, ciclos e limites válidos.
Não se utiliza VCD para obter matrizes.

Há timeout em ciclos no testbench e timeout de parede por subprocesso. Ambos
causam falha. Os arquivos são abertos dentro do processo de estímulo para
permitir elaboração estática sem arquivos de entrada presentes.

## Compilação e tempos

Somente cinco fontes são analisadas, nesta ordem: `fixed_pkg.vhd`,
`algebra_pkg.vhd`, `algebra_pkg_body.vhd`, `essential_matrix.vhd` e o testbench.
Usa-se VHDL-2008 por causa de `std.env.finish`. `src/top.vhd` e os outros módulos
SfM não participam dessa compilação.

O cache fica em `build/essential/`. A chave inclui hashes e timestamps das
fontes, executável/versão GHDL e flags. O manifesto só é escrito após análise e
elaboração bem-sucedidas; os hashes dos artefatos são conferidos antes do reuso.
Artefato removido/corrompido ou fonte alterada exige recompilação.
Arquivos de entrada/saída usam um diretório temporário por execução, removido
ao terminar. Não compartilhe o mesmo cache entre compilações concorrentes;
esta etapa não implementa bloqueio entre processos.

`compilation.seconds` soma os subprocessos de análise e elaboração (zero em
cache hit). `simulation.seconds` mede o subprocesso GHDL inteiro, incluindo
inicialização/JIT e simulação; esses custos não foram separados artificialmente.
Preparação/referências, serialização e parsing são medidos separadamente.
`total_seconds` inclui também consulta de versão, hashes, cache e limpeza.
Em lote os tempos de execução são compartilhados, não tempos por matriz.
Clock e ciclos são tempo lógico simulado, sem equivalência demonstrada com FPGA.

## Verificação desta entrega

Os resultados efetivamente executados estão no adendo da Etapa 1 em
[RELATORIO_TESTES.md](../RELATORIO_TESTES.md). A suíte cobre identidade, zeros,
soluções analíticas, negativos, extremos, rejeição de entradas, casos aleatórios
com semente 42, mudança de F/K, reuso sem reset e repetição após reset.
Também injeta defeitos em cópias temporárias do RTL para provar detecção de
compilação inválida, travamento, estados não binários e resultado definido errado.

## Limitações preservadas

| Limitação | Consequência |
|---|---|
| Overflow Q15.16 | Resultados envolvidos são marcados inválidos; RTL mantém wrap |
| Quantização de F pequena | Pode destruir informação; erro é exposto, sem normalização automática |
| ready retido | Consumidor precisa respeitar o contrato de clock/start ou reset |
| Pipeline original com placeholders e U/X | `run.sh` não constitui prova de correção geométrica |
| Cache sem bloqueio entre processos | Compilações no mesmo cache devem ser sequenciais |
| Simulação RTL | Não demonstra aceleração nem recursos físicos de FPGA |
| Interface original desta etapa | A seleção e o fallback foram acrescentados na Etapa 2; benchmarks finais permanecem fora do escopo |
