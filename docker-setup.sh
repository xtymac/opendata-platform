#!/bin/bash

# CKAN Docker 部署脚本
echo "🚀 开始设置CKAN Docker环境..."

# 创建必要的目录
mkdir -p ckan-data
mkdir -p ckan-logs

# 下载并启动CKAN Docker Compose
echo "📦 下载CKAN Docker配置..."
curl -L https://raw.githubusercontent.com/ckan/ckan/master/docker-compose.yml -o docker-compose.yml

# 修改配置以适合开发环境
cat > docker-compose.override.yml << EOF
version: '3'
services:
  ckan:
    environment:
      - CKAN_SITE_URL=http://localhost:5000
    ports:
      - "5000:5000"
    volumes:
      - ./ckan-data:/var/lib/ckan
      - ./ckan-logs:/var/log/ckan
EOF

echo "🔧 启动CKAN服务..."
docker-compose up -d

echo "⏳ 等待服务启动..."
sleep 30

echo "🔑 创建管理员用户..."
docker-compose exec ckan ckan user add admin email=admin@example.com password=admin123
docker-compose exec ckan ckan sysadmin add admin

echo "✅ CKAN已启动！"
echo "🌐 访问地址: http://localhost:5000"
echo "👤 管理员账号: admin@example.com"
echo "🔒 管理员密码: admin123"
