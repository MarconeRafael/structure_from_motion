# Resultados medidos — execução 20261119T170335054730Z

Gerado automaticamente. Configuração e fontes identificadas em `metadata.json`.
São medidas de software e simulação RTL; nenhuma latência física de FPGA foi medida.

Dataset: 59 casos, 16 na avaliação final.
Observações: 32 numéricas, 320 temporais,
960 de políticas e 21 de falhas controladas.
Caracterização, desenvolvimento e avaliação possuem identificadores distintos (`splits.json`).
Os perfis usam somente o primeiro conjunto; `frozen_policy.json` foi salvo antes da avaliação.

## A — Validação numérica

`valid_no_overflow` significa equivalência inteira sem overflow, não qualidade geométrica.
Os erros de casos com overflow ficam visíveis, mas suas latências são excluídas da
população válida das tabelas de desempenho. Matriz essencial nula torna indefinida
a comparação geométrica normalizada. Consulte cada caso em `numeric.csv`.

| category | samples | bit_exact | valid_no_overflow | overflow | max_absolute_error_all | max_absolute_error_valid |
|---|---|---|---|---|---|---|
| controlled | 22 | 22 | 16 | 6 | 3.09218e+14 | 2.69005e-05 |
| repository_images | 4 | 4 | 4 | 0 | 3.21034 | 3.21034 |
| synthetic_geometry | 6 | 6 | 6 | 0 | 0.0273545 | 0.0273545 |

## B — Tempos de parede

Segundos por tentativa incluindo validação. `paired_valid` compara exatamente os
mesmos pares/repetições válidos nos dois caminhos. Percentis usam interpolação
linear, sem inferência sobre caudas raras. Compilação fria está em `raw.jsonl`;
compilação, preparo, serialização, processo GHDL e parsing estão em `timing.csv`.
Inicialização/JIT e simulação não são separáveis nesta instrumentação e ficam
marcados como não medidos, sem subtração de estimativas.

| backend | population | samples | seconds_median | seconds_p90 | seconds_p95 |
|---|---|---|---|---|---|
| software | all_valid | 160 | 3.9e-05 | 7.67e-05 | 8.486e-05 |
| software | paired_valid | 130 | 3.875e-05 | 7.08e-05 | 8.272e-05 |
| rtl_simulated | all_valid | 130 | 0.0878409 | 0.0957182 | 0.0993274 |
| rtl_simulated | paired_valid | 130 | 0.0878409 | 0.0957182 | 0.0993274 |

## C — Políticas e restrições

Tempos abaixo incluem requisições sem opção viável e tentativas rejeitadas;
consulte conjuntamente a taxa de validade. O custo da decisão e o orçamento
incluem verificações de versões/assinaturas. As preferências/requisitos foram
declarados em `config.json` antes de observar os resultados finais.

| scenario | policy | requests | valid | no_feasible | fallbacks | error_violations | time_overruns | seconds_median | decision_seconds_median |
|---|---|---|---|---|---|---|---|---|---|
| balanced | software | 64 | 64 | 0 | 0 | 0 | 0 | 5.64e-05 | 2.695e-05 |
| balanced | rtl_simulated | 64 | 40 | 0 | 0 | 12 | 0 | 0.0887511 | 2.445e-05 |
| balanced | auto | 64 | 56 | 8 | 0 | 0 | 0 | 0.0152813 | 0.0151897 |
| impossible | software | 64 | 0 | 0 | 0 | 0 | 64 | 7.525e-05 | 3.12e-05 |
| impossible | rtl_simulated | 64 | 0 | 0 | 0 | 52 | 64 | 0.0878989 | 2.935e-05 |
| impossible | auto | 64 | 0 | 64 | 0 | 0 | 64 | 0.0150946 | 0.015093 |
| rtl_preferred | software | 64 | 64 | 0 | 0 | 0 | 0 | 6.485e-05 | 3.08e-05 |
| rtl_preferred | rtl_simulated | 64 | 40 | 0 | 0 | 12 | 0 | 0.087113 | 2.49e-05 |
| rtl_preferred | auto | 64 | 56 | 8 | 0 | 0 | 0 | 0.0587285 | 0.0152958 |
| strict | software | 64 | 64 | 0 | 0 | 0 | 0 | 5.64e-05 | 2.675e-05 |
| strict | rtl_simulated | 64 | 0 | 0 | 0 | 52 | 0 | 0.0893727 | 2.425e-05 |
| strict | auto | 64 | 56 | 8 | 0 | 0 | 0 | 0.0155108 | 0.0154583 |
| tight_deadline | software | 64 | 64 | 0 | 0 | 0 | 0 | 7.775e-05 | 3.34e-05 |
| tight_deadline | rtl_simulated | 64 | 0 | 0 | 0 | 12 | 64 | 0.0879945 | 2.965e-05 |
| tight_deadline | auto | 64 | 0 | 64 | 0 | 0 | 64 | 0.0153622 | 0.0153605 |

