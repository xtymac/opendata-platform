# PLATEAU 数据采集完整指南

## 🎯 PLATEAU 数据源信息

### 官方数据源：G空間情報センター
- **网站**: https://www.geospatial.jp/ckan/
- **类型**: CKAN 实例
- **DCAT Catalog**: ✅ **可用** - `https://www.geospatial.jp/ckan/catalog.rdf`
- **API**: CKAN API v3
- **数据**: 100+ 日本城市的 3D 都市模型

## ✅ 推荐采集方法

### 方案 1：使用 DCAT RDF Harvester（推荐）⭐

这是**最简单、最完整**的方法，可以一次性采集所有 PLATEAU 数据集。

#### 通过 Web UI 创建

1. **访问 Harvest 页面**
   ```
   https://opendata.uixai.org/harvest/new
   ```

2. **填写表单**：
   ```
   URL: https://www.geospatial.jp/ckan/catalog.rdf

   Title: PLATEAU 3D都市モデル (G空間情報センター)

   Description:
   G空間情報センターが提供する日本全国100以上の都市の3D都市モデルデータ。
   CityGML形式で建築物、道路、都市計画などのデータを含む。

   Source type: DCAT RDF Harvester

   Update frequency: Weekly (または Manual)

   Configuration:
   ```
   ```json
   {
     "rdf_format": "xml",
     "clean_tags": true,
     "override_extras": false,
     "default_tags": [
       {"name": "plateau"},
       {"name": "3d-city-model"},
       {"name": "citygml"},
       {"name": "japan"}
     ],
     "default_extras": {
       "source_name": "G空間情報センター",
       "source_url": "https://www.geospatial.jp/ckan/",
       "project": "PLATEAU"
     }
   }
   ```

3. **点击 "Save"**

4. **运行采集**
   - 点击 "Reharvest" 按钮

#### 通过命令行创建

```bash
docker exec ckan ckan -c /srv/app/ckan.ini harvester source create \
  plateau-geospatial \
  https://www.geospatial.jp/ckan/catalog.rdf \
  dcat_rdf \
  true \
  "PLATEAU 3D都市モデル (G空間情報センター)" \
  "G空間情報センターが提供する日本全国の3D都市モデルデータ" \
  '{"rdf_format":"xml","clean_tags":true,"override_extras":false,"default_tags":[{"name":"plateau"},{"name":"3d-city-model"},{"name":"citygml"}],"default_extras":{"source_name":"G空間情報センター","project":"PLATEAU"}}'

# 运行采集
docker exec ckan ckan -c /srv/app/ckan.ini harvester run
```

---

### 方案 2：使用 CKAN Harvester

直接从 CKAN 实例采集（需要先安装 ckanext-harvest 的 ckan harvester）。

#### 检查是否有 CKAN Harvester

```bash
# 列出可用的 harvester 类型
docker exec ckan ckan -c /srv/app/ckan.ini harvester sources
```

如果有 `ckan` harvester 类型，可以使用：

```bash
docker exec ckan ckan -c /srv/app/ckan.ini harvester source create \
  plateau-ckan \
  https://www.geospatial.jp/ckan \
  ckan \
  true \
  "PLATEAU (CKAN)" \
  "直接从G空間情報センターCKAN采集" \
  '{"api_version": 3, "default_tags":[{"name":"plateau"}]}'
```

---

### 方案 3：使用 CKAN API 直接导入（批量）

适合一次性导入或自定义处理。

```bash
# 获取所有数据集列表
curl https://www.geospatial.jp/ckan/api/3/action/package_list > plateau_packages.json

# 获取单个数据集详情
curl https://www.geospatial.jp/ckan/api/3/action/package_show?id=plateau-13100-chiyoda-ku-2020
```

---

## 📝 配置选项详解

### DCAT RDF Harvester 配置参数

