# Resultados da avaliação — 2026-11-19

Execução principal:
[`20261119T170335054730Z`](../experiments/results/20261119T170335054730Z/RESULTS.md).
O resumo desse diretório foi gerado automaticamente a partir das observações;
CSV/JSON são a fonte dos valores abaixo. Configuração e critérios não foram
alterados depois da avaliação final.

## Escopo e auditoria

Windows, Python 3.11.9, NumPy 2.2.6, OpenCV headless 4.12.0.88, Matplotlib 3.10.7
e GHDL 6.0.0 mcode. A auditoria inicial executou os 55 testes existentes. Com os
seis novos testes de dados/métricas, o comando experimental executou **61 testes,
sem falhas, erros ou testes ignorados**. `pip check` também passou.

Foram usados 59 casos, divididos em 33 de caracterização, 10 de desenvolvimento
e 16 de avaliação. Os splits têm IDs distintos; os pools de correspondências
reais são disjuntos. O caso padrão `strict` foi escolhido no desenvolvimento e
congelado antes dos resultados finais. Todas as cinco configurações previamente
declaradas continuaram na comparação.

Na execução principal, duas repetições independentes produziram **32 comparações
numéricas, 320 medições temporais, 960 requisições de políticas e 21 testes de
falha controlada**. As duas compilações frias ficam registradas separadamente;
todas as 160 tentativas RTL temporais reutilizaram o cache.

## Correção e qualidade

As **32/32 saídas RTL foram bit-exatas** contra o modelo inteiro, com diferença
máxima de zero unidades signed32. Destas, **seis apresentaram overflow**, foram
marcadas inválidas e excluídas das estatísticas de desempenho válido.

| Categoria | Observações | Sem overflow | Com overflow | Maior erro absoluto sem overflow |
|---|---:|---:|---:|---:|
| Controle numérico | 22 | 16 | 6 | 2,69005 × 10⁻⁵ |
| Geometria sintética conhecida | 6 | 6 | 0 | 0,0273545 |
| Imagens do repositório | 4 | 4 | 0 | 3,21034 |

Ausência de overflow não demonstrou qualidade geométrica. No sintético, a
referência NumPy diferiu de `[t]×R` em no máximo 5,56 × 10⁻¹⁷, enquanto o RTL
teve erro relativo de **2,35% a 10,95%** e erro de forma normalizado de
**0,02746 a 0,09702**. Há quantização significativa de F pequena.

No par de imagens foram extraídos 129 inliers pelo pipeline existente. As duas
Fs finais tiveram erro absoluto RTL de 0,720792 e 3,210339; o erro relativo foi
15,13% e 4,85%. O erro de forma foi 0,21402 e 0,09105. São comparações contra
NumPy com a mesma K estimada, sem ground truth de reconstrução real.

## Tempos e overhead

Na população **pareada válida**, com 130 observações de cada backend:

| Backend | Mediana por tentativa | p95 |
|---|---:|---:|
| software | 38,75 µs | 82,72 µs |
| rtl_simulated | 87,8409 ms | 99,3274 ms |

NumPy foi mais rápido em **130/130 pares**, e seu erro contra a referência é
zero por definição do contrato. Assim, o software dominou o RTL simulado em
tempo e erro numérico nas observações comparáveis desta avaliação. Isso não é
uma conclusão sobre FPGA física ou todo o espaço de aplicações SfM.

Os tempos incluem o adaptador e sua validação; o processo GHDL inclui
inicialização/JIT e simulação, que não puderam ser medidos separadamente.
Não são tempos puros de multiplicação nem latência física de hardware.

No cenário `balanced`, a mediana do tempo total foi **56,40 µs** para software
fixo, **88,7511 ms** para RTL fixo e **15,2813 ms** para auto. A diferença pareada
auto menos a política fixa selecionada teve mediana de **15,2147 ms**. As consultas
de versão e assinaturas participam desse overhead. O gerenciador não superou
software fixo nesta avaliação.

## Decisões e restrições

Cada célula abaixo contém sucessos sobre 64 requisições do cenário, incluindo
ambas as repetições experimentais e duas repetições de cada um dos 16 casos.

