# 🚀 Yamaguchi OpenData Platform 云端部署指南

## 📋 目录
1. [AWS 部署方案](#aws-部署方案)
2. [阿里云部署方案](#阿里云部署方案)
3. [Azure 部署方案](#azure-部署方案)
4. [通用 Docker 部署](#通用-docker-部署)
5. [域名和SSL配置](#域名和ssl配置)
6. [监控和维护](#监控和维护)

---

## 🎯 推荐方案：AWS 部署

### 步骤1: 创建EC2实例

```bash
# 1. 登录AWS控制台，创建EC2实例
# 推荐配置：
# - 实例类型: t3.medium (2 vCPU, 4GB RAM)
# - 操作系统: Ubuntu 22.04 LTS
# - 存储: 30GB gp3
# - 安全组: 开放端口 22, 80, 443, 5000

# 2. 连接到实例
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### 步骤2: 安装依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker和Docker Compose
sudo apt install -y docker.io docker-compose git nginx

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

# 重新登录以应用Docker权限
exit
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### 步骤3: 部署CKAN

```bash
# 克隆项目
git clone https://github.com/your-repo/yamaguchi-ckan.git
cd yamaguchi-ckan

# 创建生产环境配置
cp docker-compose.yml docker-compose.prod.yml

# 修改生产配置
nano docker-compose.prod.yml
```

### 步骤4: 环境配置

```bash
# 创建环境变量文件
cat > .env << EOF
# 数据库配置
POSTGRES_USER=ckan_default
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=ckan_default

# CKAN配置
CKAN_SITE_URL=https://opendata.yamaguchi.jp
CKAN_SECRET_KEY=$(openssl rand -base64 32)

# Redis配置
REDIS_URL=redis://redis:6379/0

# Solr配置
SOLR_URL=http://solr:8983/solr/ckan
EOF
```

---

## 🇨🇳 阿里云部署方案

### 步骤1: 创建ECS实例

```bash
# 1. 登录阿里云控制台
# 2. 创建ECS实例
# 推荐配置：
# - 实例规格: ecs.t6-c2m4.large (2核4GB)
# - 镜像: Ubuntu 22.04
# - 系统盘: 40GB ESSD
# - 安全组: 开放22, 80, 443, 5000端口

# 3. 连接实例
ssh root@your-ecs-ip
```

### 步骤2: 快速部署脚本

```bash
# 下载快速部署脚本
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker

# 安装必要工具
apt install -y git nginx certbot python3-certbot-nginx

# 克隆项目
git clone https://github.com/your-repo/yamaguchi-ckan.git
cd yamaguchi-ckan

# 运行部署脚本
chmod +x deploy-aliyun.sh
./deploy-aliyun.sh
```

---

## ⚡ 通用 Docker 部署

### Docker Compose 生产配置

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  ckan:
    build: .
    container_name: yamaguchi-ckan
    environment:
      - CKAN_SITE_URL=${CKAN_SITE_URL}
      - CKAN_SECRET_KEY=${CKAN_SECRET_KEY}
      - CKAN_SQLALCHEMY_URL=postgresql://ckan_default:${POSTGRES_PASSWORD}@db/ckan_default
      - CKAN_DATASTORE_WRITE_URL=postgresql://ckan_default:${POSTGRES_PASSWORD}@db/datastore_default
      - CKAN_DATASTORE_READ_URL=postgresql://datastore_default:${POSTGRES_PASSWORD}@db/datastore_default
      - CKAN_REDIS_URL=${REDIS_URL}
      - CKAN_SOLR_URL=${SOLR_URL}
    ports:
      - "5000:5000"
    depends_on:
      - db
      - redis
      - solr
    volumes:
      - ckan_storage:/var/lib/ckan
    restart: unless-stopped

  db:
    image: postgres:15
    container_name: yamaguchi-postgres
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: yamaguchi-redis
    restart: unless-stopped

  solr:
    image: ckan/ckan-solr:2.9-solr8
    container_name: yamaguchi-solr
    volumes:
      - solr_data:/var/solr
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: yamaguchi-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt
    depends_on:
      - ckan
    restart: unless-stopped

volumes:
  postgres_data:
  solr_data:
  ckan_storage:
```

### Nginx 配置

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream ckan {
        server ckan:5000;
    }

    server {
        listen 80;
        server_name opendata.yamaguchi.jp;

        # HTTP重定向到HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name opendata.yamaguchi.jp;

        # SSL配置
        ssl_certificate /etc/letsencrypt/live/opendata.yamaguchi.jp/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/opendata.yamaguchi.jp/privkey.pem;

        # 安全头
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";

        # Gzip压缩
        gzip on;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

        location / {
            proxy_pass http://ckan;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 静态文件缓存
        location /base/ {
            proxy_pass http://ckan;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

---

## 🛡️ 域名和SSL配置

### 申请免费SSL证书

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 申请证书
sudo certbot --nginx -d opendata.yamaguchi.jp

# 设置自动续期
sudo crontab -e
# 添加以下行:
0 3 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

### DNS配置

```bash
# 在域名服务商添加以下记录：
# A记录: opendata.yamaguchi.jp -> 你的服务器IP
# CNAME记录: www.opendata.yamaguchi.jp -> opendata.yamaguchi.jp
```

---

## 📊 监控和维护

### 日志监控

```bash
# 查看容器日志
docker-compose logs -f ckan

# 设置日志轮转
cat > /etc/logrotate.d/docker << EOF
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=1M
    missingok
    delaycompress
    copytruncate
}
EOF
```

### 备份策略

```bash
#!/bin/bash
# backup.sh - 每日备份脚本

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup"

# 备份数据库
docker exec yamaguchi-postgres pg_dump -U ckan_default ckan_default > $BACKUP_DIR/ckan_$DATE.sql

# 备份文件存储
docker cp yamaguchi-ckan:/var/lib/ckan $BACKUP_DIR/ckan_files_$DATE

# 清理7天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "ckan_files_*" -mtime +7 -exec rm -rf {} \;

# 上传到云存储（可选）
# aws s3 sync $BACKUP_DIR s3://yamaguchi-backup/
```

---

## 🚀 部署命令速查

```bash
# 快速部署
git clone https://github.com/your-repo/yamaguchi-ckan.git
cd yamaguchi-ckan
chmod +x deploy.sh
./deploy.sh

# 更新部署
git pull
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# 查看状态
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

## 💰 成本估算

### AWS (东京区域)
- EC2 t3.medium: $30/月
- EBS 30GB: $3/月
- 流量 100GB: $9/月
- **总计**: ~$42/月

### 阿里云 (中国香港)
- ECS 2核4GB: ¥200/月
- 云盘 40GB: ¥15/月
- 流量 100GB: ¥50/月
- **总计**: ~¥265/月

需要我为您创建具体的部署脚本吗？