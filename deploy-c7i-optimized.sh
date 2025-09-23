#!/bin/bash

# Yamaguchi OpenData Platform 部署脚本 - c7i-flex 优化版
# 针对 AWS c7i-flex.large 实例优化

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "🚀 Yamaguchi OpenData Platform - c7i-flex 优化部署"
echo "=================================================="

# 检测实例类型
INSTANCE_TYPE=$(curl -s http://169.254.169.254/latest/meta-data/instance-type 2>/dev/null || echo "unknown")
log_info "检测到实例类型: $INSTANCE_TYPE"

if [[ $INSTANCE_TYPE == c7i-flex* ]]; then
    log_success "检测到c7i-flex实例，启用优化配置"
    USE_C7I_OPTIMIZATIONS=true
else
    log_warning "未检测到c7i-flex实例，使用标准配置"
    USE_C7I_OPTIMIZATIONS=false
fi

# 系统优化（针对c7i-flex）
optimize_system() {
    log_info "优化系统配置..."

    # 更新系统
    sudo apt update && sudo apt upgrade -y

    # 安装性能工具
    sudo apt install -y htop iotop sysstat curl wget git

    if [ "$USE_C7I_OPTIMIZATIONS" = true ]; then
        # c7i-flex 特定优化
        log_info "应用c7i-flex优化配置..."

        # 启用高性能CPU调控器
        echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

        # 优化网络参数
        cat >> /tmp/99-network-optimizations.conf << EOF
# c7i-flex 网络优化
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.netdev_max_backlog = 5000
EOF
        sudo mv /tmp/99-network-optimizations.conf /etc/sysctl.d/
        sudo sysctl -p /etc/sysctl.d/99-network-optimizations.conf

        # 禁用不必要的服务
        sudo systemctl disable snapd.service || true
        sudo systemctl stop snapd.service || true
    fi

    log_success "系统优化完成"
}

# 安装Docker（优化版本）
install_docker() {
    if ! command -v docker &> /dev/null; then
        log_info "安装Docker..."

        # 安装Docker官方仓库
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        sudo apt update
        sudo apt install -y docker-ce docker-ce-cli containerd.io

        # Docker优化配置
        sudo mkdir -p /etc/docker
        cat > /tmp/daemon.json << EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "storage-driver": "overlay2"
EOF

        if [ "$USE_C7I_OPTIMIZATIONS" = true ]; then
            cat >> /tmp/daemon.json << EOF
    ,
    "default-ulimits": {
        "nofile": {
            "Hard": 64000,
            "Name": "nofile",
            "Soft": 64000
        }
    }
EOF
        fi

        echo "}" >> /tmp/daemon.json
        sudo mv /tmp/daemon.json /etc/docker/daemon.json

        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER

        log_success "Docker安装完成"
    else
        log_success "Docker已安装"
    fi
}

# 安装Docker Compose
install_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        log_info "安装Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        log_success "Docker Compose安装完成"
    else
        log_success "Docker Compose已安装"
    fi
}

# 创建优化的环境配置
create_optimized_env() {
    log_info "创建优化的环境配置..."

    # 获取实例信息
    SERVER_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || curl -s ifconfig.me)
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "unknown")

    # 生成强密码
    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    CKAN_SECRET_KEY=$(openssl rand -base64 32)

    cat > .env << EOF
# Yamaguchi OpenData Platform - c7i-flex 优化配置
# Instance: $INSTANCE_TYPE ($INSTANCE_ID)
# Generated: $(date)

# 基本配置
ENVIRONMENT=production
DEBUG=false
CKAN_SITE_URL=http://$SERVER_IP:5000
CKAN_SECRET_KEY=$CKAN_SECRET_KEY

# 数据库配置
POSTGRES_USER=ckan_default
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=ckan_default

# 性能配置
CKAN_PORT=5000
REDIS_URL=redis://redis:6379/0
SOLR_URL=http://solr:8983/solr/ckan

# c7i-flex 性能优化
CKAN_MAX_WORKERS=4
POSTGRES_MAX_CONNECTIONS=200
SOLR_HEAP=2g
REDIS_MAXMEMORY=512mb
EOF

    log_success "环境配置创建完成"
    log_info "访问地址将是: http://$SERVER_IP:5000"
}

