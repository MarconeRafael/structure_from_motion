# Reprodução dos experimentos A–E

Esta entrega atende à Tarefa 3/3. `objective.md` fornece o contexto geral; não
autoriza atribuir à simulação resultados de hardware físico.

## Instalação

Requer Python 3.10+ compatível com os wheels fixados, GHDL com VHDL-2008 e Git.
NumPy/OpenCV são usados nos dados e backends; Matplotlib gera figuras estáticas
sem GUI. Nenhum serviço remoto é utilizado depois da instalação.

```bash
# Linux/WSL: instale GHDL na própria distribuição antes da execução.
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-experiments.txt
python run_experiments.py --config experiments/config.json
```

No PowerShell deste checkout:

```powershell
$env:GHDL = (Resolve-Path ./build/tools/ghdl/bin/ghdl.exe).Path
& ./.venv/Scripts/python.exe -m pip install -r requirements-experiments.txt
& ./.venv/Scripts/python.exe run_experiments.py --config experiments/config.json
```

Também há `--ghdl /caminho/ghdl` e `--output-dir /diretorio/base`. Caminhos da
configuração são relativos à raiz do projeto. Cada execução cria um subdiretório
UTC único e não sobrescreve evidências anteriores. `build/` contém apenas caches
e cópias descartáveis. O cache Matplotlib padrão também fica em `build/`.

Para reproduzir exatamente as versões Python de uma execução registrada,
instale seu `requirements-lock.txt` em um novo venv. O binário GHDL deve ser
obtido separadamente na mesma versão/backend. Caminhos de venv fazem parte da
assinatura dos perfis: um ambiente novo precisa caracterizar novamente.

## O que o comando faz

1. Confere dependências e assinaturas e salva configuração, hashes e versões.
2. Executa toda a suíte com GHDL/OpenCV obrigatórios; uma falha impede benchmarks.
3. Gera os três splits e regenera o dataset para conferir determinismo das sementes.
4. Em cada repetição independente, compila em um cache novo e caracteriza somente
   o conjunto de treino, mantendo os perfis e seus aquecimentos registrados.
5. Usa somente o conjunto de desenvolvimento para congelar o cenário padrão.
6. Executa A (números), B (tempos) e C (políticas) nos casos finais, com ordens
   alternadas por uma semente explícita.
7. Executa D com injeções controladas segregadas das observações normais.
8. Compara repetibilidade E, exporta tabelas, figuras e resumo Markdown.

Qualquer saída inválida permanece registrada. O resumo de latências válidas
exclui overflow/falha e apresenta também a população pareada, sem ocultar as
taxas de invalidez da outra tabela. Não há ajuste de política a partir da avaliação.

## Arquivos de cada execução

| Arquivo | Conteúdo |
|---|---|
| `config.json`, `metadata.json` | Configuração anterior às medidas, hashes, versões, Git e status |
| `requirements-lock.txt`, `tests.txt` | Ambiente Python e auditoria executada |
| `dataset.json`, `splits.json` | Matrizes, geometria, correspondências, IDs e sementes |
| `profiles_*.json` | Perfis medidos por repetição, classe e backend |
| `development.csv`, `frozen_policy.json` | Escolha anterior à avaliação final |
| `raw.jsonl` | Saídas completas, stdout/stderr, processos e decisões por observação |
| `numeric.csv` | Comparação NumPy/modelo/RTL e erros geométricos quando definidos |
| `timing.csv` | Tempos e componentes observáveis, incluindo casos rejeitados |
| `policies.csv`, `comparisons.csv` | Mesmos casos/requisitos para as três políticas e comparação posterior |
| `faults.csv` | Injeções, detecção, falha inicial e recuperação |
| `reproducibility.csv` | Estabilidade entre repetições |
| `table_*.csv`, `summary.json`, `RESULTS.md` | Agregações derivadas automaticamente |
| `figures/*.png`, `figures/*.pdf` | Erros, ECDF de latência e sucesso das políticas |

`metadata.status=complete` exige término do fluxo e aprovação das verificações
experimentais. Um diretório interrompido com status `running` não é uma avaliação
concluída. Falha em verificação final gera `failed_checks` e exit não zero.

O programa não exige um valor final de sucesso de política: inviabilidade,
quantização e overhead são resultados científicos a registrar, não motivo para
alterar retrospectivamente a configuração.

Metodologia: [METHODOLOGY.md](METHODOLOGY.md). Resultados entregues:
[RESULTS.md](RESULTS.md). Ameaças e pendências: [LIMITATIONS.md](LIMITATIONS.md).

A verificação entregue também recriou um venv em `build/clean_experiments_env`,
instalou o lock da execução principal e repetiu o mesmo comando com
`--output-dir experiments/results/clean_install`. Os dois conjuntos brutos foram
preservados. A comparação fica em `clean_install_comparison.json` na execução
principal; recriar o venv não exige reutilizar seus perfis antigos.
