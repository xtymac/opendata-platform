#!/bin/bash

# Yamaguchi OpenData Platform 部署脚本
# Author: Claude AI
# Version: 1.0

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_warning "建议不要使用root用户运行此脚本"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 检查系统要求
check_requirements() {
    log_info "检查系统要求..."

    # 检查操作系统
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_success "操作系统: Linux"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi

    # 检查内存
    MEMORY=$(free -m | awk 'NR==2{printf "%.1f", $2/1024}')
    if (( $(echo "$MEMORY >= 2.0" | bc -l) )); then
        log_success "内存: ${MEMORY}GB"
    else
        log_warning "内存不足 (${MEMORY}GB < 2GB), 可能影响性能"
    fi

    # 检查磁盘空间
    DISK=$(df -h / | awk 'NR==2 {print $4}' | sed 's/G//')
    if (( $(echo "$DISK >= 10" | bc -l) )); then
        log_success "磁盘空间: ${DISK}GB 可用"
    else
        log_error "磁盘空间不足 (${DISK}GB < 10GB)"
        exit 1
    fi
}

# 安装Docker
install_docker() {
    if ! command -v docker &> /dev/null; then
        log_info "安装Docker..."
        curl -fsSL https://get.docker.com | sh
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

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."

    mkdir -p nginx/ssl
    mkdir -p postgresql
    mkdir -p backups
    mkdir -p logs

    log_success "目录结构创建完成"
}

# 生成环境配置
generate_env() {
    if [ ! -f .env ]; then
        log_info "生成环境配置..."

        # 生成随机密码
        POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        CKAN_SECRET_KEY=$(openssl rand -base64 32)

        # 获取服务器IP
        SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")

        cat > .env << EOF
# 数据库配置
POSTGRES_USER=ckan_default
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=ckan_default

# CKAN配置
CKAN_SITE_URL=http://$SERVER_IP:5000
CKAN_SECRET_KEY=$CKAN_SECRET_KEY
CKAN_PORT=5000

# Redis配置
REDIS_URL=redis://redis:6379/0

# Solr配置
SOLR_URL=http://solr:8983/solr/ckan

# 部署环境
ENVIRONMENT=production
DEBUG=false
EOF

        log_success "环境配置生成完成"
        log_warning "请检查并修改 .env 文件中的配置"
    else
        log_success "环境配置已存在"
    fi
}

# 创建数据库初始化脚本
create_db_init() {
    log_info "创建数据库初始化脚本..."

    cat > postgresql/init-db.sql << 'EOF'
-- 创建数据存储用户和数据库
CREATE USER datastore_default WITH PASSWORD 'pass';
CREATE DATABASE datastore_default OWNER ckan_default ENCODING 'utf-8';

-- 设置权限
GRANT ALL PRIVILEGES ON DATABASE ckan_default TO ckan_default;
GRANT ALL PRIVILEGES ON DATABASE datastore_default TO ckan_default;
GRANT CONNECT ON DATABASE datastore_default TO datastore_default;
GRANT USAGE ON SCHEMA public TO datastore_default;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO datastore_default;
ALTER DEFAULT PRIVILEGES FOR USER ckan_default IN SCHEMA public GRANT SELECT ON TABLES TO datastore_default;
EOF

    log_success "数据库初始化脚本创建完成"
}

# 创建Nginx配置
create_nginx_config() {
    log_info "创建Nginx配置..."

    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # 基本设置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    upstream ckan {
        server ckan:5000;
    }

    server {
        listen 80;
        server_name _;

        # 安全头
        add_header X-Frame-Options SAMEORIGIN;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";

        location / {
            proxy_pass http://ckan;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # 静态文件缓存
        location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
            proxy_pass http://ckan;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # 健康检查
        location /health {
            proxy_pass http://ckan/api/3/action/status_show;
        }
    }
}
EOF

    log_success "Nginx配置创建完成"
}

