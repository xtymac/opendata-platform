# Imaginary Cities Data Importer

成功导入虚构城市数据到 CKAN 平台！

## 导入结果

### 组织 (Organization)
- **名称**: imaginary-cities
- **标题**: Imaginary Cities
- **包含数据集**: 3个

### 数据集 (Datasets)

#### 1. imaginary-cities-country (国家数据)
- **标题**: Imaginary Cities - Countries
- **内容**: 2个虚构国家 (Utopia, Arcadia)
- **字段**:
  - id: 唯一标识符
  - name: 国家名称
  - capital: 首都
  - area: 面积 (平方公里)
  - population: 人口
  - gdp: GDP
  - boundary: GeoJSON格式的地理边界
- **资源**:
  - countries_data.json (JSON格式)
  - countries_data.csv (CSV格式)

#### 2. imaginary-cities-city (城市数据)
- **标题**: Imaginary Cities - Cities
- **内容**: 8个著名虚构城市
  - Atlantis (亚特兰蒂斯)
  - Metropolis (大都会)
  - Eldorado (黄金国)
  - Gotham (哥谭市)
  - Wakanda (瓦坎达)
  - Rapture (极乐城)
  - Zion (锡安)
  - Midgar (米德加)
- **字段**:
  - id: 唯一标识符
  - name: 城市名称
  - description: 描述
  - area: 面积
  - population: 人口
  - gdp: GDP
  - founding_year: 建立年份
- **资源**:
  - cities_data.json (JSON格式)
  - cities_data.csv (CSV格式)

#### 3. imaginary-cities-assets (图片资源)
- **标题**: Imaginary Cities - Image Assets
- **内容**: 3个图片资源
- **字段**:
  - type: 资源类型
  - id: 唯一标识符
  - url: 图片URL
  - contentType: 内容类型 (image/avif, image/jpeg)
- **资源**:
  - assets_data.json (JSON格式)
  - assets_data.csv (CSV格式)

## 访问数据

### Web界面
访问: https://opendata.uixai.org/organization/imaginary-cities

### API访问

#### 获取组织信息
```bash
curl http://localhost/api/3/action/organization_show?id=imaginary-cities
```

#### 获取国家数据集
```bash
curl http://localhost/api/3/action/package_show?id=imaginary-cities-country
```

#### 获取城市数据集
```bash
curl http://localhost/api/3/action/package_show?id=imaginary-cities-city
```

#### 获取资源数据集
```bash
curl http://localhost/api/3/action/package_show?id=imaginary-cities-assets
```

## 重新导入数据

如果需要更新数据，只需重新运行导入脚本：

```bash
python3 /home/ubuntu/imaginary_cities_importer.py
```

脚本会自动：
- 检测已存在的数据集
- 更新而不是重复创建
- 添加新资源

## 配置文件

配置信息存储在 [config.json](config.json):
- CKAN URL
- API密钥
- Re:Earth API端点

## 数据源

所有数据来自 Re:Earth CMS API:
- Country: https://api.cms.reearth.io/api/p/xgtbhkfgwv/imaginary-cities/country
- City: https://api.cms.reearth.io/api/p/xgtbhkfgwv/imaginary-cities/city
- Assets: https://api.cms.reearth.io/api/p/xgtbhkfgwv/imaginary-cities/assets

## 文件说明

- [imaginary_cities_importer.py](imaginary_cities_importer.py) - 主导入脚本
- [config.json](config.json) - 配置文件
- IMAGINARY_CITIES_README.md - 本说明文档

## 定期同步 (可选)

如果需要定期从 Re:Earth API 同步数据，可以设置 cron 任务：

```bash
# 编辑 crontab
crontab -e

# 添加以下行 (每天凌晨2点运行)
0 2 * * * /usr/bin/python3 /home/ubuntu/imaginary_cities_importer.py >> /home/ubuntu/import.log 2>&1
```

## 许可证

所有数据集使用 Creative Commons Attribution (CC-BY) 许可证。

## 技术细节

- **CKAN版本**: 2.11.3
- **Python版本**: 3.10
- **数据格式**: JSON, CSV
- **API认证**: JWT Token
- **组织**: imaginary-cities

---

导入完成时间: 2025-11-18
