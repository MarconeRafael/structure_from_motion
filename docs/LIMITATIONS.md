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
- **Plataforma:** a avaliação entregue foi executada no Windows com GHDL portátil.
  Scripts suportam caminhos parametrizados, mas execução Linux/WSL ainda precisa
  ser demonstrada no ambiente correspondente.
- **Literatura:** não há revisão sistemática nem comparação com seletores
  publicados. Originalidade e adequação editorial não foram estabelecidas.

Antes de submissão: ampliar cenas/câmeras e repetições, reproduzir em Linux e em
outro computador, avaliar qualidade geométrica com ground truth, revisar seleção
e co-design existentes e definir uma contribuição sustentada pelos dados. Se o
seletor for trivial, enquadrar como estudo de caso de verificação, validade dos
perfis e custo de integração; não fabricar ganhos de aceleração.
