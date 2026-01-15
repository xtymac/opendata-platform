# Playwright MCP 测试结果报告

## 测试日期
2025-10-04

## 测试目标
使用 Playwright MCP 自动化测试 CKAN 首页的 Groups 显示功能

## 测试工具
- **Playwright MCP**: v0.0.41
- **Chromium**: 140.0.7339.186
- **测试脚本**: `/home/ubuntu/test_ckan_groups.js`
- **截图**: `/home/ubuntu/ckan_homepage.png`

## 测试结果

### ✅ 成功项

1. **Playwright MCP 安装和配置**
   - ✅ Chromium 浏览器已安装
   - ✅ 系统依赖已安装（75个包）
   - ✅ 可以正常访问和测试网站

2. **自定义组织区域**
   - ✅ 标题显示正确："最近収集したデータ"
   - ✅ 副标题显示正确："データがある組織を2つ見つけました"
   - ✅ 显示 2 个组织：
     - G空間情報センター - 5 个数据集
     - U.S. Geological Survey - 1 个数据集
   - ✅ "すべての組織を表示" 按钮正常

3. **JavaScript 功能**
   - ✅ 首页 JavaScript 正常执行
   - ✅ API 调用成功
   - ✅ DOM 动态插入成功

### ❌ 问题项

1. **Featured Groups 配置问题**
   - ❌ 配置了 `ckan.featured_groups = travel bousai-anzen`
   - ❌ 但首页只显示 1 个 Group（観光/Travel）
   - ❌ 第二个 Group（防災・防犯/bousai-anzen）未显示

## 问题根因分析

### 1. 配置读取问题
```bash
# 环境变量已设置
CKAN__FEATURED_GROUPS=travel bousai-anzen

# ckan.ini 中也已设置
ckan.featured_groups = travel bousai-anzen

# 但运行时 config.get() 返回 None
```

### 2. Helper 函数限制
```python
def get_featured_groups(count: int = 1) -> list[dict[str, Any]]:
    '''Returns a list of favourite group'''
    config_groups = config.get('ckan.featured_groups')  # 返回 None
    groups = featured_group_org(get_action='group_show',
                                list_action='group_list',
                                count=count,  # 默认值是 1
                                items=config_groups)
    return groups
```

**问题**：
- `count=1` 表示只返回 1 个 group
- `config_groups` 为 None 时，函数从所有 groups 中随机取 1 个

### 3. 模板限制
```jinja2
{% set groups = h.get_featured_groups() %}  {# count 默认是 1 #}

{% for group in groups %}
  <div class="card box">
    {% snippet 'snippets/group_item.html', group=group %}
  </div>
{% endfor %}
```

## 当前首页状态

### Groups 区域（左侧）
- 显示 1 个：**観光** (travel)

### Organizations 区域（通过 JavaScript 动态添加）
- 显示 2 个：
  1. **G空間情報センター** - 5 datasets
  2. **U.S. Geological Survey** - 1 dataset

## 解决方案建议

### 方案 1：修改核心模板（最简单但不推荐）
```jinja2
{# /srv/app/src/ckan/ckan/templates/home/snippets/featured_group.html #}
{% set groups = h.get_featured_groups(count=10) %}
```

**优点**：简单直接
**缺点**：修改核心文件，升级时会丢失

### 方案 2：创建自定义插件 Helper（推荐）
在 ckanext-assistant 中添加自定义 helper：

```python
def get_all_featured_groups():
    '''Get all configured featured groups'''
    import ckan.plugins.toolkit as tk
    config_groups_str = tk.config.get('ckan.featured_groups', '')
    if config_groups_str:
        group_names = config_groups_str.split()
        groups = []
        for name in group_names:
            try:
                group = tk.get_action('group_show')(
                    {'ignore_auth': True},
                    {'id': name}
                )
                groups.append(group)
            except:
                pass
        return groups
    return []
```

### 方案 3：直接在 docker-compose.yml 中设置显示数量
如果 CKAN 支持环境变量配置 featured groups 数量：
```yaml
CKAN__FEATURED_GROUPS__COUNT: 10
```

## 测试文件位置

- **测试脚本**: `/home/ubuntu/test_ckan_groups.js`
- **测试结果截图**: `/home/ubuntu/ckan_homepage.png`
- **Playwright 配置**: `~/.config/claude/claude_desktop_config.json`
- **详细安装文档**: `/home/ubuntu/PLAYWRIGHT_MCP_SETUP.md`

## 总结

✅ **Playwright MCP 测试成功**：可以自动化测试网页，检测 DOM 元素，验证功能

✅ **自定义组织显示成功**：JavaScript 动态加载的组织区域工作正常

⚠️ **Featured Groups 显示不完整**：配置问题导致只显示 1 个而不是 2 个 groups

## 下一步建议

1. 如果只需要显示组织，当前的 JavaScript 方案已经完美工作
2. 如果需要显示 2 个 Groups，建议使用方案 2 创建自定义 helper
3. 或者接受当前状态（1 个 Group + 2 个自定义组织显示）