```json
{
  "rdf_format": "xml",              // RDF 格式：xml, turtle, n3, nt
  "clean_tags": true,               // 清理和规范化标签
  "override_extras": false,         // 是否覆盖现有的 extras 字段

  "default_tags": [                 // 为所有采集的数据集添加标签
    {"name": "plateau"},
    {"name": "3d-city-model"},
    {"name": "citygml"},
    {"name": "japan"}
  ],

  "default_groups": [],             // 添加到指定 group（需要先创建）

  "default_extras": {               // 添加额外的元数据字段
    "source_name": "G空間情報センター",
    "source_url": "https://www.geospatial.jp/ckan/",
    "project": "PLATEAU",
    "country": "Japan"
  },

  "remote_groups": "only_local",    // group 处理：only_local, create, none
  "remote_orgs": "only_local"       // organization 处理
}
```

### 常用配置组合

#### 1. 最小配置（快速测试）
```json
{
  "rdf_format": "xml"
}
```

#### 2. 标准配置（推荐）
```json
{
  "rdf_format": "xml",
  "clean_tags": true,
  "default_tags": [{"name": "plateau"}]
}
```

#### 3. 完整配置（生产环境）
```json
{
  "rdf_format": "xml",
  "clean_tags": true,
  "override_extras": false,
  "default_tags": [
    {"name": "plateau"},
    {"name": "3d-city-model"},
    {"name": "geospatial"}
  ],
  "default_extras": {
    "source": "G空間情報センター",
    "license_title": "CC BY 4.0"
  },
  "validators": []
}
```

---

## 🔍 按需采集特定城市

如果只想采集特定城市的数据，可以使用 CKAN API 的搜索功能。

### 方法 1：使用 CKAN API 搜索

```bash
# 搜索东京的数据
curl "https://www.geospatial.jp/ckan/api/3/action/package_search?q=東京&rows=1000"

# 搜索特定年份
curl "https://www.geospatial.jp/ckan/api/3/action/package_search?q=2023&rows=1000"

# 组合搜索
curl "https://www.geospatial.jp/ckan/api/3/action/package_search?q=東京 2023&rows=1000"
```

### 方法 2：创建多个 Harvest Source（按地区）

```bash
# 东京地区
docker exec ckan ckan -c /srv/app/ckan.ini harvester source create \
  plateau-tokyo \
  "https://www.geospatial.jp/ckan/api/3/action/package_search?q=東京&rows=1000" \
  custom \
  ...

# 大阪地区
docker exec ckan ckan -c /srv/app/ckan.ini harvester source create \
  plateau-osaka \
  "https://www.geospatial.jp/ckan/api/3/action/package_search?q=大阪&rows=1000" \
  custom \
  ...
```

---

## 🧪 测试采集

### 1. 小规模测试

建议先用少量数据测试：

```bash
# 方法 A: 使用 DCAT 但限制数量（需要在配置中添加）
# 注意：DCAT harvester 会采集整个 catalog，无法直接限制数量

# 方法 B: 手动采集单个数据集测试
curl https://www.geospatial.jp/ckan/api/3/action/package_show?id=plateau-13100-chiyoda-ku-2020 \
  | jq . > sample_dataset.json
```

### 2. 验证采集结果

```bash
# 检查采集状态
docker exec ckan ckan -c /srv/app/ckan.ini harvester jobs

# 查看特定 job 详情
docker exec ckan ckan -c /srv/app/ckan.ini harvester job-show <job-id>

# 搜索已采集的 PLATEAU 数据
docker exec ckan ckan -c /srv/app/ckan.ini search-index rebuild
curl "http://localhost:5000/api/3/action/package_search?q=plateau"
```

### 3. 检查数据质量

访问 CKAN UI 检查：
- 数据集标题是否正确
- 资源链接是否有效
- 标签是否合适
- 额外字段是否完整

---

## 🔧 故障排查

### 问题 1: 采集失败 - "Connection timeout"

**原因**: G空間情報センター的 catalog 很大（969KB RDF）

