# Etapa 4. Auditoria, cache de assinaturas e cobertura

A [Etapa 3](RESULTS.md) conserva seus valores, dados brutos e figuras. A
comparação pareada desta etapa executou o gerenciador original a partir do
snapshot arquivado, em uma nova sessão com o gerenciador otimizado. A verificação
antes e depois da sessão confirmou os mesmos hashes para os 95 arquivos históricos.

## Reprodução

```bash
python -m pip install -r requirements-experiments.txt
REQUIRE_GHDL=1 REQUIRE_OPENCV=1 python -m unittest discover -s tests -v
python -m experiments.stage4 --config experiments/stage4_config.json
```

GHDL deve estar no PATH ou ser indicado por `GHDL` ou `--ghdl`. Cada execução
usa um diretório novo em `experiments/stage4_results/` e um cache de compilação
próprio. A configuração rejeita diretórios de saída dentro do histórico. O
executor verifica os hashes do dataset, da configuração e do snapshot da Etapa 3,
recalcula suas tabelas e registra os hashes de todos os arquivos históricos.
Checkouts com finais de linha diferentes podem validar o snapshot por conversão
CRLF/LF em memória.

Os testes passaram no Windows com Python 3.11.9 e GHDL 6.0.0 mcode e no WSL
Ubuntu 22.04 com Python 3.10.12 e GHDL 1.0.0 mcode. No WSL, os pacotes GHDL
e libgnat da distribuição foram extraídos no diretório `build/stage4-linux`,
com bibliotecas e dependências Python locais. A configuração
[Linux tests](../.github/workflows/linux-tests.yml) instala as ferramentas no
runner Ubuntu e rejeita skips. A execução remota desse workflow está pendente.
[Log Windows](../experiments/stage4_results/20261119T175029183225Z/windows_tests.txt) ·
[Log WSL](../experiments/stage4_results/20261119T175029183225Z/wsl_tests.txt).
Ambos os experimentos usaram NumPy 2.2.6, OpenCV 4.12.0.88 e Matplotlib 3.10.7.
As dependências foram registradas em
[lock Windows](../experiments/stage4_results/20261119T175029183225Z/requirements-lock.txt)
e [lock WSL](../experiments/stage4_results/20261119T175314057268Z/requirements-lock.txt).

## Auditoria e desenho da comparação

Os brutos arquivados reproduzem as tabelas publicadas na Etapa 3. Os 59 pares
F/K são distintos e os IDs de correspondências reais são disjuntos entre os
três splits. O filtro RANSAC do par completo é compartilhado e a cena permanece
a mesma. O hash do snapshot corresponde ao manifesto histórico. Antes da
Etapa 4, a única diferença em relação às fontes de medição arquivadas era
a correção já registrada no limite inferior dos eixos das figuras de erro.
O subprocesso GHDL continua a reunir inicialização e simulação em uma medida.

Os 33 casos de caracterização originais geraram novas observações em cada
plataforma. Os dois gerenciadores receberam as mesmas amostras, com suas
respectivas assinaturas. A troca de assinatura foi feita em uma cópia dos
perfis, após verificar que os backends e o RTL correspondem ao snapshot. O
primeiro caso de desenvolvimento aqueceu o cache de assinaturas. Os 16 casos
finais foram executados quatro vezes nos cinco cenários preexistentes, com
ordem de casos e variantes determinada por semente. Cada cenário tem 64
requisições por variante. Os baselines fixos executam sob os mesmos limites.
Medições de Windows e WSL são populações distintas.

A assinatura fica em memória por instância. Cada consulta resolve o executável
e verifica metadados das fontes e da ferramenta, além da configuração e das
variáveis relevantes de resolução. Uma mudança invalida o cache e recalcula
versão e hashes. A assinatura RTL inclui SHA-256 do executável, inclusive para
substituição que mantenha a mesma versão. O projeto pressupõe atualizações
normais de arquivos, cujos metadados mudam. Bibliotecas compartilhadas não são
individualmente verificadas. Crie uma instância e caracterize novamente após
mudança do ambiente do simulador. Perfis anteriores ao formato de assinatura
atual precisam de nova caracterização para uso operacional.

