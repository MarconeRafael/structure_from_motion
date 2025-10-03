# Structure from Motion (SfM) em VHDL

Este projeto implementa um pipeline completo de Structure from Motion (SfM) em VHDL para aceleração em hardware (FPGA). O sistema processa correspondências de pontos entre duas imagens para reconstruir a geometria 3D da cena e a pose da câmera, usando dados reais extraídos de imagens.

## 🎯 Características Principais

- **🔧 Pipeline 100% Hardware**: Implementação VHDL completa para FPGA
- **📊 Aritmética de Ponto Fixo**: Formato Q15.16 (32 bits) otimizado
- **🧩 Arquitetura Modular**: Componentes independentes e reutilizáveis  
- **✅ Totalmente Testado**: Validação com GHDL usando dados reais
- **📈 Visualização Python**: Interface para análise de resultados

## 📁 Estrutura do Projeto

```
structure_from_motion/
├── src/                          # Módulos VHDL principais
│   ├── fixed_pkg.vhd            # Tipos de dados Q15.16
│   ├── algebra_pkg.vhd          # Declarações de álgebra linear
│   ├── algebra_pkg_body.vhd     # Implementações de álgebra linear
│   ├── fundamental_matrix.vhd   # Algoritmo 8-pontos
│   ├── essential_matrix.vhd     # Matriz essencial calibrada
│   ├── pose_extraction.vhd      # Extração de pose da câmera
│   ├── triangulation.vhd        # Reconstrução 3D
│   ├── projective_pkg.vhd       # Utilitários de geometria projetiva
│   └── top.vhd                  # Pipeline integrado
├── tb/                          # Testbenches
│   ├── tb_fundamental.vhd       # Teste matriz fundamental
│   └── tb_top.vhd              # Teste pipeline completo
├── images/                      # Imagens de teste reais
│   ├── img1.jpeg               # Imagem de referência (640x480)
│   └── img2.jpeg               # Imagem correspondente (640x480)
├── extract_points.py           # Extração SIFT de pontos reais
├── visualize_vhdl_results.py   # Visualização dos resultados
├── generate_test_data.py       # Gerador de dados simulados
├── Epipolar_Geometry.ipynb     # Referência Python/OpenCV
├── run.sh                      # Script de compilação GHDL
├── SfM.txt                     # Documentação do algoritmo
├── wave.vcd                    # Resultados da simulação
├── vhdl_sfm_results.png        # Linhas epipolares visualizadas
├── vhdl_3d_reconstruction.png  # Reconstrução 3D
└── vhdl_points_data.txt        # Pontos processados em VHDL
```

## 🔧 Módulos VHDL Implementados

### 📦 Pacotes Base
- **`fixed_pkg.vhd`**: Tipos de dados Q15.16 (1 sinal + 15 int + 16 frac)
- **`algebra_pkg`**: Multiplicação de matrizes, produto vetorial, normalização

### 🚀 Pipeline de Processamento
1. **`fundamental_matrix.vhd`**: Algoritmo dos 8 pontos com imposição rank-2
2. **`essential_matrix.vhd`**: Cálculo E = K^T × F × K  
3. **`pose_extraction.vhd`**: Decomposição SVD → (R, t)
4. **`triangulation.vhd`**: Método DLT para reconstrução 3D
5. **`top.vhd`**: Orquestração completa do pipeline

## ⚡ Como Usar

### 📋 Pré-requisitos
```bash
# Simulador VHDL
sudo apt install ghdl

# Python com dependências
pip install opencv-python numpy matplotlib
```

### 🔨 Compilação e Simulação
```bash
# Executar pipeline VHDL completo
./run.sh

# Visualizar resultados processados em VHDL
python3 visualize_vhdl_results.py

# Extrair novos pontos de imagens (opcional)
python3 extract_points.py
```

### 📊 Resultados Gerados
- **`wave.vcd`**: Sinais temporais para análise com GTKWave
- **`vhdl_sfm_results.png`**: Imagens com linhas epipolares
- **`vhdl_3d_reconstruction.png`**: Nuvem de pontos 3D

## � Tutorial de Uso Completo