**解决方案**:
```bash
# 增加超时时间
docker exec ckan bash -c "echo 'ckanext.harvest.timeout = 300' >> /srv/app/ckan.ini"
docker compose restart ckan
```

### 问题 2: 标签格式错误

**解决方案**: 在配置中添加 `"clean_tags": true`

### 问题 3: 采集的数据集没有显示

**解决方案**:
```bash
# 重建搜索索引
docker exec ckan ckan -c /srv/app/ckan.ini search-index rebuild

# 检查数据集确实存在
docker exec ckan ckan -c /srv/app/ckan.ini package list
```

### 问题 4: 资源链接失效

**原因**: G空間情報センター的资源可能托管在外部

**解决方案**: 检查原始数据集的资源链接是否正常

---

## 📊 预期采集结果

采集完成后，您将获得：

- **数据集数量**: 约 100-200+ 个（取决于 G空間情報センター当前的数据量）
- **覆盖城市**: 日本全国主要城市（东京、大阪、横滨、名古屋等）
- **数据年份**: 2020-2024
- **数据格式**: 主要是 CityGML
- **数据类型**: 建築物、道路、都市計画、地形等

### 示例数据集

- `plateau-13100-chiyoda-ku-2023` - 東京都千代田区 2023年度
- `plateau-27100-osaka-shi-2023` - 大阪市 2023年度
- `plateau-14100-yokohama-shi-2022` - 横浜市 2022年度

---

## 🎯 下一步建议

1. **首次采集**
   - 使用 DCAT RDF Harvester 采集完整 catalog
   - 设置为 Manual 频率，先手动测试

2. **验证数据**
   - 检查至少 5-10 个数据集
   - 验证资源链接是否有效
   - 确认元数据字段正确

3. **优化配置**
   - 根据需要调整标签
   - 添加自定义 extras
   - 设置合适的更新频率

4. **定期更新**
   - 设置为 Weekly 或 Monthly 自动更新
   - 或配置 cron job 定期运行

---

## ✅ 完整操作步骤

### 快速开始（推荐）

```bash
# 1. 通过命令行创建 Harvest Source
docker exec ckan ckan -c /srv/app/ckan.ini harvester source create \
  plateau-all \
  https://www.geospatial.jp/ckan/catalog.rdf \
  dcat_rdf \
  true \
  "PLATEAU 3D都市モデル" \
  "G空間情報センター提供の3D都市モデルデータ" \
  '{"rdf_format":"xml","clean_tags":true,"default_tags":[{"name":"plateau"},{"name":"3d-city-model"}]}'

# 2. 运行采集
docker exec ckan ckan -c /srv/app/ckan.ini harvester run

# 3. 监控进度
watch -n 10 'docker exec ckan ckan -c /srv/app/ckan.ini harvester jobs'

# 4. 重建索引
docker exec ckan ckan -c /srv/app/ckan.ini search-index rebuild

# 5. 验证结果
curl "http://localhost:5000/api/3/action/package_search?q=plateau&rows=5" | jq '.result.count'
```

---

## 📚 相关资源

- **G空間情報センター**: https://www.geospatial.jp/ckan/
- **PLATEAU 官网**: https://www.mlit.go.jp/plateau/
- **PLATEAU Portal**: https://front.geospatial.jp/plateau_portal_site/
- **ckanext-dcat 文档**: https://github.com/ckan/ckanext-dcat
- **DCAT 标准**: https://www.w3.org/TR/vocab-dcat-2/

---

## 🎉 总结

**推荐 URL**:
```
https://www.geospatial.jp/ckan/catalog.rdf
```

**推荐 Source type**:
```
DCAT RDF Harvester
```

**推荐配置**:
```json
{
  "rdf_format": "xml",
  "clean_tags": true,
  "default_tags": [
    {"name": "plateau"},
    {"name": "3d-city-model"}
  ]
}
```

这样可以一次性采集所有 PLATEAU 数据！🚀