## Windows. Overhead e cobertura

| Cenário balanceado, 64 requisições por variante | Decisão mediana | p95 da decisão | Tempo total mediano | Overhead pareado sobre software | Válidos |
|---|---:|---:|---:|---:|---:|
| Software fixo | 0,022 ms | 0,034 ms | 0,049 ms | 0 | 64/64 |
| RTL fixo | 0,021 ms | 0,033 ms | 90,339 ms | 90,292 ms | 40/64 |
| Gerenciador original | 15,679 ms | 17,928 ms | 15,739 ms | 15,667 ms | 56/64 |
| Gerenciador otimizado | 1,402 ms | 2,017 ms | 1,443 ms | 1,376 ms | 56/64 |
| Otimizado com software verificado | 1,407 ms | 1,883 ms | 1,466 ms | 1,394 ms | 64/64 |

A decisão mediana caiu 91,1%. A assinatura consumiu 15,384 ms no original
e 1,162 ms no otimizado. No otimizado, consulta e compatibilidade de perfis
tiveram mediana de 0,128 ms, filtragem 0,075 ms e ordenação 0,003 ms. As medianas
dos componentes são marginais. A construção do gerenciador, que inclui a
validação inicial dos perfis, custou 1,02 ms no original e 1,17 ms no otimizado.
A primeira decisão do
otimizado custou 60,97 ms com zero acertos de cache. A redução vale para
solicitações sucessivas. O NumPy fixo continuou com o menor tempo.

| Cenário | Original | Otimizado | Otimizado com software verificado | Software fixo |
|---|---:|---:|---:|---:|
| Estrito | 56/64 | 56/64 | 64/64 | 64/64 |
| Balanceado | 56/64 | 56/64 | 64/64 | 64/64 |
| Preferência RTL | 56/64 | 56/64 | 64/64 | 64/64 |
| Prazo de 5 ms | 0/64 | 56/64 | 64/64 | 64/64 |
| Prazo zero | 0/64 | 0/64 | 0/64 | 0/64 |

Sem prazo, as decisões iniciais do original e do otimizado coincidiram. No
balanceado, as oito falsas recusas correspondem a duas entradas fora do
envelope, repetidas quatro vezes. Entre os candidatos RTL, oito foram excluídos
por domínio, oito por falhas observadas e 16 por erro previsto. No prazo de
5 ms, o RTL perdeu também 32 candidaturas pelo limite temporal. A ferramenta
estava disponível nas medições pareadas. O teste de retirada do executável
comprova invalidação e indisponibilidade separadamente.
As classes RTL com falha na caracterização tiveram 8/8 falhas
(`overflow32`) e 2/2 (`accumulator64`). As outras seis tiveram zero.
Logo, a perda observada por falha no treino não pôde ser atribuída a um
perfil que agregasse sucessos e falhas.

Em cada cenário com resgate, oito tentativas de software sem perfil foram
validadas após execução. Os registros preservam `selected_backend=null`, a
ausência de garantia prévia e o custo da tentativa. A execução só começa
quando ainda há orçamento e passa pelos limites de erro e tempo observados.
`initial_selection_success` permanece falso. A opção de CLI é
`--verify-unprofiled-software`. A política conservadora continua como padrão.
Não houve falsa aceitação nas variantes gerenciadas do Windows nesta amostra.
O indicador de falsa aceitação corresponde a uma escolha inicial que falhou
na execução ou validação. Nos baselines fixos, a mesma coluna conta tentativas
fixas reprovadas.

A caracterização já separava famílias. Com dois casos finais fora dos envelopes
e um deles em uma família com apenas um caso de treino, subdividir a amostra
reduziria a sustentação empírica. A alternativa de cobertura avaliada foi a
tentativa explícita de software sujeita a validação.

## Geometria sintética adicional

Três sementes derivadas produziram 108 entradas por split e 324 no conjunto
separado. O conjunto final contém 27 poses, com quatro escalas de F por pose.
As focais foram 220, 525 e 1100 pixels, as amplitudes de translação 0,05, 0,2
e 0,5 e o ruído gaussiano de imagem 0, 0,5 e 1,5 pixel. Cada cena tem 48 pontos,
com profundidade mínima final de 3,95 nas duas câmeras. O maior resíduo
epipolar limpo foi 2,22 × 10⁻¹⁶ na escala original. Com ruído, a F foi
estimada pelo método de oito pontos e alinhada em norma e sinal à referência
antes de aplicar os mesmos fatores de escala. A referência E teórica é
`[t]×R` com o mesmo fator de escala.

