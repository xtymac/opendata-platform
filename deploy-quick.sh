#!/bin/bash

# Yamaguchi OpenData Platform 快速部署脚本
# 一键部署到云服务器

set -e

echo "🚀 Yamaguchi OpenData Platform 快速部署"
echo "====================================="

# 检测云服务商
detect_cloud_provider() {
    if curl -s --max-time 2 http://169.254.169.254/latest/meta-data/ &>/dev/null; then
        echo "AWS"
    elif curl -s --max-time 2 http://100.100.100.200/latest/meta-data/ &>/dev/null; then
        echo "Aliyun"
    elif curl -s --max-time 2 http://169.254.169.254/metadata/instance &>/dev/null; then
        echo "Azure"
    else
        echo "Unknown"
    fi
}

CLOUD_PROVIDER=$(detect_cloud_provider)
echo "检测到云服务商: $CLOUD_PROVIDER"

# 安装Docker
echo "📦 安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
fi

# 安装Docker Compose
echo "📦 安装Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# 启动服务
echo "🚀 启动Yamaguchi OpenData Platform..."
if docker-compose -f docker-compose.prod.yml ps | grep -q yamaguchi-ckan; then
    echo "服务已在运行，重启中..."
    docker-compose -f docker-compose.prod.yml restart
else
    echo "首次启动服务..."
    docker-compose -f docker-compose.prod.yml up -d
fi

# 等待服务就绪
echo "⏳ 等待服务启动..."
sleep 30

# 获取访问地址
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")

echo ""
echo "🎉 部署完成！"
echo "================"
echo "🌐 访问地址: http://$SERVER_IP:5000"
echo "👤 管理员: admin@yamaguchi.jp"
echo "🔒 密码: admin123"
echo ""
echo "💡 提示:"
echo "  - 首次访问可能需要几分钟初始化"
echo "  - 请及时修改默认密码"
echo "  - 查看日志: docker-compose -f docker-compose.prod.yml logs -f"
echo ""