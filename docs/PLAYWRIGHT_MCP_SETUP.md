# Playwright MCP 安装和配置指南

## 已完成的安装步骤

### 1. 安装 Playwright 浏览器
```bash
npx playwright install chromium
```
- ✅ Chromium 140.0.7339.186 已下载
- ✅ FFMPEG 已安装
- ✅ Headless Shell 已安装

### 2. 安装系统依赖
```bash
sudo npx playwright install-deps chromium
```
- ✅ 75 个系统包已安装
- ✅ 包括 libatk, libcups, libcairo, libpango 等

### 3. Playwright MCP 配置

已创建配置文件在：`~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--browser",
        "chromium",
        "--headless"
      ]
    }
  }
}
```

## 如何使用

### 在 Claude Desktop 中使用

1. 打开 Claude Desktop 设置
2. 找到 MCP Servers 配置
3. 添加上述配置
4. 重启 Claude Desktop

### 命令行测试

#### 启动 Playwright MCP 服务器（Headless 模式）
```bash
npx @playwright/mcp@latest --browser chromium --headless
```

#### 启动 Playwright MCP 服务器（Headed 模式，可见浏览器）
```bash
npx @playwright/mcp@latest --browser chromium
```

#### 测试 CKAN 首页（使用特定配置）
```bash
npx @playwright/mcp@latest \
  --browser chromium \
  --headless \
  --allowed-hosts opendata.uixai.org \
  --viewport-size 1920x1080
```

## 可用选项

### 浏览器选择
- `--browser chromium` - 使用 Chromium
- `--browser firefox` - 使用 Firefox（需要先安装）
- `--browser webkit` - 使用 WebKit（需要先安装）

### 显示模式
- `--headless` - 无头模式（后台运行）
- 不加 `--headless` - 有头模式（显示浏览器窗口）

### 安全和权限
- `--allowed-hosts <hosts>` - 允许访问的主机列表
- `--grant-permissions <perms>` - 授予的浏览器权限
- `--ignore-https-errors` - 忽略 HTTPS 错误

### 会话保存
- `--save-trace` - 保存 Playwright Trace
- `--save-video 1920x1080` - 保存视频录制
- `--save-session` - 保存会话状态

## 测试用例示例

### 测试访问 CKAN 首页
可以使用 Playwright MCP 来：

1. 访问 https://opendata.uixai.org/
2. 验证页面标题
3. 检查组织显示
4. 截取页面截图
5. 检查 JavaScript 是否正确执行

### 验证组织显示功能
可以测试：
- "最近収集したデータ" 标题是否显示
- "データがある組織を2つ見つけました" 文字是否正确
- "すべての組織を表示" 按钮是否可点击
- 两个组织卡片是否正确显示

## 文件位置

- **配置文件**: `~/.config/claude/claude_desktop_config.json`
- **浏览器缓存**: `~/.cache/ms-playwright/`
- **Chromium**: `~/.cache/ms-playwright/chromium-1193/`

## 版本信息

- **Playwright MCP**: 0.0.41
- **Chromium**: 140.0.7339.186
- **Node.js**: v18.20.8
- **npx**: 10.8.2

## 下一步

要在 Claude Desktop 中使用 Playwright MCP：

1. 将配置添加到 Claude Desktop
2. 重启应用
3. 在对话中可以使用浏览器自动化功能
4. 可以访问网页、截图、执行 JavaScript 等

## 注意事项

- Headless 模式性能更好，适合自动化测试
- Headed 模式可以看到浏览器操作，适合调试
- 使用 `--save-trace` 可以后续在 Playwright Trace Viewer 中查看执行过程
