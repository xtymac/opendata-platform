# CKAN 数据平台一体化项目

该仓库提供一套可直接部署的 CKAN 数据平台，聚合了日本国土交通省（MLIT）和 PLATEAU 三维城市模型等数据源，集成了自定义采集插件、3D Web Map 展示、Playwright 自动化测试以及基于 OpenAI 的智能助手服务。

## 关键特性

- **完整的 CKAN 容器栈**：PostgreSQL、Solr、Redis、Datapusher、Nginx 以及自定义扩展一站式启动（`ckan-stack/docker-compose.yml`）。
- **采集插件**：内置 `mlit_harvester` 扩展，并附带独立的 `ckanext-plateau-harvester` 项目用于采集 PLATEAU Portal 数据。
- **3D 数据展示**：`cesium_viewer` 资源视图和 `/3d/` 静态发布能力，用于加载 3D Tiles 或 3DCityDB Web Map。
- **智能助手服务**：`assistant-service/` 通过 FastAPI 调用 OpenAI 模型，支持阅读服务器日志、预览 CKAN 资源等运维场景。
- **自动化测试工具链**：Playwright MCP、脚本化的首页检查（`test_ckan_groups.js`）、MLIT 采集快速检测（`quick_test.sh`）等。
- **完善文档**：包含采集指南、3D 地图集成、Playwright 使用说明与调试手册。

## 仓库结构

```text
ckan-stack/                 # Docker 化的 CKAN 运行栈与扩展挂载
  ├─ assistant-service/     # 基于 FastAPI 的 CKAN 智能助手
  ├─ extensions/            # 挂载到 CKAN 容器的定制扩展
  ├─ webmaps/               # 3D Web Map 静态资源，按 /3d/<项目>/ 发布
  ├─ scripts/               # 数据/地图发布脚本
  ├─ DCAT_HARVESTER_SETUP.md 等文档
ckanext-plateau-harvester/   # 独立的 PLATEAU 采集插件 (AGPL-3.0)
ckanext/                     # 本地开发用扩展占位目录
PLAYWRIGHT_*.md              # Playwright MCP 安装和测试说明
3D_WEB_MAP_SETUP.md          # 3D Web Map 集成指南
TESTING_GUIDE.md             # MLIT Harvester 测试步骤
quick_test.sh                # MLIT 采集插件快速自检脚本
test_ckan_groups.js          # Playwright 首页回归检查脚本
```

## 快速开始

1. **准备依赖**
   - Docker / Docker Compose v2
   - Node.js ≥ 18（运行 Playwright 工具链）
   - 可选：Python 环境（开发或调试扩展时使用）

2. **配置密钥**
   - 复制或编辑 `ckan-stack/.env`，填写 `OPENAI_API_KEY`、`CKAN_BEAKER_SESSION_SECRET`、`CKAN_APP_SECRET_KEY` 等敏感信息。
   - 若启用 SSH 工具，按需设置 `SSH_ASSISTANT_*` 变量；未使用可留空。

3. **启动 CKAN 栈**
   ```bash
   cd ckan-stack
   docker compose up -d --build
   ```
   - 首次启动会拉取 CKAN 2.11.3 镜像，并挂载自定义扩展到容器。
   - 可通过 `docker compose logs -f ckan` 观察启动过程。

4. **访问平台**
   - 默认站点 URL 在 `docker-compose.yml` 中设置为 `https://opendata.uixai.org`。
   - 本地调试可改为 `http://localhost` 并重新启动容器。
   - 使用 `docker compose exec ckan ckan -c /srv/app/ckan.ini sysadmin add admin <email>` 创建管理员账号。

5. **（可选）安装 Playwright 依赖**
   ```bash
   npm install
   npx playwright install chromium
   ```
   更多细节参考 `PLAYWRIGHT_MCP_SETUP.md`。

## 采集插件一览

### MLIT Harvester

- 已在 CKAN 容器中启用 `ckanext-mlit_harvester` 插件，API Key 通过 `mlit.api_key`（或环境变量）注入。
- 使用脚本 `./quick_test.sh` 或指南 `TESTING_GUIDE.md` 验证配置、创建采集源并运行 `docker exec ckan ckan -c /srv/app/ckan.ini harvester run`。

### PLATEAU Harvester

- 独立维护在 `ckanext-plateau-harvester/`，包含 REST 与 GraphQL 双模式采集逻辑、Mock API、配置示例与测试脚本。
- 安装方式：
  ```bash
  cd ckanext-plateau-harvester
  pip install -e .
  ```
- 启用后在 `ckan.ini` 中增加 `plateau_harvester` 插件，并按文档 `HARVEST_CONFIG_EXAMPLES.md` 配置采集源。
- `ckan-stack/DCAT_HARVESTER_SETUP.md` 与 `PLATEAU_HARVEST_GUIDE.md` 提供了连接 G 空間情報センター DCAT Catalog 的实操说明。

## 3D Web Map 与 Cesium 集成

- Nginx 将 `ckan-stack/webmaps/` 映射到 `/3d/`，可直接托管 3DCityDB 导出的静态站点。
- CKAN 内置 `ckanext-cesium_viewer`，支持对资源中的 3D Tiles ZIP 进行自动解压与在线预览。
- 通过 `ckan-stack/scripts/publish_web_map.py` 可一键创建或更新数据集、资源及 Cesium 视图，具体流程详见 `3D_WEB_MAP_SETUP.md`。

## 智能助手服务

- `ckan-stack/assistant-service/` 提供 FastAPI 应用，以 OpenAI 模型为后端，为 CKAN 管理员提供：
  - 读取容器内日志或配置文件（受 `SSH_ASSISTANT_ALLOWED_ROOTS` 限制）。
  - 解析 CKAN 数据集资源、预览 CSV。
  - 多语言问答与上下文总结。
- 服务默认监听 `8000` 端口，可通过环境变量 `OPENAI_MODEL` 指定模型。

## 自动化与测试

- **Playwright MCP**：详见 `PLAYWRIGHT_MCP_SETUP.md` 与 `PLAYWRIGHT_MCP_READY.md`，可在 Claude Desktop 中复用。
- **首页回归检查**：执行 `node test_ckan_groups.js`，会验证首页组织模块与特色分组展示，并生成 `ckan_homepage.png` 截图。
- **MLIT 快速体检**：`./quick_test.sh` 在容器内完成 API Key、插件安装、HTTP Header 设置检查。
- **Shell/脚本测试**：`test_mlit_harvester.sh`、`test_playwright_mcp.sh`、`test_import_one.py` 等脚本可根据需要运行。

## 相关文档

- `ckan-stack/DCAT_HARVESTER_SETUP.md`：DCAT 采集器配置详情
- `ckan-stack/PLATEAU_HARVEST_GUIDE.md`：PLATEAU 数据源接入全流程
- `ckan-stack/HOMEPAGE_UPDATE.md`：首页热门组织模块实现说明
- `PLAYWRIGHT_MCP_USAGE.md`：Playwright MCP 在 Claude 中的使用方法
- `ckanext-plateau-harvester/README.md`：PLATEAU 采集插件的完整说明书

## 许可信息

- `ckanext-plateau-harvester` 以 **AGPL-3.0** 许可发布，详见 `ckanext-plateau-harvester/LICENSE`。
- 其余自定义脚本与配置默认沿用 CKAN 兼容的开源许可证，如需对外发布请确认是否包含第三方依赖的限制。

欢迎根据实际部署环境调整配置，并在运行前替换示例密钥及外部服务地址。若需新增采集源、定制前端或扩展容器，请在 `ckan-stack/extensions/` 中增改对应插件并重新构建容器。