Comparação pareada posterior à decisão, sem alimentar o seletor:

| scenario | requests | initial_feasible_ex_post | missed_observed_feasible | overhead_seconds_median | oracle_excess_seconds_median |
|---|---|---|---|---|---|
| balanced | 64 | 56 | 8 | 0.0152147 | 0.0152147 |
| impossible | 64 | 0 | 0 | — | — |
| rtl_preferred | 64 | 56 | 8 | 0.0153528 | 0.100105 |
| strict | 64 | 56 | 8 | 0.0154152 | 0.0154152 |
| tight_deadline | 64 | 0 | 64 | — | — |

`oracle` é apenas a melhor alternativa fixa observada no mesmo caso/cenário/
repetição. Não é garantia de melhor latência nem conhecimento disponível ao seletor.
Overhead é a diferença pareada de tempos totais, sujeita à carga e à ordem de execução.

## D — Robustez

| fault | fallback_policy | status | selected_backend | backend | fallback_count | initial_success | detection_ok |
|---|---|---|---|---|---|---|---|
| unavailable_before_selection | software | ok | software | software | 0 | True | True |
| unavailable_before_selection | none | ok | software | software | 0 | True | True |
| unavailable_before_selection | no_alternative | no_feasible_configuration | — | — | 0 | False | True |
| unavailable_after_selection | software | fallback_ok | rtl_simulated | software | 1 | False | True |
| unavailable_after_selection | none | error | rtl_simulated | rtl_simulated | 0 | False | True |
| unavailable_after_selection | no_alternative | error | rtl_simulated | rtl_simulated | 0 | False | True |
| timeout | software | fallback_ok | rtl_simulated | software | 1 | False | True |
| timeout | none | error | rtl_simulated | rtl_simulated | 0 | False | True |
| timeout | no_alternative | error | rtl_simulated | rtl_simulated | 0 | False | True |
| invalid_file | software | fallback_ok | rtl_simulated | software | 1 | False | True |
| invalid_file | none | error | rtl_simulated | rtl_simulated | 0 | False | True |
| invalid_file | no_alternative | error | rtl_simulated | rtl_simulated | 0 | False | True |
| incomplete_output | software | fallback_ok | rtl_simulated | software | 1 | False | True |
| incomplete_output | none | error | rtl_simulated | rtl_simulated | 0 | False | True |
| incomplete_output | no_alternative | error | rtl_simulated | rtl_simulated | 0 | False | True |
| undefined_rtl | software | fallback_ok | rtl_simulated | software | 1 | False | True |
| undefined_rtl | none | error | rtl_simulated | rtl_simulated | 0 | False | True |
| undefined_rtl | no_alternative | error | rtl_simulated | rtl_simulated | 0 | False | True |
| numeric_limit | software | fallback_ok | rtl_simulated | software | 1 | False | True |
| numeric_limit | none | constraint_violation | rtl_simulated | rtl_simulated | 0 | False | True |
| numeric_limit | no_alternative | constraint_violation | rtl_simulated | rtl_simulated | 0 | False | True |

Injeções são segregadas das falhas naturais. Indisponibilidade antes da seleção
deve podar o candidato, sem inventar um fallback. A falha numérica usa F=0,1I,
K=I e limite zero depois de perfis exatos de ±I, demonstrando que um envelope
empírico não prova erro uniforme. U/X é produzido em uma cópia descartável do RTL.

## E — Reprodutibilidade

Regeneração independente do dataset idêntica: True.
Resultados numéricos estáveis entre repetições: True.
Decisões/status/saídas estáveis: 480/480 comparações.
As eventuais diferenças estão em `reproducibility.csv`; tempos de parede não
são exigidos idênticos. Seeds e perfis brutos permanecem disponíveis.

## Interpretação e limites

Este kernel 3×3 tem custo NumPy pequeno frente ao subprocesso GHDL e à seleção.
A escolha por menor tempo pode se reduzir sistematicamente ao software.
Prefira descrever validade, generalização dos perfis, verificação e overhead;
não atribua aceleração física à simulação ou vantagem científica a matrizes de stress.
As imagens pertencem a uma única cena, com K estimada e sem ground truth.
O estudo não demonstra originalidade nem prontidão editorial.

Figuras medidas/derivadas: `figures/numeric_errors.png`, `figures/latency_ecdf.png`
e `figures/policy_success.png`, também em PDF. Tabelas são reproduzidas dos CSVs.
