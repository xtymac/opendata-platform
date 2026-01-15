# 地图可视化使用指南

## 🗺️ 已启用的地图功能

您的 CKAN 平台现在可以在地图上可视化地理数据！

### 可用的地图插件

1. **GeoView** (geo_view) - 基础地图查看器
2. **Simple Map** (simple_map) - 简单地图插件
3. **Cesium Viewer** (cesium_viewer) - Cesium 3D地球查看器

### Country 数据集的地图视图

**数据集**: imaginary-cities-country
**资源**: countries_boundaries.geojson
**视图**: Map viewer (自动创建)

#### 访问地图视图

1. **Web界面访问**:
   ```
   https://opendata.uixai.org/dataset/imaginary-cities-country
   ```

2. **点击 GeoJSON 资源** (countries_boundaries.geojson)

3. **选择 "Map viewer" 标签页** - 您将看到虚构国家的地理边界显示在地图上

#### 地图上可以看到什么

- **Utopia** (乌托邦): 位于坐标 [139.7-139.8, 35.6-35.7] 的多边形边界
- **Arcadia** (阿卡迪亚): 位于坐标 [140-140.2, 36-36.3] 的多边形边界

点击每个多边形可以看到国家的属性信息：
- 名称 (name)
- 首都 (capital)
- 面积 (area)
- 人口 (population)
- GDP

### GeoJSON 数据结构

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[...]]
      },
      "properties": {
        "name": "Utopia",
        "capital": "Eden",
        "area": 100000,
        "population": 5000000,
        "gdp": 750000
      }
    }
  ]
}
```

### API 访问

#### 获取 GeoJSON 数据
```bash
curl -O "https://opendata.uixai.org/dataset/0672fadf-4111-4152-9309-eb3c6e2961a6/resource/10d6bed8-9a83-4939-af5b-190cbff5ea09/download/countries_boundaries.geojson"
```

#### 查看资源视图信息
```bash
curl "http://localhost/api/3/action/resource_view_list?id=10d6bed8-9a83-4939-af5b-190cbff5ea09"
```

### 其他格式的地图可视化支持

CKAN 的地图插件支持以下格式：

- ✅ **GeoJSON** (.geojson, .json) - 已使用
- ✅ **KML** (.kml) - Google Earth 格式
- ✅ **WMS** - Web Map Service
- ✅ **WFS** - Web Feature Service

### 为其他数据集添加地图视图

如果您想为其他数据集添加地图视图，可以：

1. **准备 GeoJSON 数据**
2. **运行添加脚本**:
   ```bash
   python3 /home/ubuntu/add_geojson_resources.py
   ```

或手动创建 GeoJSON FeatureCollection 并上传到 CKAN。

### 地图视图的优势

🌍 **直观展示**: 地理数据一目了然
🖱️ **交互式**: 可以缩放、平移、点击查看详情
📊 **属性显示**: 点击要素显示完整属性信息
🔗 **可嵌入**: 地图视图可以嵌入到其他网页
📱 **响应式**: 支持移动设备访问

### 技术细节

**插件版本**:
- ckanext-geoview: 0.2.2
- ckanext-simplemap: 0.1.0
- ckanext-cesium-viewer: 0.1.0
- geojson: 3.1.0

**地图库**: Leaflet.js (通过 geoview)

**坐标系统**: WGS84 (EPSG:4326)

### 相关脚本

- [add_geojson_resources.py](add_geojson_resources.py) - 添加 GeoJSON 资源脚本
- [imaginary_cities_importer.py](imaginary_cities_importer.py) - 主数据导入脚本

---

**更新时间**: 2025-11-18
**地图视图状态**: ✅ 已启用并正常工作
