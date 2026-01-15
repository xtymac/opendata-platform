# DCAT Harvester 设置指南

## ✅ 已完成配置

### 1. 安装的插件
已安装 `ckanext-dcat` 及以下子插件：
- `dcat` - DCAT 核心插件
- `dcat_rdf_harvester` - RDF/XML DCAT harvester
- `dcat_json_harvester` - JSON-LD DCAT harvester
- `dcat_json_interface` - JSON API 接口
- `structured_data` - 结构化数据支持

### 2. 当前插件配置
```
ckan.plugins = envvars datastore resource_proxy image_view text_view
               datatables_view geo_view simple_map datapusher harvest
               dcat dcat_rdf_harvester dcat_json_harvester
               dcat_json_interface structured_data
               mlit_harvester csv_file_harvester assistant
```

## 🎯 采集 PLATEAU Portal 数据

### PLATEAU Portal 信息
- URL: https://front.geospatial.jp/plateau_portal_site/
- 数据格式: 需要检查是否提供 DCAT catalog (RDF/XML, JSON-LD, Turtle等)

### 方法 1: 通过 Web UI 创建 Harvest Source

1. **访问 Harvest 页面**
   ```
   https://opendata.uixai.org/harvest
   ```

2. **点击 "Add Harvest Source"**

3. **填写表单**:
   - **URL**: PLATEAU Portal 的 DCAT endpoint
     - 尝试: `https://front.geospatial.jp/plateau_portal_site/catalog.rdf`
     - 或: `https://front.geospatial.jp/plateau_portal_site/catalog.json`
     - 或: `https://front.geospatial.jp/plateau_portal_site/catalog.ttl`

   - **Title**: `PLATEAU Portal`

   - **Source type**: 选择以下之一
     - `DCAT RDF Harvester` - 用于 RDF/XML 或 Turtle 格式
     - `DCAT JSON Harvester` - 用于 JSON-LD 格式

   - **Update frequency**: 选择更新频率（如 Weekly）

   - **Configuration**: (可选，JSON格式)
     ```json
     {
       "rdf_format": "xml",
       "clean_tags": true,
       "override_extras": false
     }
     ```

4. **点击 "Save"**

5. **运行采集**
   - 点击 "Reharvest" 按钮
   - 或通过命令行: `docker exec ckan ckan -c /srv/app/ckan.ini harvester run`

### 方法 2: 通过命令行创建

```bash
# RDF/XML 格式
docker exec ckan ckan -c /srv/app/ckan.ini harvester source create \
  plateau-portal \
  https://front.geospatial.jp/plateau_portal_site/catalog.rdf \
  dcat_rdf \
  true \
  "" \
  "" \
  '{"rdf_format":"xml","clean_tags":true}'

# JSON-LD 格式
docker exec ckan ckan -c /srv/app/ckan.ini harvester source create \
  plateau-portal-json \
  https://front.geospatial.jp/plateau_portal_site/catalog.json \
  dcat_json \
  true \
  "" \
  "" \
  '{"clean_tags":true}'
```

### 方法 3: 检测 PLATEAU Portal 的实际 DCAT endpoint

由于不确定 PLATEAU Portal 是否提供标准 DCAT catalog，需要先检测：

```bash
# 检查可能的 DCAT endpoints
curl -I https://front.geospatial.jp/plateau_portal_site/catalog.rdf
curl -I https://front.geospatial.jp/plateau_portal_site/catalog.json
curl -I https://front.geospatial.jp/plateau_portal_site/catalog.jsonld
curl -I https://front.geospatial.jp/plateau_portal_site/catalog.ttl
curl -I https://front.geospatial.jp/plateau_portal_site/dcat
curl -I https://front.geospatial.jp/plateau_portal_site/api/dcat

# 或者检查网站的 <link rel="alternate"> 标签
curl https://front.geospatial.jp/plateau_portal_site/ | grep -i "dcat\|catalog\|rdf"
```

