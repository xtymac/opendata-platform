# 首页显示最近采集的组织

## ✅ 已完成配置

已在 CKAN 首页添加"最近采集的数据组织"模块，显示最近的 2 个组织。

## 📁 修改的文件

```
/home/ubuntu/ckan-stack/extensions/ckanext-assistant/ckanext/assistant/templates/home/index.html
```

## 🎨 显示内容

首页右侧栏会显示：

1. **标题**: "最近采集的数据组织"
2. **组织列表**: 显示最近的 2 个组织
   - 组织图标/首字母
   - 组织名称（可点击）
   - 组织描述（前 80 字符）
   - 数据集数量
3. **查看更多按钮**: 链接到完整的组织列表页面

## 📊 显示的组织

当前会显示：
- **g-space** (G空間情報センター) - PLATEAU 数据
- **其他最近更新的组织**

按 `metadata_modified desc` 排序，始终显示最近更新的组织。

## 🔄 如何工作

模板使用 CKAN 的 `organization_list` action:

```jinja2
{% set organizations = h.get_action('organization_list',
    {'all_fields': True, 'sort': 'metadata_modified desc', 'limit': 2}) %}
```

- `all_fields`: 获取完整组织信息
- `sort`: 按最后修改时间降序排列
- `limit`: 只显示 2 个组织

## 🎯 查看效果

访问: https://opendata.uixai.org/

在首页右侧应该能看到"最近采集的数据组织"模块。

## ⚙️ 自定义选项

### 1. 修改显示数量

编辑 `/home/ubuntu/ckan-stack/extensions/ckanext-assistant/ckanext/assistant/templates/home/index.html`

修改 `limit: 2` 为其他数字：

```jinja2
{% set organizations = h.get_action('organization_list',
    {'all_fields': True, 'sort': 'metadata_modified desc', 'limit': 3}) %}
```

### 2. 修改排序方式

可用的排序选项：
- `'metadata_modified desc'` - 最近更新（当前）
- `'metadata_created desc'` - 最近创建
- `'package_count desc'` - 数据集数量最多
- `'title asc'` - 按名称排序

### 3. 修改样式

在模板中可以调整：
- 图标大小：`width: 50px; height: 50px`
- 描述长度：`extract_length=80`
- 边距、颜色等 CSS

### 4. 添加过滤条件

只显示特定组织，例如只显示包含 "plateau" 的组织：

```jinja2
{% set organizations = h.get_action('organization_list',
    {'all_fields': True, 'sort': 'metadata_modified desc'}) %}
{% set plateau_orgs = [] %}
{% for org in organizations %}
  {% if 'plateau' in org.name.lower() or 'plateau' in (org.title or '').lower() %}
    {% set _ = plateau_orgs.append(org) %}
  {% endif %}
{% endfor %}
{% set organizations = plateau_orgs[:2] %}
```

## 🔄 更新模板后

每次修改模板后，重启 CKAN：

```bash
cd /home/ubuntu/ckan-stack
docker compose restart ckan
```

或清除 CKAN 缓存：

```bash
docker exec ckan ckan -c /srv/app/ckan.ini cache clear
```

## 📋 完整模板位置

```
extensions/
└── ckanext-assistant/
    └── ckanext/
        └── assistant/
            ├── plugin.py              ← 已配置 add_template_directory
            └── templates/
                └── home/
                    └── index.html     ← 首页模板覆盖
```

## 🎨 模板继承结构

```
CKAN 核心模板
  └── ckan/templates/home/index.html
      └── ckanext-assistant 覆盖
          └── 添加 "最近采集的数据组织" 模块
```

使用 `{% ckan_extends %}` 继承原始模板，只覆盖 `secondary_content` 块。

## 🔍 故障排查

### 问题：首页没有显示组织模块

**检查**:
1. 确认模板文件已创建
2. 确认 CKAN 已重启
3. 检查浏览器缓存（Ctrl+Shift+R 强制刷新）

```bash
# 检查模板文件
ls -la /home/ubuntu/ckan-stack/extensions/ckanext-assistant/ckanext/assistant/templates/home/

# 重启 CKAN
cd /home/ubuntu/ckan-stack && docker compose restart ckan

# 查看日志
docker logs ckan --tail 50 | grep -i template
```

### 问题：显示为空

可能原因：
- 没有组织数据
- 组织的 `metadata_modified` 字段为空

**解决**:
```bash
# 检查组织列表
curl -s "https://opendata.uixai.org/api/3/action/organization_list?all_fields=true" | jq .
```

### 问题：样式错乱

CKAN 使用 Bootstrap 2.x，确保使用兼容的类名：
- `btn btn-primary` 而不是 `btn-primary`
- `media-item` 而不是 `card`

## 💡 扩展建议

### 1. 添加组织图标

为组织添加图标：
1. 登录 CKAN
2. 访问组织页面
3. 点击 "Manage"
4. 上传图标图片

### 2. 显示最新数据集

在首页也显示最新数据集：

```jinja2
<div class="module module-narrow module-shallow">
  <h2 class="module-heading">
    <i class="fa fa-database"></i>
    最新数据集
  </h2>
  <div class="module-content">
    {% set packages = h.get_action('package_search',
        {'sort': 'metadata_modified desc', 'rows': 5}) %}
    {% for pkg in packages.results %}
      <div class="dataset-item">
        <a href="{{ h.url_for('dataset.read', id=pkg.name) }}">
          {{ pkg.title }}
        </a>
      </div>
    {% endfor %}
  </div>
</div>
```

### 3. 添加统计数字

显示总体统计：

```jinja2
{% set stats = h.get_action('package_search', {'rows': 0}) %}
<div class="stats">
  <strong>{{ stats.count }}</strong> 数据集
</div>
```

---

## ✅ 完成

现在您的 CKAN 首页会显示最近采集的 2 个组织！

访问查看: https://opendata.uixai.org/

如需调整显示内容或样式，编辑模板文件并重启 CKAN 即可。