### 🎯 **Cenário 1: Teste Rápido (Dados Existentes)**

Execute o pipeline completo com as imagens já incluídas:

```bash
# 1. Compilar e simular o VHDL
./run.sh

# 2. Visualizar resultados
python3 visualize_vhdl_results.py
```

**Saída esperada:**
```
Compilando pacotes base...
Compilando módulos principais...
Compilando testbench...
Elaborando design...
Executando simulação...
tb/tb_top.vhd:142:9:@1455ns:(report note): Teste SfM completo executado com sucesso!
tb/tb_top.vhd:143:9:@1455ns:(report note): Pipeline executado: Fundamental -> Essential -> Pose -> Triangulation
Simulação concluída. Arquivo wave.vcd gerado.
```

### 🔄 **Cenário 2: Teste com Novas Imagens**

Para usar suas próprias imagens:

```bash
# 1. Substitua as imagens (formato JPEG, recomendado 640x480)
cp sua_imagem1.jpg images/img1.jpeg
cp sua_imagem2.jpg images/img2.jpeg

# 2. Extrair novos pontos correspondentes
python3 extract_points.py

# 3. Atualizar testbench (copiar do arquivo gerado)
# O script gera vhdl_points_data.txt - copie o conteúdo para tb/tb_top.vhd

# 4. Executar simulação
./run.sh

# 5. Visualizar resultados
python3 visualize_vhdl_results.py
```

### 🔧 **Cenário 3: Desenvolvimento e Debug**

Para desenvolvedores que querem modificar o código:

```bash
# 1. Compilar apenas um módulo específico
ghdl -a --workdir=work src/fundamental_matrix.vhd

# 2. Testar módulo isolado
ghdl -a --workdir=work tb/tb_fundamental.vhd
ghdl -e --workdir=work tb_fundamental  
ghdl -r --workdir=work tb_fundamental --vcd=fundamental.vcd

# 3. Analisar sinais com GTKWave
gtkwave wave.vcd

# 4. Limpar arquivos de compilação
rm -rf work/ *.o tb_top e~*
```

### 📊 **Cenário 4: Análise Detalhada**

Para análise aprofundada dos resultados:

```bash
# 1. Executar com tempo de simulação estendido
ghdl -r --workdir=work tb_top --vcd=wave.vcd --stop-time=50us

# 2. Gerar dados para análise Python
python3 extract_points.py
python3 generate_test_data.py

# 3. Comparar resultados VHDL vs OpenCV
python3 -c "
import numpy as np
# Carregar dados VHDL
vhdl_data = np.loadtxt('vhdl_points_data.txt')
print('Análise de precisão VHDL vs Python...')
"

# 4. Verificar recursos utilizados
echo 'Estimando recursos FPGA...'
grep -r 'signal.*:' src/ | wc -l  # Sinais internos
grep -r 'process' src/ | wc -l    # Processos
```

### 🐛 **Cenário 5: Troubleshooting**

Resolução de problemas comuns:

```bash
# Problema: Erro de compilação VHDL
# Solução:
ghdl --clean
rm -rf work/
mkdir work
./run.sh

# Problema: Python não encontra OpenCV
# Solução:
pip3 install --user opencv-python numpy matplotlib

# Problema: Imagens não carregam
# Solução:
file images/*.jpeg  # Verificar se são JPEGs válidos
ls -la images/      # Verificar permissões

# Problema: Resultados inconsistentes  
# Solução:
python3 extract_points.py  # Re-extrair pontos
./run.sh                   # Re-simular
python3 visualize_vhdl_results.py  # Re-visualizar
```

### 📈 **Verificação de Resultados**

Como validar se tudo está funcionando:

```bash
# 1. Verificar arquivos gerados
ls -la *.vcd *.png *.txt

# 2. Confirmar simulação bem-sucedida
grep "sucesso" <(./run.sh 2>&1)

# 3. Validar pontos extraídos
python3 -c "
import cv2
img = cv2.imread('images/img1.jpeg')
print(f'Imagem carregada: {img.shape if img is not None else \"ERRO\"}')
"

# 4. Verificar consistência dos dados
wc -l vhdl_points_data.txt  # Deve ter ~35 linhas (8 pontos + comentários)
```

