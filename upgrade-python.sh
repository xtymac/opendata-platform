#!/bin/bash

# Python 3.10 升级脚本
echo "🐍 升级到Python 3.10..."

# 安装Python 3.10
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# 创建新的虚拟环境
echo "🔄 创建新的虚拟环境..."
python3.10 -m venv ckan-env-310
source ckan-env-310/bin/activate

# 安装依赖
echo "📦 安装CKAN依赖..."
pip install --upgrade pip
pip install -e .
pip install -r requirements.txt

echo "✅ Python 3.10环境已准备就绪！"
echo "🔧 使用方法:"
echo "   source ckan-env-310/bin/activate"
echo "   ckan -c ckan.ini db init"
