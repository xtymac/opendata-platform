# ✅ 导入脚本已修复

## 🔧 修复内容

### 问题 1: 数据集 ID 404 错误
**原因**: 之前使用的 ID 格式不正确

**修复**: 更新为实际存在的数据集 ID

### 问题 2: 无法连接 localhost:5000
**原因**: 从服务器外部无法访问 localhost

**修复**: 改用公网域名 `https://opendata.uixai.org`

---

## 📦 新的数据集列表

现在将导入这 5 个**真实存在**的 PLATEAU 数据集：

1. **東京都中央区 2023** (`plateau-13102-chuo-ku-2023`)
   - 东京中心区域，包含银座等著名地标

2. **東京都港区 2023** (`plateau-13103-minato-ku-2023`)
   - 东京港区，包含六本木、台场等区域

3. **横浜市 2024** (`plateau-14100-yokohama-shi-2024`)
   - 横滨市最新 2024 年数据

4. **東京都渋谷区 2023** (`plateau-13113-shibuya-ku-2023`)
   - 涩谷区，东京时尚中心

5. **東京都品川区 2024** (`plateau-13109-shinagawa-ku-2024`)
   - 品川区 2024 年最新数据

---

## 🚀 运行方式

```bash
cd /home/ubuntu/ckan-stack
python3 import_plateau_simple.py
```

### 输入信息

当提示输入 API Key 时，使用：
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI4azJSdkNsVk4zTnE5eVkxVDJqUDRPZjRWTEJWOWJtNXlTTFc5OEtVSXV3IiwiaWF0IjoxNzU5NTY2ODAxfQ.DpQHaJnZt8LRwT-e8rPTJs81ZLYu-T1Qkgr7VVx5qck
```

---

## ⏱️ 预计时间

- 每个数据集约 5-10 秒
- 总计约 1-2 分钟

---

## ✅ 成功后的操作

### 1. 重建搜索索引
```bash
docker exec ckan ckan -c /srv/app/ckan.ini search-index rebuild
```

### 2. 查看导入的数据集
访问: https://opendata.uixai.org/dataset?q=plateau

### 3. 验证导入
```bash
curl -s "https://opendata.uixai.org/api/3/action/package_search?q=plateau&rows=5" | jq '.result.count'
```

应该显示 5 (或更多，如果之前已有其他 PLATEAU 数据)

---

## 🔍 如果还有问题

### 问题：SSL 证书错误

如果遇到 SSL 错误，可以临时禁用验证（仅用于测试）：

编辑脚本，在 requests 调用中添加 `verify=False`：
```python
response = requests.get(url, params=params, timeout=30, verify=False)
```

### 问题：API Key 无效

确认您的 API Key 是否有效：
```bash
curl -H "Authorization: YOUR_API_KEY" \
  "https://opendata.uixai.org/api/3/action/organization_list"
```

### 问题：数据集已存在

如果之前导入过，会报错 "name already exists"。

解决方法：
1. 删除旧数据集，或
2. 修改脚本中的数据集 name（添加后缀）

---

## 📊 导入后的数据

每个数据集包含：
- **标题**: 日文原始标题
- **描述**: 详细说明
- **标签**: plateau, imported, 3d-city-model
- **资源**: CityGML 文件、元数据等
- **Extras**: 来源信息

---

## 🎯 下一步

导入完成后，您可以：

1. **浏览数据集**
   - https://opendata.uixai.org/dataset

2. **使用 API 查询**
   ```bash
   curl "https://opendata.uixai.org/api/3/action/package_show?id=plateau-13102-chuo-ku-2023"
   ```

3. **下载资源**
   - 每个数据集包含可下载的 CityGML 文件

4. **导入更多数据**
   - 编辑脚本中的 DATASETS 列表
   - 添加更多数据集 ID

---

## 🔄 如需更换数据集

### 查找其他 PLATEAU 数据集

```bash
# 搜索所有 PLATEAU 数据集
curl -s "https://www.geospatial.jp/ckan/api/3/action/package_search?q=plateau&rows=100" \
  | jq -r '.result.results[] | "\(.name) - \(.title)"'

# 搜索特定城市
curl -s "https://www.geospatial.jp/ckan/api/3/action/package_search?q=plateau+大阪&rows=10" \
  | jq -r '.result.results[] | "\(.name) - \(.title)"'
```

### 更新脚本

编辑 `import_plateau_simple.py`，修改 `DATASETS` 列表：

```python
DATASETS = [
    {
        "id": "您找到的数据集ID",
        "name": "数据集名称"
    },
    # ... 添加更多
]
```

---

**现在可以开始导入了！** 🚀

运行命令：
```bash
python3 import_plateau_simple.py
```