# 创建c7i-flex优化的Docker Compose配置
create_optimized_compose() {
    log_info "创建优化的Docker Compose配置..."

    cat > docker-compose.c7i.yml << 'EOF'
version: '3.8'

services:
  ckan:
    build: .
    container_name: yamaguchi-ckan-c7i
    environment:
      - CKAN_SITE_URL=${CKAN_SITE_URL}
      - CKAN_SECRET_KEY=${CKAN_SECRET_KEY}
      - CKAN_SQLALCHEMY_URL=postgresql://ckan_default:${POSTGRES_PASSWORD}@db/ckan_default
      - CKAN_DATASTORE_WRITE_URL=postgresql://ckan_default:${POSTGRES_PASSWORD}@db/datastore_default
      - CKAN_DATASTORE_READ_URL=postgresql://datastore_default:${POSTGRES_PASSWORD}@db/datastore_default
      - CKAN_REDIS_URL=${REDIS_URL}
      - CKAN_SOLR_URL=${SOLR_URL}
      - CKAN_WORKERS=${CKAN_MAX_WORKERS:-4}
    ports:
      - "${CKAN_PORT:-5000}:5000"
    depends_on:
      - db
      - redis
      - solr
    volumes:
      - ckan_storage:/var/lib/ckan
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.5'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G

  db:
    image: postgres:15-alpine
    container_name: yamaguchi-postgres-c7i
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8
    command: [
      "postgres",
      "-c", "max_connections=${POSTGRES_MAX_CONNECTIONS:-200}",
      "-c", "shared_buffers=256MB",
      "-c", "effective_cache_size=1GB",
      "-c", "maintenance_work_mem=64MB",
      "-c", "checkpoint_completion_target=0.9",
      "-c", "wal_buffers=16MB",
      "-c", "default_statistics_target=100"
    ]
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  redis:
    image: redis:7-alpine
    container_name: yamaguchi-redis-c7i
    command: [
      "redis-server",
      "--appendonly", "yes",
      "--maxmemory", "${REDIS_MAXMEMORY:-512mb}",
      "--maxmemory-policy", "allkeys-lru"
    ]
    volumes:
      - redis_data:/data
    restart: unless-stopped

  solr:
    image: ckan/ckan-solr:2.9-solr8
    container_name: yamaguchi-solr-c7i
    environment:
      - SOLR_HEAP=${SOLR_HEAP:-2g}
    volumes:
      - solr_data:/var/solr
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  solr_data:
  ckan_storage:
EOF

    log_success "优化的Docker Compose配置创建完成"
}

# 主部署流程
main() {
    optimize_system
    install_docker
    install_docker_compose
    create_optimized_env
    create_optimized_compose

    log_info "开始构建和启动服务..."

    # 重新登录以应用Docker组权限
    if ! docker ps &>/dev/null; then
        log_warning "需要重新登录以应用Docker权限"
        log_info "请运行: newgrp docker"
        log_info "然后执行: docker-compose -f docker-compose.c7i.yml up -d"
        exit 0
    fi

    # 启动服务
    docker-compose -f docker-compose.c7i.yml up -d

    log_info "等待服务启动..."
    sleep 30

    # 初始化CKAN
    log_info "初始化CKAN数据库..."
    docker exec yamaguchi-ckan-c7i ckan db init || true

    # 获取访问信息
    SERVER_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || curl -s ifconfig.me)

    echo ""
    log_success "🎉 Yamaguchi OpenData Platform 部署完成！"
    echo "=================================================="
    echo "🌐 访问地址: http://$SERVER_IP:5000"
    echo "🖥️  实例类型: $INSTANCE_TYPE"
    echo "⚡ 性能优化: 已启用"
    echo "=================================================="
    echo ""
    log_info "常用命令:"
    echo "  查看状态: docker-compose -f docker-compose.c7i.yml ps"
    echo "  查看日志: docker-compose -f docker-compose.c7i.yml logs -f"
    echo "  重启服务: docker-compose -f docker-compose.c7i.yml restart"
    echo ""
}

main "$@"