# 首页组织显示 - 更新说明

## 🔄 问题与解决

### 原始问题
所有组织的 `metadata_modified` 字段为 null，导致无法按修改时间排序。

### 解决方案
改为按 `package_count`（数据集数量）降序排序，显示数据集最多的两个组织。

## ✅ 当前配置

### 显示逻辑
```jinja2
{# 获取所有组织并按数据集数量排序 #}
{% set all_orgs = h.get_action('organization_list', {'all_fields': True}) %}
{% set sorted_orgs = all_orgs|sort(attribute='package_count', reverse=True) %}
{% set organizations = sorted_orgs[:2] %}
```

### 显示顺序（按数据集数量）
1. **g-space** (G空間情報センター) - 5 个数据集
2. **U.S. Geological Survey** - 1 个数据集

### 标题变更
- 原标题：❌ "最近采集的数据组织"
- 新标题：✅ "热门数据组织"

## 🎯 查看效果

访问首页：https://opendata.uixai.org/

应该在右侧看到：
```
┌─────────────────────────┐
│ 热门数据组织             │
├─────────────────────────┤
│ 🔷 G空間情報センター     │
│    📊 5 数据集           │
├─────────────────────────┤
│ 🔷 U.S. Geological...   │
│    📊 1 数据集           │
├─────────────────────────┤
│  [查看所有组织 →]       │
└─────────────────────────┘
```

## 🔧 故障排查

### 如果还是只看到一个组织

1. **强制刷新浏览器**
   ```
   Windows/Linux: Ctrl + Shift + R
   Mac: Cmd + Shift + R
   ```

2. **清除 CKAN 缓存**
   ```bash
   docker exec ckan ckan -c /srv/app/ckan.ini cache clear
   ```

3. **检查模板文件**
   ```bash
   cat /home/ubuntu/ckan-stack/extensions/ckanext-assistant/ckanext/assistant/templates/home/index.html | head -20
   ```

4. **验证组织数据**
   ```bash
   curl -s "https://opendata.uixai.org/api/3/action/organization_list?all_fields=true" | jq '.result[] | {name, title, package_count}'
   ```

5. **检查 CKAN 日志**
   ```bash
   docker logs ckan --tail 50 | grep -i template
   ```

## 📝 其他排序选项

### 选项 1: 按名称排序
```jinja2
{% set sorted_orgs = all_orgs|sort(attribute='title') %}
```

### 选项 2: 只显示有数据的组织
```jinja2
{% set orgs_with_data = all_orgs|selectattr('package_count', 'gt', 0)|list %}
{% set sorted_orgs = orgs_with_data|sort(attribute='package_count', reverse=True) %}
```

### 选项 3: 显示特定组织
```jinja2
{% set featured_orgs = ['g-space', 'u-s-geological-survey'] %}
{% set organizations = [] %}
{% for org in all_orgs %}
  {% if org.name in featured_orgs %}
    {% set _ = organizations.append(org) %}
  {% endif %}
{% endfor %}
```

## 🎨 显示更多组织

修改显示数量：
```jinja2
{% set organizations = sorted_orgs[:3] %}  {# 显示 3 个 #}
```

## 📊 显示所有有数据的组织

如果想显示所有有数据集的组织：
```jinja2
{% set organizations = all_orgs|selectattr('package_count', 'gt', 0)|list %}
{% set organizations = organizations|sort(attribute='package_count', reverse=True) %}
```

然后移除 `[:2]` 限制。

## 🔄 修改后的步骤

1. 编辑模板文件
2. 重启 CKAN：`docker compose restart ckan`
3. 强制刷新浏览器：Ctrl+Shift+R

## ✅ 验证成功

成功的标志：
- ✅ 首页右侧显示"热门数据组织"模块
- ✅ 显示 2 个组织（g-space 和 U.S. Geological Survey）
- ✅ g-space 显示 5 个数据集
- ✅ 每个组织可点击查看详情

## 💡 扩展建议

### 添加组织描述

为组织添加描述，会自动显示在首页：

1. 访问：https://opendata.uixai.org/organization/g-space
2. 点击 "Manage"
3. 编辑 "Description" 字段
4. 保存

描述会显示在组织卡片中（前 80 字符）。

### 添加组织图标

1. 访问组织页面
2. 点击 "Manage"
3. 上传图标图片
4. 保存

图标会替代首字母圆圈显示。

---

## 📅 更新日志

### 2025-10-04
- 修改排序逻辑：从 `metadata_modified` 改为 `package_count`
- 更新标题：从 "最近采集的数据组织" 改为 "热门数据组织"
- 原因：所有组织的 metadata_modified 为 null

---

现在刷新首页，应该能看到两个组织了！🎉
