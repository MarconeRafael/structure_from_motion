# Trabalhos relacionados

Revisão direcionada em 19 de novembro de 2026. As fontes incluem artigos, versões
depositadas pelos autores e registros institucionais. A busca cobriu escalonamento
heterogêneo, offload sob restrições, verificação RTL em Python, ponto fixo e geometria
epipolar. A abrangência é limitada a uma seleção de trabalhos pertinentes.

**Perfis e custo de escalonamento.** Cédric Augonnet, Samuel Thibault, Raymond
Namyst e Pierre-André Wacrenier. “StarPU: A Unified Platform for Task Scheduling
on Heterogeneous Multicore Architectures.” *Concurrency and Computation: Practice
and Experience*, 23(2), 187–198, 2011. O sistema usa modelos de desempenho para
distribuir tarefas em plataformas heterogêneas e discute o overhead de execução
de uma tarefa no runtime. Isso estabelece precedentes para perfis e medição
do overhead. Aqui a unidade de avaliação é uma chamada para um único kernel,
com restrição explícita de erro e verificação da identidade do backend.
[DOI 10.1002/cpe.1631](https://doi.org/10.1002/cpe.1631) ·
[Artigo](https://people.bordeaux.inria.fr/gaupy/ressources/teachings/2021/algo_hpc/articles-2021/starpu.pdf).

**Offload sob restrições.** Eduardo Cuervo, Aruna Balasubramanian, Dae-ki Cho,
Alec Wolman, Stefan Saroiu, Ranveer Chandra e Paramvir Bahl. “MAUI: Making
Smartphones Last Longer with Code Offload.” *ACM MobiSys*, 49–62, 2010.
MAUI usa perfis de métodos, condições da rede e otimização em tempo de execução
para decidir quais métodos executar remotamente. Os autores relatam economias
energéticas em aplicações móveis avaliadas. O presente estudo mede tempo
e qualidade numérica de duas implementações locais, com uma política de dois
candidatos. A seleção por restrições já é estabelecida.
[DOI 10.1145/1814433.1814441](https://doi.org/10.1145/1814433.1814441) ·
[Artigo](https://www.microsoft.com/en-us/research/wp-content/uploads/2010/06/maui.pdf).

**Testes RTL em Python.** Benjamin John Rosser. “Verification of Readout
Electronics in the ATLAS ITk Strips Detector.” *APS DPF 2019*, 2019,
arXiv:1910.06694. O autor relata o uso de cocotb para simular eletrônica de
leitura e encontrar problemas durante o desenvolvimento. O uso de Python para
testar RTL tem precedente direto. A comparação local usa TextIO e dois modelos
para distinguir divergência de implementação de perda por quantização.
[DOI do depósito 10.48550/arXiv.1910.06694](https://doi.org/10.48550/arXiv.1910.06694) ·
[Texto no CERN](https://cds.cern.ch/record/2697349/files/1910.06694.pdf).

**Limites numéricos e escolha de precisão.** Eva Darulova e Viktor Kuncak.
“Towards a Compiler for Reals.” *ACM Transactions on Programming Languages and
Systems*, 39(2), artigo 8, 2017. Rosa usa análise de erro para compilar programas
com especificações sobre reais para aritmética de precisão finita, incluindo
ponto fixo. A abordagem oferece limites fundamentados em análise para as
condições especificadas. O estudo atual mede o comportamento de um formato
Q15.16 fixo e testa a cobertura empírica dos perfis, que só fornece observações
dos casos ensaiados.
[DOI 10.1145/3014426](https://doi.org/10.1145/3014426) ·
[Versão dos autores](https://lara.epfl.ch/~kuncak/papers/DarulovaKuncak17RealsTOPLAS.pdf).

**Condicionamento da geometria epipolar.** Richard I. Hartley. “In Defense of
the Eight-Point Algorithm.” *IEEE Transactions on Pattern Analysis and Machine
Intelligence*, 19(6), 580–593, 1997. A normalização das coordenadas melhora o
condicionamento do sistema linear e a estabilidade da estimação de F em imagens
reais. O experimento atual distingue o erro do estimador com correspondências
ruidosas do erro de conversão e cálculo em Q15.16 após a estimação. Multiplicar
F por um escalar neste experimento é distinto de normalizar coordenadas antes
da estimação.
[DOI 10.1109/34.601246](https://doi.org/10.1109/34.601246) ·
[Artigo](https://mil.ufl.edu/nechyba/www/eel6562/course_materials/t9.3d_vision/hartley1997.pdf).

**SfM em FPGA.** Mateusz Komorkiewicz, Tomasz Kryjak, Katarzyna
Chuchacz-Kowalczyk, Paweł Skruch e Marek Gorgoń. “FPGA Based System for Real-Time
Structure from Motion Computation.” *DASIP*, 1–7, 2015. Os autores descrevem
um SoC com FPGA e ARM que processa extração e casamento de características,
matriz fundamental, projeção e triangulação. A exploração de projeto identifica
compromissos entre recursos, frequência e precisão. Este repositório fornece
uma avaliação pareada de seleção e verificação de E sobre RTL simulado, em
um escopo de software e simulação.
[DOI 10.1109/DASIP.2015.7367241](https://doi.org/10.1109/DASIP.2015.7367241) ·
[Registro e resumo institucional](https://badap.agh.edu.pl/publikacja/93233).

O conjunto revisado sustenta um estudo de caso sobre o custo de verificar
identidade, a cobertura de perfis empíricos e a distorção de E com quantização.
Uma revisão mais abrangente e comparações com outros contratos numéricos
são necessárias para delimitar a contribuição frente à literatura.