| Multiplicador de F | Bit-exatos | Overflow | Distorção entre os sem overflow | E nula entre os sem overflow |
|---|---:|---:|---:|---:|
| 0,01 | 27/27 | 0 | 27 | 11 |
| 1 | 27/27 | 0 | 26 | 0 |
| 100 | 27/27 | 0 | 18 | 0 |
| 100.000 | 27/27 | 8 | 0 | 0 |

Distorção usa a distância de Frobenius entre matrizes normalizadas, mínima
entre os dois sinais. O limiar descritivo de 0,1 foi definido na configuração
antes da avaliação, e os casos de forma indefinida por E nula contam como
distorção. Esse limiar não foi calibrado para pose. A escala maior reduziu
a perda por quantização entre as saídas restantes e introduziu overflow.
Na escala 1, as medianas float64 contra E teórica foram próximas de zero,
0,302 e 0,568 para os três níveis de ruído. A avaliação mede E e distingue
a contribuição do estimador e a distância introduzida pelo cálculo em ponto fixo.
As quatro escalas compartilham cada cena. Cenas são amostradas novamente entre
níveis de ruído, então a comparação entre níveis é descritiva e não pareada.

## Repetição no WSL

O experimento completo também passou no WSL com GHDL 1.0.0, executando o
repositório na montagem `/mnt/c`. Cada variante produziu 64 requisições
por cenário. No balanceado, a decisão mediana foi 151,905 ms no original e
30,724 ms no otimizado. O overhead pareado sobre software fixo caiu de
151,921 ms para 30,751 ms. A cobertura foi 56/64 em ambos e 64/64 com oito
tentativas de software verificadas. A decisão continuou acima dos 5 ms no
cenário com prazo, e as três variantes gerenciadas tiveram 0/64 sucessos
enquanto software fixo teve 64/64.

As 108 matrizes inteiras de saída coincidiram componente a componente entre
Windows e WSL. As duas execuções também produziram as mesmas contagens de
overflow e distorção por escala. A comparação entre plataformas valida o
fluxo e a aritmética testada. Seus tempos refletem versões distintas e o
sistema de arquivos montado, sem controle para isolar cada fator.
[Tabela WSL](../experiments/stage4_results/20261119T175314057268Z/table_policies.csv) ·
[JSON bruto WSL](../experiments/stage4_results/20261119T175314057268Z/paired_raw.json) ·
[Metadados WSL](../experiments/stage4_results/20261119T175314057268Z/metadata.json).

## Dados e limites

- [Observações pareadas em CSV](../experiments/stage4_results/20261119T175029183225Z/paired.csv) ·
  [Brutos em JSON](../experiments/stage4_results/20261119T175029183225Z/paired_raw.json) ·
  [Metadados e hashes](../experiments/stage4_results/20261119T175029183225Z/metadata.json).
- [Tabelas e percentis](../experiments/stage4_results/20261119T175029183225Z/summary.json) ·
  [Exclusões](../experiments/stage4_results/20261119T175029183225Z/table_candidate_exclusions.csv) ·
  [Geometria](../experiments/stage4_results/20261119T175029183225Z/geometry.csv).
- [Gráfico de decisão e cobertura](../experiments/stage4_results/20261119T175029183225Z/manager_comparison.pdf) ·
  [Gráfico de escala e overflow](../experiments/stage4_results/20261119T175029183225Z/geometry_scale.pdf).

As medições abrangem dois simuladores mcode e um computador. São necessários
mais computadores, cenas independentes e calibração real antes de generalizar
tempo ou qualidade. O estudo não inclui latência física de FPGA, energia ou
qualidade de reconstrução 3D. O [manuscrito](PAPER_DRAFT.md) registra as
conclusões observadas e a [revisão](RELATED_WORK.md) delimita a contribuição.
