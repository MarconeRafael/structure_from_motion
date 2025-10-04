#!/bin/bash
echo "🐍 Configurando ambiente Python para Structure from Motion VHDL..."

# Remover ambiente existente se houver
if [ -d ".venv" ]; then
    echo "Removendo ambiente virtual existente..."
    rm -rf .venv
fi

# Criar novo ambiente
echo "Criando ambiente virtual..."
python3 -m venv .venv

# Ativar ambiente
echo "Ativando ambiente virtual..."
source .venv/bin/activate

# Atualizar pip
echo "Atualizando pip..."
pip install --upgrade pip

# Instalar dependências
echo "Instalando dependências..."
pip install opencv-python numpy matplotlib

# Verificar instalação
echo "Verificando instalação..."
python3 -c "import cv2, numpy, matplotlib; print('✅ Todas as dependências instaladas com sucesso!')"

echo "🎉 Ambiente configurado! Use 'source .venv/bin/activate' para ativar"
