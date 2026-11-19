# Gerenciador Python–VHDL — Etapa 2

A Etapa 4 acrescentou cache de assinaturas por instância e a opção
`--verify-unprofiled-software`. Após a alteração da assinatura, gere novos
perfis para executar a política conservadora. Veja o contrato e a comparação
com a versão original no [relatório da Etapa 4](STAGE4.md).

O gerenciador seleciona o cálculo `E = Kᵀ F K` entre NumPy float64 e o kernel
Q15.16 simulado. Reutiliza `GhdlBackend` da Etapa 1, sem alterar os módulos VHDL,
os testbenches anteriores ou os scripts OpenCV. O texto da Tarefa 2/3 define o
escopo desta entrega; `objective.md` permanece como contexto do trabalho maior.

## Instalação e CLI

Use o ambiente da Etapa 1, com Python 3.10+ e GHDL com suporte a VHDL-2008.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m hybrid_sfm --backend software
python -m hybrid_sfm --backend rtl_simulated --input examples/essential_identity.json

# Perfis precisam ser medidos no ambiente em que a seleção ocorrerá.
python -m hybrid_sfm --characterize --repeats 3 --warmup 1 --output perfis.json
python -m hybrid_sfm --backend auto --profiles perfis.json --max-error 0.01
python -m hybrid_sfm --backend auto --profiles perfis.json --prefer prefer_rtl --fallback software
python -m hybrid_sfm --backend auto --profiles perfis.json --max-seconds 1 --output decisao.json

REQUIRE_GHDL=1 python -m unittest discover -s tests -v
```

No Windows, use `.venv/Scripts/python.exe`. Para o GHDL portátil já disponível
neste checkout em `build/tools/ghdl`, configure em PowerShell:

```powershell
$env:GHDL = (Resolve-Path ./build/tools/ghdl/bin/ghdl.exe).Path
$env:REQUIRE_GHDL = '1'
& ./.venv/Scripts/python.exe -m unittest discover -s tests -v
```

O modo software não requer GHDL nem OpenCV. Para estimar F a partir de pontos,
instale a dependência opcional `python -m pip install -r requirements-sfm.txt`.
Para exigir esse teste adicional, defina também `REQUIRE_OPENCV=1`.
Depois de instalar as dependências, os caminhos funcionam sem acesso à rede.

A entrada padrão é o caso fixo `examples/essential_identity.json`. `--input`
aceita `{"F": matriz3x3, "K": matriz3x3}` ou
`{"points1": pontosNx2, "points2": pontosNx2, "K": matriz3x3}`.
Caracterização aceita um par F/K ou `{"cases": [par1, par2, ...]}`; pontos devem
ser convertidos em F antes de caracterizar. Use `--input-class` para identificar
a classe de entradas, mantendo o mesmo identificador ao selecionar.

Toda saída é JSON, em stdout ou `--output`. Nos modos novos: exit 0 para `ok`
ou `fallback_ok`, 2 para inviabilidade/falha/violação de requisitos e 1 para erro
de entrada/configuração/arquivo. A caracterização pode produzir perfis com falhas;
exit 1 sinaliza backend indisponível. Não confunda exit 0 da caracterização com
qualidade aprovada: examine `failure_rate` e os diagnósticos.
Sem `--backend`, a CLI mantém o formato e os códigos da Etapa 1.

## Interface pública

```python
from hybrid_sfm.backends import ExecutionConfig, run_backend
from hybrid_sfm.manager import ExecutionManager, Requirements
from hybrid_sfm.profiles import characterize, load_profiles
from hybrid_sfm.metrics import write_json

config = ExecutionConfig(timeout=30, max_cycles=10)
profiles = characterize([(F, K)], config=config, repeats=3, warmup=1)
write_json("perfis.json", profiles)

manager = ExecutionManager(load_profiles("perfis.json"), config=config)
result = manager.execute(F, K, mode="auto", requirements=Requirements(
    max_error=0.01, max_seconds=1, preference="min_time", fallback="software"))