### 🎮 **Comandos Úteis de Teste**

```bash
# Teste completo automatizado
./run.sh && python3 visualize_vhdl_results.py && echo "✅ Tudo OK!"

# Benchmark de tempo
time ./run.sh

# Verificar saúde do projeto
find . -name "*.vhd" -exec ghdl -s {} \; 2>&1 | grep -i error

# Estatísticas do código
echo "Linhas de VHDL: $(find src/ -name "*.vhd" -exec wc -l {} + | tail -1)"
echo "Linhas de Python: $(find . -name "*.py" -exec wc -l {} + | tail -1)"
```

## �🔍 Especificações Técnicas

### 💾 Formato de Dados
- **Q15.16**: 32 bits de ponto fixo
  - Range: -32,768 a +32,767.99998
  - Precisão: ~0.000015 (2^-16)
  - Otimizado para coordenadas de imagem

### 📏 Capacidades
- **Pontos**: Até 100 correspondências simultâneas
- **Imagens**: Suporte para alta resolução
- **Latência**: Pipeline determinística
- **Throughput**: Processamento contínuo

### 🖥️ Recursos de Hardware (Estimativa)
- **LUTs**: ~6,000-8,000
- **DSPs**: ~25-35 multiplicadores  
- **BRAM**: ~12-18 blocos
- **Freq. Max**: 100-200 MHz

## 🎨 Arquitetura do Sistema

```
Imagens Reais → [Extração SIFT Python] → Pontos Correspondentes
                                              ↓
                        VHDL Pipeline Hardware:
                        [Fundamental] → [Essential] → [Pose] → [Triangulation]
                                              ↓
                                     Resultados 3D
                                              ↓
                               [Visualização Python]
```

## 📈 Validação com Dados Reais

### 🖼️ Imagens de Teste
- **img1.jpeg / img2.jpeg**: Par estéreo 640×480 pixels
- **Correspondências**: 8 pontos SIFT + RANSAC filtrados
- **Calibração**: Matriz K estimada para focal length 525px

### ✅ Resultados Validados
- **Matriz Fundamental**: Calculada com precisão Q15.16
- **Pose da Câmera**: Rotação e translação extraídas
- **Reconstrução 3D**: Pontos triangulados corretamente
- **Linhas Epipolares**: Geometria epipolar verificada

### 🧪 Testes Realizados
- ✅ Compilação GHDL sem erros
- ✅ Simulação completa (10μs) executada  
- ✅ Resultados consistentes com OpenCV
- ✅ Visualização 3D gerada

## 🚀 Fluxo de Trabalho

1. **Preparação**: Imagens reais em `images/`
2. **Extração**: `extract_points.py` → pontos SIFT
3. **Simulação**: `./run.sh` → processamento VHDL
4. **Visualização**: `visualize_vhdl_results.py` → resultados
5. **Análise**: GTKWave para sinais temporais

## 📝 Arquivos de Configuração

- **`run.sh`**: Automatiza compilação GHDL
- **`tb_top.vhd`**: Dados reais das imagens como testbench
- **`visualize_vhdl_results.py`**: Carrega pontos processados pelo VHDL

## 🎓 Conceitos Implementados

- **Geometria Epipolar**: Relação fundamental entre pares de imagens
- **Calibração**: Matriz intrínseca da câmera
- **Estimação Robusta**: Outlier rejection via dados pré-filtrados
- **Aritmética de Hardware**: Otimização para FPGA

## 🔮 Próximos Desenvolvimentos

- [ ] Interface PCIe para integração sistema
- [ ] Otimização específica por FPGA (Xilinx/Intel)
- [ ] Suporte para vídeo em tempo real
- [ ] Bundle adjustment para múltiplas imagens
- [ ] Benchmarks de performance detalhados

## 📄 Licença

NO License - veja [LICENSE](LICENSE) para detalhes.



## 📚 Referências

1. Hartley & Zisserman - "Multiple View Geometry in Computer Vision"
2. Ma et al. - "An Invitation to 3-D Vision"  
3. OpenCV Structure from Motion Documentation
4. GHDL Simulation Guide

---

