
```
# Structure from Motion (SfM) em Hardware

Este projeto implementa o algoritmo **Structure from Motion (SfM)** em hardware, com uma abordagem híbrida que envolve:
- Prototipagem inicial em **Python (Jupyter/Colab)** para validação matemática.
- **Pseudo-código** para descrição algorítmica intermediária.
- Implementação final em **VHDL**, visando execução em FPGA.

---

## 📂 Estrutura do Projeto

.
├── SfM.txt                  # Pseudo-código do algoritmo SfM
├── src/                     # Implementação principal em VHDL
│   ├── Epipolar\_Geometry.ipynb   # Protótipo Python/Colab
│   ├── algebra\_pkg.vhd
│   ├── algebra\_pkg\_body.vhd
│   ├── essential\_matrix.vhd
│   ├── fundamental\_matrix.vhd
│   ├── normalize.vhd
│   ├── pose\_extraction.vhd
│   ├── projective\_pkg.vhd
│   ├── triangulation.vhd
│   └── fixed\_pkg.vhd
├── tb/                      # Testbenches VHDL
│   └── tb\_fundamental.vhd
├── run.sh                   # Script de simulação
├── wave.vcd                 # Saída de simulação (onda)
├── work/, work-obj93.cf     # Diretórios/artefatos de compilação
└── README.md


---

## 🚀 Fluxo de Desenvolvimento

1. **Modelagem matemática**  
   - Uso de **Python (Jupyter/Colab)** para validar:
     - Cálculo da matriz fundamental e essencial.
     - Geometria epipolar.
     - Triangulação de pontos 3D.

2. **Pseudo-código**  
   - Documento `SfM.txt` descreve a lógica algorítmica do pipeline SfM.

3. **Implementação em VHDL**  
   - Arquivos em `src/` contêm a implementação modular:
     - `fundamental_matrix.vhd` → cálculo da matriz fundamental.  
     - `essential_matrix.vhd` → matriz essencial.  
     - `pose_extraction.vhd` → extração da pose (R, t).  
     - `triangulation.vhd` → reconstrução 3D.  
     - `normalize.vhd`, `algebra_pkg.vhd` e `fixed_pkg.vhd` → suporte matemático.  

4. **Simulação**  
   - Testbenches disponíveis em `tb/`.  
   - Rodar simulação com:  
     ```bash
     ./run.sh
     ```

---

## 📖 Referências Teóricas

- Hartley, R., & Zisserman, A. *Multiple View Geometry in Computer Vision*. Cambridge University Press.  
- Ma, Y., Soatto, S., Kosecka, J., & Sastry, S. S. *An Invitation to 3D Vision: From Images to Geometric Models*. Springer.  

---

## 📌 Objetivo

Validar a viabilidade de **aceleração em hardware** para etapas críticas do SfM, explorando arquiteturas FPGA para **redução de latência** em aplicações de visão computacional.

---

## ⚠️ Licença

Este projeto está publicado sob a política de **"No License"**.  
Isso significa que **não há permissão automática para uso, modificação, distribuição ou reutilização** do código.  
Para qualquer utilização, entre em contato com o autor.
````
