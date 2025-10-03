#!/usr/bin/env python3
"""
Script para extrair pontos correspondentes das imagens locais e gerar dados VHDL
"""

import cv2
import numpy as np
import os

def q15_16_to_vhdl(value):
    """Converte um valor float para formato Q15.16 e retorna como código VHDL"""
    # Q15.16: 1 bit sinal + 15 bits inteiros + 16 bits fracionários
    q15_16_value = int(value * 65536)  # 2^16 = 65536
    return f"to_signed({q15_16_value}, 32)"

def extract_feature_points(img1_path, img2_path, max_points=10):
    """
    Extrai pontos correspondentes entre duas imagens usando SIFT
    """
    print(f"Carregando imagens:")
    print(f"  - {img1_path}")
    print(f"  - {img2_path}")
    
    # Carregar imagens em escala de cinza
    img1 = cv2.imread(img1_path, 0)
    img2 = cv2.imread(img2_path, 0)
    
    if img1 is None or img2 is None:
        print("Erro: Não foi possível carregar as imagens!")
        return None, None
    
    print(f"Dimensões das imagens:")
    print(f"  - Imagem 1: {img1.shape}")
    print(f"  - Imagem 2: {img2.shape}")
    
    # Criar detector SIFT
    sift = cv2.SIFT_create()
    
    # Detectar keypoints e descritores
    kp1, desc1 = sift.detectAndCompute(img1, None)
    kp2, desc2 = sift.detectAndCompute(img2, None)
    
    print(f"Keypoints detectados:")
    print(f"  - Imagem 1: {len(kp1)}")
    print(f"  - Imagem 2: {len(kp2)}")
    
    # Matcher FLANN
    FLANN_INDEX_KDTREE = 0
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    
    # Encontrar correspondências
    matches = flann.knnMatch(desc1, desc2, k=2)
    
    # Aplicar teste de razão (Lowe's ratio test)
    good_matches = []
    pts1 = []
    pts2 = []
    
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < 0.7 * n.distance:
                good_matches.append(m)
                pts1.append(kp1[m.queryIdx].pt)
                pts2.append(kp2[m.trainIdx].pt)
    
    print(f"Correspondências válidas encontradas: {len(good_matches)}")
    
    # Converter para arrays numpy
    pts1 = np.array(pts1, dtype=np.float32)
    pts2 = np.array(pts2, dtype=np.float32)
    
    # Calcular matriz fundamental para filtrar outliers
    if len(pts1) >= 8:
        F, mask = cv2.findFundamentalMat(pts1, pts2, cv2.FM_RANSAC)
        if mask is not None:
            pts1 = pts1[mask.ravel() == 1]
            pts2 = pts2[mask.ravel() == 1]
            print(f"Pontos inliers após RANSAC: {len(pts1)}")
    
    # Limitar ao número máximo de pontos
    if len(pts1) > max_points:
        indices = np.random.choice(len(pts1), max_points, replace=False)
        pts1 = pts1[indices]
        pts2 = pts2[indices]
        print(f"Limitado a {max_points} pontos para o VHDL")
    
    return pts1, pts2

def generate_vhdl_data(pts1, pts2):
    """
    Gera código VHDL para inicializar os arrays de pontos
    """
    if pts1 is None or pts2 is None:
        return ""
    
    vhdl_code = "        -- Dados extraídos das imagens locais img1.jpeg e img2.jpeg\n"
    vhdl_code += "        -- Pontos correspondentes encontrados via SIFT + RANSAC\n\n"
    
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
    # Caminhos das imagens
    img1_path = "images/img1.jpeg"
    img2_path = "images/img2.jpeg"
    
    # Verificar se as imagens existem
    if not os.path.exists(img1_path):
        print(f"Erro: {img1_path} não encontrado!")
        return
    
    if not os.path.exists(img2_path):
        print(f"Erro: {img2_path} não encontrado!")
        return
    
    # Extrair pontos correspondentes
    pts1, pts2 = extract_feature_points(img1_path, img2_path, max_points=8)
    
    if pts1 is None:
        print("Falha na extração de pontos!")
        return
    
    # Gerar código VHDL
    vhdl_code = generate_vhdl_data(pts1, pts2)
    
    # Salvar em arquivo
    with open("vhdl_points_data.txt", "w") as f:
        f.write(vhdl_code)
    
    print(f"\nCódigo VHDL gerado e salvo em 'vhdl_points_data.txt'")
    print(f"Total de pontos: {len(pts1)}")
    print("\nPré-visualização do código VHDL:")
    print("=" * 60)
    print(vhdl_code[:800] + "..." if len(vhdl_code) > 800 else vhdl_code)

if __name__ == "__main__":
    main()