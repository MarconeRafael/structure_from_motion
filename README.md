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

## 🔍 Especificações Técnicas

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

MIT License - veja [LICENSE](LICENSE) para detalhes.

## 🤝 Contribuição

Contribuições são bem-vindas! Por favor:
1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças  
4. Push para a branch
5. Abra um Pull Request

## 📚 Referências

1. Hartley & Zisserman - "Multiple View Geometry in Computer Vision"
2. Ma et al. - "An Invitation to 3-D Vision"  
3. OpenCV Structure from Motion Documentation
4. GHDL Simulation Guide

---

**🚀 Status**: Projeto Completo e Funcional  
**📅 Última Atualização**: Outubro 2025  
**🏷️ Versão**: 1.0.0