## 🔍 PLATEAU 可能的采集方案

### 选项 A: 如果 PLATEAU 提供 DCAT catalog
使用上述 DCAT harvester 直接采集

### 选项 B: 如果 PLATEAU 提供 CSW (Catalog Service for Web)
使用 CSW harvester:
```bash
pip install ckanext-spatial
# 然后使用 csw_harvester
```

### 选项 C: 如果 PLATEAU 提供 OGC API - Records
可能需要自定义 harvester

### 选项 D: 如果只有网页数据
使用之前创建的自定义 PLATEAU harvester (REST/GraphQL)

## 📝 配置选项说明

### DCAT RDF Harvester 配置
```json
{
  "rdf_format": "xml",           // 或 "turtle", "n3", "nt"
  "clean_tags": true,            // 清理标签
  "override_extras": false,      // 不覆盖现有 extras
  "default_tags": [              // 添加默认标签
    {"name": "plateau"},
    {"name": "3d-city-model"}
  ],
  "default_groups": ["geo"],     // 添加到指定 group
  "default_extras": {            // 添加额外字段
    "source": "PLATEAU Portal"
  }
}
```

### DCAT JSON Harvester 配置
```json
{
  "clean_tags": true,
  "override_extras": false,
  "default_tags": [
    {"name": "plateau"}
  ]
}
```

## 🧪 测试 DCAT Harvester

### 1. 使用公开的 DCAT catalog 测试
```bash
# 测试欧盟数据门户 (data.europa.eu)
docker exec ckan ckan -c /srv/app/ckan.ini harvester source create \
  test-dcat \
  https://data.europa.eu/api/hub/store/data.json \
  dcat_json \
  true \
  "" \
  "" \
  '{}'

# 运行采集
docker exec ckan ckan -c /srv/app/ckan.ini harvester run
```

### 2. 检查采集状态
```bash
docker exec ckan ckan -c /srv/app/ckan.ini harvester sources
docker exec ckan ckan -c /srv/app/ckan.ini harvester jobs
```

## 🔧 故障排查

### 检查 DCAT 插件是否加载
```bash
docker exec ckan bash -c "grep 'ckan.plugins' /srv/app/ckan.ini"
```

### 查看可用的 harvester 类型
通过 Web UI: `/harvest/new` 页面的 "Source type" 下拉菜单

### 查看日志
```bash
docker logs ckan --tail 100 | grep -i dcat
docker logs ckan --tail 100 | grep -i harvest
```

### 重新初始化 harvest 数据库
```bash
docker exec ckan ckan -c /srv/app/ckan.ini harvester initdb
```

## 📚 DCAT 标准参考

- **DCAT Version 2**: https://www.w3.org/TR/vocab-dcat-2/
- **DCAT-AP**: https://joinup.ec.europa.eu/collection/semantic-interoperability-community-semic/solution/dcat-application-profile-data-portals-europe
- **ckanext-dcat 文档**: https://github.com/ckan/ckanext-dcat

## 🎯 下一步

1. **确定 PLATEAU Portal 的数据格式**
   - 访问网站查看是否有 API 文档
   - 检查是否提供 DCAT catalog
   - 查看开发者文档或联系支持

2. **如果没有 DCAT catalog**
   - 使用之前创建的自定义 PLATEAU harvester
   - 或开发专用的 PLATEAU Portal harvester

3. **测试采集**
   - 先用小批量数据测试
   - 验证字段映射是否正确
   - 调整配置优化结果

## ✅ 验证安装

运行以下命令验证 DCAT harvester 可用：

```bash
# 列出所有 harvest sources
docker exec ckan ckan -c /srv/app/ckan.ini harvester sources

# 检查插件
docker logs ckan 2>&1 | grep "Setting the following plugins"
```

应该看到 `dcat dcat_rdf_harvester dcat_json_harvester` 等插件已加载。

---

**完成！** 🎉 DCAT Harvester 已启用，可以通过 `/harvest/new` 创建新的采集源。