# 创建Dockerfile
create_dockerfile() {
    if [ ! -f Dockerfile ]; then
        log_info "创建Dockerfile..."

        cat > Dockerfile << 'EOF'
FROM ckan/ckan-base:2.10

# 安装额外的Python包
USER ckan
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# 复制CKAN配置和扩展
COPY --chown=ckan:ckan ckan /srv/app/src/ckan/ckan
COPY --chown=ckan:ckan ckanext /srv/app/src/ckan/ckanext

# 设置工作目录
WORKDIR /srv/app/src/ckan

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["ckan", "run", "--host", "0.0.0.0", "--port", "5000"]
EOF

        log_success "Dockerfile创建完成"
    else
        log_success "Dockerfile已存在"
    fi
}

# 创建备份脚本
create_backup_script() {
    log_info "创建备份脚本..."

    cat > backup.sh << 'EOF'
#!/bin/bash

# Yamaguchi OpenData Platform 备份脚本

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
CONTAINER_PREFIX="yamaguchi"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
echo "备份数据库..."
docker exec ${CONTAINER_PREFIX}-postgres pg_dump -U ckan_default ckan_default > $BACKUP_DIR/ckan_$DATE.sql
docker exec ${CONTAINER_PREFIX}-postgres pg_dump -U ckan_default datastore_default > $BACKUP_DIR/datastore_$DATE.sql

# 备份文件存储
echo "备份文件存储..."
docker cp ${CONTAINER_PREFIX}-ckan:/var/lib/ckan $BACKUP_DIR/ckan_files_$DATE

# 压缩备份
echo "压缩备份文件..."
tar -czf $BACKUP_DIR/yamaguchi_backup_$DATE.tar.gz $BACKUP_DIR/ckan_$DATE.sql $BACKUP_DIR/datastore_$DATE.sql $BACKUP_DIR/ckan_files_$DATE

# 清理临时文件
rm -f $BACKUP_DIR/ckan_$DATE.sql $BACKUP_DIR/datastore_$DATE.sql
rm -rf $BACKUP_DIR/ckan_files_$DATE

# 清理7天前的备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "备份完成: $BACKUP_DIR/yamaguchi_backup_$DATE.tar.gz"
EOF

    chmod +x backup.sh
    log_success "备份脚本创建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    # 拉取镜像
    docker-compose -f docker-compose.prod.yml pull

    # 构建并启动服务
    docker-compose -f docker-compose.prod.yml up -d --build

    log_success "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."

    # 等待数据库
    while ! docker exec yamaguchi-postgres pg_isready -U ckan_default &>/dev/null; do
        echo -n "."
        sleep 2
    done
    echo
    log_success "数据库就绪"

    # 等待CKAN
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:5000/api/3/action/status_show &>/dev/null; then
            log_success "CKAN服务就绪"
            return 0
        fi
        echo -n "."
        sleep 5
        ((attempt++))
    done
    echo
    log_warning "CKAN服务启动超时，请检查日志"
}

# 初始化CKAN
initialize_ckan() {
    log_info "初始化CKAN..."

    # 初始化数据库
    docker exec yamaguchi-ckan ckan db init

    # 创建管理员用户
    echo "创建管理员用户..."
    docker exec -it yamaguchi-ckan ckan user add admin email=admin@yamaguchi.jp password=admin123 fullname="Administrator"
    docker exec yamaguchi-ckan ckan sysadmin add admin

    log_success "CKAN初始化完成"
}

# 显示部署信息
show_deployment_info() {
    local SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")

    echo
    log_success "🎉 Yamaguchi OpenData Platform 部署完成！"
    echo
    echo "==============================================="
    echo "🌐 访问地址: http://$SERVER_IP:5000"
    echo "👤 管理员账号: admin@yamaguchi.jp"
    echo "🔒 管理员密码: admin123"
    echo "==============================================="
    echo
    log_warning "请及时修改默认密码！"
    echo
    echo "常用命令:"
    echo "  查看服务状态: docker-compose -f docker-compose.prod.yml ps"
    echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
    echo "  备份数据: ./backup.sh"
    echo
}

# 主函数
main() {
    echo "🚀 Yamaguchi OpenData Platform 部署脚本"
    echo "========================================"

    check_root
    check_requirements
    install_docker
    install_docker_compose
    create_directories
    generate_env
    create_db_init
    create_nginx_config
    create_dockerfile
    create_backup_script
    start_services
    wait_for_services
    initialize_ckan
    show_deployment_info
}

# 执行主函数
main "$@"