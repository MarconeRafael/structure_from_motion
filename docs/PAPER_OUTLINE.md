# Estrutura proposta para artigo — ainda não pronto para submissão

**Constraint-Based Execution Selection for a Structure-from-Motion Geometry Kernel:
A Python–VHDL Simulation Study**

1. **Introdução.** Pergunta sobre viabilidade de seleção, validade numérica e
   overhead. Delimitar operação 3×3 e simulação, sem promessa de aceleração física.
2. **Trabalhos relacionados.** Revisar co-design hardware/software, seleção por
   restrições, contratos numéricos de ponto fixo, verificação RTL e kernels SfM.
   Esta seção está pendente: não há referências inventadas nem alegação de lacuna
   antes de pesquisar e comparar métodos publicados.
3. **Arquitetura.** Python → arquivos signed32 → testbench → GHDL → Python.
   NumPy float64, modelo inteiro independente e RTL; handshake e validação.
4. **Política de seleção.** Perfis anteriores, limites rígidos, preferências,
   inviabilidade e fallback rastreável. Explicar por que dois candidatos não
   justificam um otimizador sofisticado e quando a seleção se reduz ao software.
5. **Metodologia experimental.** Configuração congelada; 33/10/16 casos para
   treino/desenvolvimento/avaliação; dados controlados, geometria conhecida e
   imagens reais; medidas de parede e qualidade; baseline fixo e comparação ex post.
6. **Resultados.** Usar exclusivamente CSV/JSON e figuras da execução identificada
   em `RESULTS.md`. Mostrar equivalência inteira, overflow/quantização, percentis,
   sucessos/violações, overhead e falhas. Não omitir cenários inviáveis.
7. **Discussão.** Se NumPy dominar, declarar a dominância observada sob este
   contrato e ambiente. Investigar validade do RTL apesar do custo, limites de
   generalização dos perfis e custo da verificação; não fabricar vantagem da política.
8. **Ameaças à validade.** Uma cena, K estimada, amostras pequenas, caudas não
   caracterizadas, software como referência, cache/carga e ausência de FPGA.
9. **Conclusão.** Responder somente à pergunta avaliada. Separar resultados
   reproduzidos de hipótese futura e explicitar pendências.

## Potencial de contribuição e pendências

O artefato pode sustentar um estudo de caso de integração/verificação numérica e
avaliação negativa de seleção em um kernel pequeno. A política por si só é simples
e sua originalidade não foi estabelecida. Resultados em matrizes artificiais não
provam utilidade no SfM real. Não há evidência de ineditismo ou publicabilidade.

Antes da submissão são necessários: revisão bibliográfica real, comparação com
alternativas publicadas, mais cenas com calibração/ground truth, repetições em
outras plataformas, avaliação geométrica além de E e definição da contribuição
apoiada por esses resultados. Os testes passarem não resolve essas pendências.
