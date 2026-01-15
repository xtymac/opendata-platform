# CKAN 3D Tiles 视图使用指南

本指南介绍如何使用 `cesium_viewer` 资源视图在 CKAN 页面中展示 PLATEAU 等 CityGML/3D Tiles 数据。该扩展支持远程或 CKAN 存储的 ZIP 资源，首次访问时会自动解压并提供 Cesium 预览。

## 1. 功能概览

- 自动识别 ZIP 资源：下载并解压到 `/3d/auto/<resource_id>/...`，后续访问直接复用解压结果。
- 支持手动覆盖 `tileset_url`，或在 ZIP 中指定 `tileset_path`（相对路径）。
- 通过 CKAN 表单直接配置，无需手动修改 JSON。
- 预置 OpenStreetMap 底图；当 3D Tiles 加载失败时可继续在地图上导航，方便排查。

## 2. 前置条件

1. CKAN 已启用 `cesium_viewer` 插件，且 `docker-compose.yml` 中挂载了 `./webmaps:/srv/app/webmaps`。
2. nginx 已将 `/3d/` 指向工作目录 `webmaps/`，并允许跨域（`Access-Control-Allow-Origin *`）。
3. CKAN 管理员账号或具备创建/编辑视图的权限。

## 3. 准备数据

### 方式 A：使用远程 ZIP（推荐）

1. 在 CKAN 资源中填写远程 ZIP URL，例如：
   `https://assets.cms.plateau.reearth.io/.../13109_shinagawa-ku_city_2024_3dtiles_mvt_1_op.zip`
2. 保存资源，保持 formato/mimetype 为 `ZIP` / `application/zip`（系统会自动识别）。

### 方式 B：上传 ZIP 到 CKAN

1. 在资源页面上传 ZIP 文档。
2. 保存后即可被自动解压。

> 无论采用哪种方式，首次打开 3D 视图时都会下载并解压。ZIP 较大时请耐心等待，可在 `docker compose logs -f ckan` 查看进度。

## 4. 创建视图

1. 打开资源页面 → **创建视图** → 选择 **3D Cesium Viewer**。
2. 填写标题（例如“Bridge LOD2 Viewer”）并保存。
3. 视图创建完成后，点击视图右上角 **Edit view** 进入配置页面。

## 5. 配置关键字段

在编辑页面中，“Title / Description” 下方会出现新的输入框：

- **Tileset URL override**（可选）：
  - 直接指定公开的 `tileset.json` 地址时填写此项；空置则使用自动解析的 URL。
- **Tileset path inside archive**（常用）：
  - 当资源是 ZIP 时，输入 `tileset.json` 在压缩包内的相对路径。
  - 示例：`13109_shinagawa-ku_city_2024_citygml_1_op_bldg_3dtiles_13109_shinagawa-ku_lod1/tileset.json`
  - 路径可通过以下方法找到：
    1. 在服务器查看解压目录：`ls ckan-stack/webmaps/auto/<resource_id>`
    2. `unzip -l` 在本地列出 ZIP 内容。
- **Allow fullscreen**：是否显示 Cesium 的全屏按钮。

点击 **Update** 保存设置。刷新“View view”页面，首次加载会解压并定位到模型范围。如果只看到底图，请继续执行第 6 节排查步骤。

## 6. 验证与排查

1. **检查网络请求**：
   - 在浏览器 DevTools → Network 中确认 `tileset.json`、`.b3dm/.glb` 请求返回 `200`。
   - 若出现 `404`，说明 `tileset_path` 填写错误或资源缺失。
2. **确认解压目录**：
   - `ls ckan-stack/webmaps/auto/<resource_id>` 查看自动解压的所有 tileset。
   - 删除目录可触发重新解压（例如更新 ZIP 后）。
3. **跨域 / 权限问题**：
   - 所有资源均通过 nginx `/3d/` 提供，默认添加 `Access-Control-Allow-Origin *`；若改动了 nginx 配置需保留该响应头。
4. **日志**：
   - `docker compose logs -f ckan` 中会显示下载和解压过程的 INFO/ERROR，便于定位失败原因。

## 7. 典型使用场景

- **单一 tileset**：仅需在 `Tileset path` 填写路径即可。
- **多专题数据包**：
  - 可针对同一资源创建多个视图，分别指向不同的 `tileset_path`（建筑、桥梁、灾害等）。
- **已有远程发布目录**：直接在 `Tileset URL override` 填写 `https://host/path/tileset.json`，可以跳过自动解压功能。

## 8. 常见问题

| 现象 | 解决方案 |
| --- | --- |
| 页面只有底图，控制台报 `Failed to load Cesium tileset` | 检查 `tileset_path` 是否正确；确认 `tileset.json` 请求返回 200。 |
| 资源视图仍显示旧数据 | 删除 `webmaps/auto/<resource_id>` 后刷新页面，触发重新解压。 |
| 视图配置字段未出现 | 浏览器缓存造成，刷新或重新进入“Edit view”；确保已重启 CKAN 容器加载最新版插件。 |
| 大文件首次加载超时 | 等待后台完成下载解压（可监控日志），或离线解压到 `webmaps/<project>` 后改用公开 URL。 |

## 9. 示例链接

- 资源：<https://opendata.uixai.org/dataset/plateau-13109-shinagawa-ku-2024-imported/resource/26b97c76-c416-410d-b0ab-c4d38b9a4819>
- 自动解压目录：`https://opendata.uixai.org/3d/auto/26b97c76-c416-410d-b0ab-c4d38b9a4819/...`

通过上述步骤，即可在 CKAN 中快速发布和浏览包含在 ZIP 中的 3D Tiles 数据。EOF
