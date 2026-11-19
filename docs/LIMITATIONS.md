# Limitações e ameaças à validade

- **Simulação:** não há FPGA, síntese mapeada, energia, LUT/DSP/BRAM ou frequência
  medidos. Tempo de subprocesso e ciclos lógicos não são latência física.
- **Kernel pequeno:** multiplicação 3×3 e dois backends tornam a preferência por
  menor tempo potencialmente trivial. Overhead e resultados negativos devem ser
  preservados, sem apresentar a política como avanço multiobjetivo por si só.
- **Contrato NumPy:** erro do software contra a própria referência é zero por
  definição. Não é uma prova de geometria ou aritmética real exata. A referência
  independente só existe nos cenários sintéticos com pose conhecida.
- **Q15.16:** overflow e quantização de F pequena são limitações estruturais.
  Equivalência bit a bit não prova correção matemática. O gerenciador não altera
  a escala para favorecer o RTL; erro absoluto depende da escala original.
- **Perfis empíricos:** caixas por componente não garantem qualidade em todos os
  pontos internos. Não se extrapola além delas. Perfis com qualquer falha são
  excluídos, o que pode ser excessivamente conservador em classes heterogêneas.
- **Cobertura:** apenas 59 casos, 16 finais e duas repetições do mesmo conjunto.
  Percentis empíricos não sustentam garantias de cauda ou prazo de tempo real.
- **Imagens:** um único par, cena possivelmente planar, K estimada e sem ground
  truth. O filtro RANSAC compartilha o par inteiro antes de dividir os matches;
  os splits têm IDs disjuntos mas não representam novas cenas independentes.
- **Medições:** carga do sistema, caches, criação de processos e temporização
  afetam parede. A consulta de assinaturas/GHDL participa do overhead. Inicialização
  e execução interna do simulador não foram isoladas; permanecem não medidas.
- **Oráculo ex post:** compara execuções fixas observadas separadamente, não o
  contrafactual exato da mesma execução. É um comparador descritivo, não um ótimo
  provado nem informação disponível ao gerenciador.
- **Fallback:** injeções verificam o mecanismo; não estimam probabilidade de
  falhas naturais. Um fallback válido mantém a falha da seleção inicial.
- **Pipeline:** os placeholders e defeitos do `SfM_Top` continuam abertos. O
  estudo avalia somente E; não demonstra reconstrução integral em RTL.
- **Plataforma:** a avaliação histórica ocorreu no Windows. A Etapa 4 executou a
  suíte e a comparação pareada no Windows e no WSL Ubuntu 22.04, em um mesmo
  computador. O WSL usou `/mnt/c` e outra versão do GHDL. Os tempos não foram
  combinados. O workflow remoto continua pendente. [Validação e medições novas](STAGE4.md).
- **Literatura:** não há revisão sistemática nem comparação com seletores
  publicados. Originalidade e adequação editorial não foram estabelecidas.

O estudo adicional ampliou a geometria conhecida em 108 entradas finais
sintéticas. O limiar de erro de forma ainda precisa ser relacionado à
qualidade de pose ou reconstrução. A revisão [direcionada](RELATED_WORK.md)
fornece antecedentes para avaliar a contribuição e tem escopo limitado.

Antes da submissão, ampliar cenas reais calibradas e repetições, reproduzir
em outro computador, avaliar pose com ground truth e ampliar a comparação
bibliográfica. O enquadramento do [manuscrito](PAPER_DRAFT.md) é um estudo de
caso sobre verificação, validade dos perfis e custo de integração.
