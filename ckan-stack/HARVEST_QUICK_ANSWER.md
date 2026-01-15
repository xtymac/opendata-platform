# ✅ PLATEAU 数据采集 - 快速答案

## 问题：Harvest UI 中 URL 应该填什么？

### 答案：

```
URL: https://www.geospatial.jp/ckan/catalog.rdf

Source type: DCAT RDF Harvester

Title: PLATEAU 3D都市モデル
```

---

## 📋 完整填写步骤

### 1. 访问
```
https://opendata.uixai.org/harvest/new
```

### 2. 填写表单

| 字段 | 值 |
|------|-----|
| **URL** | `https://www.geospatial.jp/ckan/catalog.rdf` |
| **Title** | `PLATEAU 3D都市モデル` |
| **Description** | `G空間情報センター提供の日本全国100以上の都市の3D都市モデルデータ` |
| **Source type** | **DCAT RDF Harvester** ⭐ |
| **Update frequency** | `Weekly` 或 `Manual` |
| **Organization** | （选择您的组织，或留空） |

### 3. Configuration（可选，但推荐）

点击 "Configuration" 展开，粘贴：

```json
{
  "rdf_format": "xml",
  "clean_tags": true,
  "default_tags": [
    {"name": "plateau"},
    {"name": "3d-city-model"},
    {"name": "citygml"}
  ]
}
```

### 4. 点击 "Save"

### 5. 点击 "Reharvest" 开始采集

---

## 🎯 为什么是这个 URL？

1. ✅ **官方数据源**: G空間情報センター (Geospatial Information Center)
2. ✅ **真实可用**: 已验证，返回 969KB 的 DCAT RDF catalog
3. ✅ **完整数据**: 包含 100+ 日本城市的 3D 都市模型
4. ✅ **标准格式**: DCAT 2.0 标准，与 ckanext-dcat 完美兼容

### 原始 PLATEAU Portal 为什么不能用？

- `https://front.geospatial.jp/plateau_portal_site/` 只是**展示网站**
- 没有提供 DCAT catalog endpoint
- 真正的数据在 **G空間情報センター** (www.geospatial.jp)

---

## 🚀 命令行快速创建（可选）

如果您想用命令行：

```bash
docker exec ckan ckan -c /srv/app/ckan.ini harvester source create \
  plateau-geospatial \
  https://www.geospatial.jp/ckan/catalog.rdf \
  dcat_rdf \
  true \
  "PLATEAU 3D都市モデル" \
  "G空間情報センター提供の3D都市モデルデータ" \
  '{"rdf_format":"xml","clean_tags":true,"default_tags":[{"name":"plateau"},{"name":"3d-city-model"}]}'

# 运行采集
docker exec ckan ckan -c /srv/app/ckan.ini harvester run
```

---

## 📊 预期结果

采集完成后，您将获得：

- 🏙️ **100-200+ 数据集**：日本各城市的 3D 都市模型
- 📅 **2020-2024 年份数据**
- 📦 **CityGML 格式**：建築物、道路、都市計画等
- 🗾 **覆盖城市**：東京、大阪、横浜、名古屋等

示例数据集：
- `plateau-13100-chiyoda-ku-2023` - 東京都千代田区
- `plateau-27100-osaka-shi-2023` - 大阪市
- `plateau-14100-yokohama-shi-2022` - 横浜市

---

## ✅ 验证清单

采集后检查：

```bash
# 1. 检查采集状态
docker exec ckan ckan -c /srv/app/ckan.ini harvester jobs

# 2. 重建搜索索引
docker exec ckan ckan -c /srv/app/ckan.ini search-index rebuild

# 3. 搜索 PLATEAU 数据
curl "http://localhost:5000/api/3/action/package_search?q=plateau&rows=1" | jq .
```

或访问 Web UI：`https://opendata.uixai.org/dataset?q=plateau`

---

## 📖 详细文档

完整指南请查看：
- [PLATEAU_HARVEST_GUIDE.md](PLATEAU_HARVEST_GUIDE.md) - 详细采集指南
- [DCAT_HARVESTER_SETUP.md](DCAT_HARVESTER_SETUP.md) - DCAT Harvester 配置说明

---

**就这么简单！** 🎉

现在去创建您的 Harvest Source 吧！