write_json("decisao.json", result)

# Mesma interface para avaliar cada backend sem seleção/fallback.
attempt = run_backend("software", F, K, config)
```

`run_backend` recebe o nome, F, K e `ExecutionConfig`; retorna E, backend, estado,
validade, métricas, diagnóstico e detalhes da execução. O adaptador RTL preserva
os registros de compilação, simulação e referência da Etapa 1. Não implementa
outra rotina de compilação ou parsing.

`ExecutionManager.execute` aceita `software`, `rtl_simulated` ou `auto`.
Modos fixos executam somente o backend solicitado, sem precisar de perfis e sem
fallback, independentemente da preferência. Os limites são verificados depois.

## Erro e tempo: significado dos limites

O contrato de erro é `max(abs(E_backend[i,j] - (K.T @ F @ K)[i,j]))`, sobre os
nove componentes, com NumPy float64 como referência. É uma norma máxima sobre
os componentes, sem normalização e sem unidade universal: usa a unidade/escala
de E determinada pelas entradas. Não é a norma matricial de soma das linhas,
nem um erro relativo ou invariante à escala. O erro do software é zero por
definição desse contrato, não uma afirmação de aritmética real exata.

O RTL quantiza as entradas em direção a zero e mantém o truncamento/wrap das
duas multiplicações originais. Overflow, discrepância inteira, valores não
finitos e falhas do simulador invalidam a tentativa antes das preferências.
Não há normalização silenciosa para favorecer o RTL.

`max_seconds` é um orçamento observado da requisição ao gerenciador: inclui
checagem dos perfis/versões, decisão, tentativas, validação e fallback, até a
checagem final. Exclui estimação prévia de F, leitura/escrita JSON e inicialização
do interpretador. Não é um prazo de tempo real garantido: uma tentativa pode
ultrapassá-lo e depois ser rejeitada. `timeout` é o watchdog por subprocesso
GHDL, não o orçamento inteiro da requisição.

Os perfis medem `observed_seconds` da tentativa uniforme, incluindo conversão,
backend e validação numérica. No RTL incluem o modelo inteiro/referências da
Etapa 1, consulta do cache e eventual compilação. O perfil não finge medir
apenas o produto matricial. A preparação dos perfis fica fora da decisão.

## Seleção e rastreabilidade

1. Verifica domínio e disponibilidade, incluindo faixa Q15.16 para RTL.
2. Consulta perfis com mesma classe, envelope por componente e assinatura da
   implementação/ambiente. Não executa o caso corrente para obter seu erro.
3. Rejeita candidatos sem perfil compatível, com falhas observadas (inclusive
   no aquecimento), erro previsto excessivo ou tempo previsto acima do orçamento
   restante. Perfis sobrepostos são combinados pelos maiores erro e tempo.
4. `min_time` escolhe o menor máximo de tempo observado. Empates escolhem
   software. `prefer_rtl` escolhe RTL quando viável; caso contrário, software.
5. Executa a escolha e verifica erro atual, validade e tempo. Essa verificação
   é posterior à decisão, inclusive quando o backend internamente usa referências.
6. Se necessário, tenta o fallback permitido e verifica novamente os limites,
   incluindo o tempo gasto na tentativa anterior.

Sem opção viável, o estado é `no_feasible_configuration` e não há tentativa.
Sem perfis, `auto` também retorna esse estado; não força software como escolha.

Fallback: `none` desativa; `software` permite apenas software; `other` permite
o outro backend. O candidato de fallback precisa de perfil compatível e precisa
caber no orçamento restante. O mesmo backend não é repetido automaticamente.
Falha de processo, timeout, parsing, estado indefinido, overflow ou violação
posterior podem acioná-lo. Se não houver fallback viável, a falha permanece.

O resultado expõe `selected_backend`, `backend`, `decision.candidates` com motivos
de eliminação e IDs dos perfis, `attempts`, `fallback` e `metrics`. Cada tentativa
guarda o diagnóstico e os tempos. `initial_selection_success=false` e
`failure_count` continuam registrando a falha mesmo com `fallback_ok`.
O E do resultado final só é preenchido quando a tentativa final é válida e
respeita os limites; resultados rejeitados ficam nos diagnósticos/detalhes.

## Perfis medidos

`characterize` grava classe, envelope por componente de F/K, entradas originais,
ordem, aquecimento, repetições, amostras, erros, tempos, falhas, data UTC e ID do
experimento. Também registra Python, NumPy, sistema/CPU, hash da implementação,
e versão/caminho/configuração do GHDL quando utilizado. `ghdl=null` no perfil
software significa que esse caminho não utiliza a ferramenta.

O documento `schema_version=1` inclui perfis e backends indisponíveis. Resumos
são conferidos contra as amostras ao carregar. A assinatura cobre os adaptadores
e as fontes relevantes; alterar versão, configuração RTL ou código invalida o
reuso. Caches existentes são reutilizados e os aquecimentos ficam registrados.

Perfis são **observações empíricas**, sem garantia uniforme de erro/tempo para
todo o envelope. O intervalo entre amostras não equivale a validação exaustiva.
Não extrapole para outra classe, escala ou máquina; caracterize novamente.
Não há autenticação criptográfica da procedência de um arquivo de perfis.
Perfis sintéticos existem somente nos testes unitários e não alimentam as
evidências experimentais entregues.

## Integração mínima com SfM

```python
from hybrid_sfm.sfm import estimate_essential, require_valid_essential

