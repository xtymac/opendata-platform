# 🚀 AWS 部署详细指南

## 📱 **手机端操作指南**

如果您在手机上操作，推荐使用AWS官方App：
- iOS: [AWS Console](https://apps.apple.com/app/aws-console/id580990573)
- Android: [AWS Console](https://play.google.com/store/apps/details?id=com.amazon.aws.console)

## 🖥️ **桌面端操作指南**

### **1. 登录AWS控制台**
访问：https://console.aws.amazon.com

### **2. 选择区域**
在右上角选择距离用户最近的区域：
- **ap-northeast-1 (Tokyo)** - 推荐亚洲用户
- **us-east-1 (N. Virginia)** - 推荐全球用户

### **3. 创建EC2实例（详细步骤）**

#### 步骤A: 进入EC2服务
1. 在AWS控制台搜索框输入 "EC2"
2. 点击 "EC2" 服务

#### 步骤B: 启动实例
1. 点击橙色的 **"Launch instance"** 按钮
2. 填写实例名称：`yamaguchi-opendata`

#### 步骤C: 选择系统镜像
1. 选择 **"Ubuntu Server 22.04 LTS"**
2. 确保显示 "Free tier eligible"

#### 步骤D: 选择实例类型
1. 选择 **"t3.medium"** (2 vCPU, 4 GiB Memory)
   - 如果预算紧张，可选择 t2.micro (免费层)

#### 步骤E: 创建密钥对
1. 点击 **"Create new key pair"**
2. 密钥对名称：`yamaguchi-key`
3. 密钥对类型：RSA
4. 私钥文件格式：.pem
5. 点击 **"Create key pair"**
6. **重要**：自动下载的 .pem 文件要妥善保存！

#### 步骤F: 网络设置
1. 点击 **"Edit"** 旁边的网络设置
2. **Auto-assign public IP**: Enable
3. **Create security group**: 选中
4. 安全组名称：`yamaguchi-sg`
5. 描述：`Security group for Yamaguchi OpenData Platform`

#### 步骤G: 配置安全组规则
添加以下规则：

```
规则1 - SSH访问
Type: SSH
Protocol: TCP
Port range: 22
Source: My IP (推荐) 或 Anywhere (0.0.0.0/0)

规则2 - HTTP访问
Type: HTTP
Protocol: TCP
Port range: 80
Source: Anywhere (0.0.0.0/0)

规则3 - HTTPS访问
Type: HTTPS
Protocol: TCP
Port range: 443
Source: Anywhere (0.0.0.0/0)

规则4 - CKAN服务
Type: Custom TCP
Protocol: TCP
Port range: 5000
Source: Anywhere (0.0.0.0/0)
```

#### 步骤H: 配置存储
1. **Size**: 30 GiB (可根据需要调整)
2. **Volume type**: gp3 (推荐)

#### 步骤I: 启动实例
1. 在右侧摘要面板检查配置
2. 点击 **"Launch instance"**
3. 等待实例状态变为 "Running"

### **4. 连接到服务器**

#### 方法1: 使用AWS网页终端（推荐新手）
1. 在EC2实例列表中，选中您的实例
2. 点击 **"Connect"**
3. 选择 **"EC2 Instance Connect"**
4. 点击 **"Connect"**

#### 方法2: 使用SSH客户端
```bash
# Windows用户推荐使用 PuTTY 或 Git Bash
# Mac/Linux用户使用终端：

# 1. 设置密钥权限
chmod 400 ~/Downloads/yamaguchi-key.pem

# 2. 连接服务器
ssh -i ~/Downloads/yamaguchi-key.pem ubuntu@你的EC2公网IP
```

### **5. 部署应用**

连接成功后，复制粘贴以下命令：

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Git
sudo apt install -y git

# 克隆项目（替换为您的实际仓库地址）
git clone https://github.com/your-username/yamaguchi-ckan.git
# 如果没有Git仓库，可以直接上传文件

# 进入项目目录
cd yamaguchi-ckan

# 赋予脚本执行权限
chmod +x deploy-quick.sh

# 运行部署脚本
./deploy-quick.sh
```

### **6. 访问您的网站**

部署完成后：
1. 在EC2控制台复制您的实例的 **"Public IPv4 address"**
2. 在浏览器中访问：`http://您的EC2公网IP:5000`

### **7. 域名配置（可选）**

如果您有域名：

#### 7.1 配置DNS记录
在域名服务商添加A记录：
```
Host: @ 或 opendata
Type: A
Value: 您的EC2公网IP
TTL: 300
```

#### 7.2 申请SSL证书
```bash
# 在EC2实例上执行：
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## 💰 **费用预估**

### **t3.medium实例 (推荐配置)**
- 实例费用: ~$30/月
- 存储费用: ~$3/月 (30GB)
- 流量费用: ~$9/月 (100GB)
- **总计**: ~$42/月

### **t2.micro实例 (免费层)**
- 实例费用: 免费12个月
- 存储费用: ~$2/月 (20GB)
- 流量费用: 15GB免费
- **总计**: ~$2/月 (首年)

## 🔧 **常见问题**

### Q: 无法连接到服务器？
A: 检查安全组是否允许SSH (端口22)，IP地址是否正确

### Q: 网站访问不了？
A: 检查安全组是否开放5000端口，实例是否正在运行

### Q: 忘记密钥文件？
A: 无法恢复，需要重新创建实例

### Q: 如何停止收费？
A: 在EC2控制台 "Terminate" (终止) 实例

## 📞 **需要帮助？**

如果遇到问题，请提供：
1. 错误信息截图
2. EC2实例ID
3. 当前执行的步骤

我会为您提供具体的解决方案！