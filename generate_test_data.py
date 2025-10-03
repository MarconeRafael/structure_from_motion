#!/usr/bin/env python3
"""
Gerador de dados de teste simulados para o pipeline VHDL SfM
Como não temos imagens reais, vamos gerar pontos correspondentes simulados
que seguem um padrão típico de calibração/movimento de câmera
"""

import numpy as np

def q15_16_to_vhdl(value):
    """Converte um valor float para formato Q15.16 e retorna como código VHDL"""
    # Q15.16: 1 bit sinal + 15 bits inteiros + 16 bits fracionários
    q15_16_value = int(value * 65536)  # 2^16 = 65536
    return f"to_signed({q15_16_value}, 32)"

def generate_simulated_stereo_points(num_points=8):
    """
    Gera pontos correspondentes simulados para um par estéreo
    Simula uma câmera que se moveu ligeiramente para a direita
    """
    print("Gerando pontos correspondentes simulados...")
    
    # Simular dimensões de imagem típicas (VGA)
    img_width = 640
    img_height = 480
    
    # Gerar pontos aleatórios na primeira imagem
    np.random.seed(42)  # para resultados reproduzíveis
    pts1 = []
    pts2 = []
    
    # Simular uma translação pequena da câmera (movimento para direita)
    baseline = 10.0  # pixels
    disparity_noise = 2.0  # ruído na disparidade
    
    for i in range(num_points):
        # Ponto na primeira imagem
        x1 = np.random.uniform(50, img_width - 50)
        y1 = np.random.uniform(50, img_height - 50)
        
        # Ponto correspondente na segunda imagem (com disparidade)
        # Simular diferentes profundidades
        depth_factor = np.random.uniform(0.5, 2.0)
        disparity = baseline / depth_factor + np.random.normal(0, disparity_noise)
        
        x2 = x1 + disparity
        y2 = y1 + np.random.normal(0, 1.0)  # pequeno ruído vertical
        
        # Garantir que os pontos estão dentro da imagem
        x2 = np.clip(x2, 0, img_width - 1)
        y2 = np.clip(y2, 0, img_height - 1)
        
        pts1.append([x1, y1])
        pts2.append([x2, y2])
    
    return np.array(pts1), np.array(pts2)

def generate_calibration_matrix():
    """Gera uma matriz de calibração típica"""
    # Parâmetros típicos para uma câmera VGA
    fx = 525.0  # distância focal em pixels
    fy = 525.0
    cx = 320.0  # centro da imagem
    cy = 240.0
    
    K = np.array([
        [fx, 0, cx],
        [0, fy, cy],
        [0, 0, 1]
    ])
    
    return K

def generate_vhdl_testbench_data(pts1, pts2, K):
    """
    Gera código VHDL completo para o testbench
    """
    vhdl_code = """        -- Dados simulados de pontos correspondentes
        -- Representam um par estéreo com movimento lateral da câmera
        
        -- Inicializar matriz de calibração K (parâmetros típicos VGA)
        K_matrix <= (others => (others => (others => '0')));
"""
    
    # Matriz K
    vhdl_code += f"        K_matrix(0,0) <= {q15_16_to_vhdl(K[0,0])};  -- fx = {K[0,0]:.1f}\n"
    vhdl_code += f"        K_matrix(1,1) <= {q15_16_to_vhdl(K[1,1])};  -- fy = {K[1,1]:.1f}\n"
    vhdl_code += f"        K_matrix(2,2) <= {q15_16_to_vhdl(K[2,2])};  -- 1.0\n"
    vhdl_code += f"        K_matrix(0,2) <= {q15_16_to_vhdl(K[0,2])};  -- cx = {K[0,2]:.1f}\n"
    vhdl_code += f"        K_matrix(1,2) <= {q15_16_to_vhdl(K[1,2])};  -- cy = {K[1,2]:.1f}\n\n"
    
    # Pontos correspondentes
    vhdl_code += "        -- Pontos correspondentes simulados\n"
    for i, (pt1, pt2) in enumerate(zip(pts1, pts2)):
        x1, y1 = pt1
        x2, y2 = pt2
        
        vhdl_code += f"        -- Ponto {i+1}\n"
        vhdl_code += f"        pts1_in({i}, 0) <= {q15_16_to_vhdl(x1)};  -- x1 = {x1:.1f}\n"
        vhdl_code += f"        pts1_in({i}, 1) <= {q15_16_to_vhdl(y1)};  -- y1 = {y1:.1f}\n"
        vhdl_code += f"        pts2_in({i}, 0) <= {q15_16_to_vhdl(x2)};  -- x2 = {x2:.1f}\n"
        vhdl_code += f"        pts2_in({i}, 1) <= {q15_16_to_vhdl(y2)};  -- y2 = {y2:.1f}\n\n"
    
    return vhdl_code

def main():
    print("=== Gerador de Dados de Teste para Pipeline VHDL SfM ===\n")
    
    # Gerar pontos simulados
    pts1, pts2 = generate_simulated_stereo_points(num_points=8)
    
    # Gerar matriz de calibração
    K = generate_calibration_matrix()
    
    print(f"Pontos gerados:")
    print(f"  - Imagem 1: {len(pts1)} pontos")
    print(f"  - Imagem 2: {len(pts2)} pontos")
    print(f"  - Matriz K: {K[0,0]:.1f}x{K[1,1]:.1f} focal length, centro ({K[0,2]:.1f}, {K[1,2]:.1f})")
    
    # Calcular disparidade média para verificação
    disparities = pts2[:, 0] - pts1[:, 0]
    print(f"  - Disparidade média: {np.mean(disparities):.2f} ± {np.std(disparities):.2f} pixels")
    
    # Gerar código VHDL
    vhdl_code = generate_vhdl_testbench_data(pts1, pts2, K)
    
    # Salvar em arquivo
    with open("vhdl_testbench_data.txt", "w") as f:
        f.write(vhdl_code)
    
    print(f"\nCódigo VHDL gerado e salvo em 'vhdl_testbench_data.txt'")
    print("\nPré-visualização do código VHDL:")
    print("=" * 60)
    print(vhdl_code[:1000] + "..." if len(vhdl_code) > 1000 else vhdl_code)
    
    # Salvar também dados Python para análise
    np.savez("simulated_data.npz", pts1=pts1, pts2=pts2, K=K)
    print("\nDados Python salvos em 'simulated_data.npz' para análise posterior")

if __name__ == "__main__":
    main()