# F fornecida, ou points1/points2 já extraídos e filtrados.
result = estimate_essential(K, points1=pts1, points2=pts2,
                            manager=manager, mode="auto", requirements=requirements)
E = require_valid_essential(result)
# Só depois desta barreira prossiga para pose/triangulação em Python.
```

O caminho de correspondências usa `cv2.findFundamentalMat(..., FM_8POINT)`, como
o script de visualização existente, com pelo menos oito pares finitos. Recusa
falha de estimação e F degenerada. Não implementa outro RANSAC ou matching.
`require_valid_essential` interrompe a continuação se E estiver inválida,
indefinida ou nula. O gerenciador ainda permite zeros em testes numéricos
controlados; essa matriz não pode passar pela barreira geométrica.
Não foram acrescentadas chamadas de pose ou triangulação que consumam E sem
verificação. O limite absoluto não comprova qualidade geométrica nem substitui
calibração, cheirality ou avaliação de reconstrução.

## Demonstração verificável e limitações

```bash
python -m examples.demo_manager --inject-timeout --output-dir build/manager_demo
```

O script mede três repetições após um aquecimento, exporta `profiles.json` e
`decisions.json` e mostra os modos fixos, seleção automática, preferência por RTL,
restrição impossível e fallback. `--inject-timeout` reduz deliberadamente o
watchdog da simulação a 1 µs e mata um subprocesso real; isso é injeção de falha,
não falha natural nem resultado para taxa de confiabilidade do artigo.

A execução registrada em [evidencias_testes/gerenciador](../evidencias_testes/gerenciador)
escolheu software com `min_time`, RTL com `prefer_rtl`, retornou inviabilidade
com orçamento zero e executou fallback para software após o timeout injetado.
Tempos e detalhes constam nos JSONs; são demonstrações operacionais em um caso
controlado, sem conclusão comparativa de desempenho para publicação.

A checagem de assinaturas tem custo de parede próprio, inclusive consulta de
versão GHDL. Na demonstração esse custo foi maior que o próprio cálculo NumPy;
não há alegação de aceleração. O cache continua sem bloqueio entre processos.
A avaliação posterior está em [EXPERIMENTS.md](EXPERIMENTS.md). A implementação
da Etapa 2 não inclui FPGA física,
medidas energéticas ou recursos de síntese. Os defeitos do pipeline `SfM_Top`
continuam documentados e não foram corrigidos nesta etapa.
