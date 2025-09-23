# CKAN 部署指南

## 🎯 推荐方案

### 方案1: 云端部署（最佳选择）

#### AWS 部署
```bash
# 1. 创建EC2实例 (Ubuntu 22.04)
# 2. 安装Docker和Docker Compose
sudo apt update
sudo apt install -y docker.io docker-compose

# 3. 克隆项目并启动
git clone <your-repo>
cd ckan
./docker-setup.sh
```

#### 阿里云部署
```bash
# 1. 创建ECS实例
# 2. 配置安全组 (开放5000端口)
# 3. 安装Docker
sudo apt update
sudo apt install -y docker.io docker-compose

# 4. 启动CKAN
./docker-setup.sh
```

### 方案2: 本地Docker部署

```bash
# 运行Docker设置脚本
./docker-setup.sh
```

### 方案3: 本地Python环境升级

```bash
# 升级Python到3.10
./upgrade-python.sh

# 然后初始化CKAN
source ckan-env-310/bin/activate
ckan -c ckan.ini db init
ckan -c ckan.ini user add admin email=admin@example.com password=admin123
ckan -c ckan.ini sysadmin add admin
ckan -c ckan.ini run
```

## 🌐 访问信息

- **URL**: http://localhost:5000 (本地) 或 http://your-server-ip:5000 (云端)
- **管理员账号**: admin@example.com
- **管理员密码**: admin123

## 📊 服务要求

### 最低配置
- **CPU**: 2核心
- **内存**: 4GB RAM
- **存储**: 20GB SSD
- **网络**: 100Mbps

### 推荐配置
- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 50GB SSD
- **网络**: 1Gbps

## 🔧 配置文件

主要配置文件：
- `ckan.ini` - CKAN主配置
- `docker-compose.yml` - Docker服务配置
- `requirements.txt` - Python依赖

## 🚀 生产环境建议

1. **使用HTTPS**: 配置SSL证书
2. **数据库优化**: 使用专用PostgreSQL实例
3. **搜索优化**: 使用Elasticsearch替代Solr
4. **缓存**: 配置Redis集群
5. **监控**: 添加日志和监控系统
6. **备份**: 定期备份数据库和文件

## 📞 技术支持

如果遇到问题：
1. 检查日志文件
2. 确认所有服务都在运行
3. 验证端口是否开放
4. 检查防火墙设置