| Cenário | Software fixo | RTL fixo | Auto |
|---|---:|---:|---:|
| strict: erro ≤ 1e-6 | 64/64 | 0/64 | 56/64 |
| balanced: erro ≤ 0,01 | 64/64 | 40/64 | 56/64 |
| rtl_preferred: erro ≤ 0,01 | 64/64 | 40/64 | 56/64 |
| tight_deadline: erro ≤ 0,01, tempo ≤ 5 ms | 64/64 | 0/64 | 0/64 |
| impossible: tempo ≤ 0 | 0/64 | 0/64 | 0/64 |

Nos três cenários sem orçamento temporal, auto fez 56 escolhas viáveis segundo
os baselines posteriores e recusou oito casos por falta de perfil compatível,
apesar de software fixo funcionar. As recusas correspondem a um caso de stress
de acumulador e um caso real fora dos envelopes de treino. A cobertura foi
87,5%, não 100%; perfis conservadores também perdem oportunidades viáveis.

Em `rtl_preferred`, auto escolheu RTL em 32 requisições, software em 24 e nenhuma
opção em oito. Isso demonstra a preferência quando viável, sem benefício de
tempo. No orçamento de 5 ms, a própria decisão custou mais que o limite e auto
recusou os 64 casos, enquanto software fixo atendeu todos.

Não houve fallback natural nas observações finais. Isso não demonstra ausência
de falhas possíveis; os testes deliberados ficam separados.

## Robustez e repetibilidade

Os **21/21 casos de falha controlada foram detectados conforme o critério**.
Ferramenta ausente antes da seleção podou o candidato; falhas posteriores
preservaram o backend originalmente escolhido. Fallback permitido recuperou
os seis tipos de falha após seleção; desativá-lo ou remover a alternativa
preservou o erro. Sucesso de recuperação não foi contado como acerto inicial.

Entre as duas repetições, foram idênticos os **16/16 resultados numéricos** e as
**480/480 combinações de decisão/status/saída comparáveis**. O dataset regenerado
com a mesma semente teve o mesmo hash. Tempos de parede variaram e não foram
forçados a coincidir.

Uma nova instalação em `build/clean_experiments_env`, usando integralmente o
`requirements-lock.txt` da execução principal, repetiu o comando experimental:
[`clean_install/20261119T170758989402Z`](../experiments/results/clean_install/20261119T170758989402Z/RESULTS.md).
Também executou 61 testes sem falhas/ignorados. O dataset e o lock foram idênticos;
**32/32 resultados numéricos e 960/960 combinações de decisão/status/saída**
coincidiram com a execução principal. As medianas pareadas foram 39,15 µs e
86,1862 ms, ilustrando a variação de parede. As duas execuções não foram agrupadas
para escolher o resultado mais favorável.

A [verificação cruzada](../experiments/results/20261119T170335054730Z/clean_install_comparison.json)
também confirmou contagens de CSV, hashes das fontes/dataset, todas as matrizes
inteiras recalculadas e todas as tabelas recomputadas diretamente dos JSONs brutos.

## Artefatos e interpretação

- [CSV numérico](../experiments/results/20261119T170335054730Z/numeric.csv),
  [tempos](../experiments/results/20261119T170335054730Z/timing.csv),
  [políticas](../experiments/results/20261119T170335054730Z/policies.csv) e
  [falhas](../experiments/results/20261119T170335054730Z/faults.csv).
- [JSON bruto](../experiments/results/20261119T170335054730Z/raw.jsonl),
  [metadados](../experiments/results/20261119T170335054730Z/metadata.json) e
  [tabelas agregadas](../experiments/results/20261119T170335054730Z/summary.json).
- [Erros numéricos](../experiments/results/20261119T170335054730Z/figures/numeric_errors.png),
  [ECDF de latência](../experiments/results/20261119T170335054730Z/figures/latency_ecdf.png) e
  [sucesso por política](../experiments/results/20261119T170335054730Z/figures/policy_success.png), também em PDF.

As figuras foram inspecionadas visualmente. Uma correção de limite não negativo
dos eixos de erro foi aplicada somente à apresentação, regenerando as figuras
dos mesmos registros. Metadados preservam hashes das fontes originais, snapshot
e identificação do pós-processamento; os dados medidos não foram alterados.

O enquadramento sustentado é um estudo de caso de **verificação numérica,
limitações de perfis e overhead de integração**. A política é simples, o software
foi dominante e não há evidência bibliográfica de originalidade. Veja
[LIMITATIONS.md](LIMITATIONS.md) e [PAPER_OUTLINE.md](PAPER_OUTLINE.md) antes de
formular alegações editoriais.
