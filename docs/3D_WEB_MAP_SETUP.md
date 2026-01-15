# 3D Web Map Integration Guide

This guide documents how to publish a 3DCityDB web map export to the bundled CKAN stack and expose a Cesium viewer directly within CKAN.

## 1. Prepare the Export

1. Produce a 3DCityDB web map export (static Cesium app) or a 3D Tiles package using the Importer/Exporter.
2. Copy the export folder to `ckan-stack/webmaps/<your-project>/` so it becomes available under `https://<ckan-host>/3d/<your-project>/`.
   - The sample dataset shipped with this repo lives in `ckan-stack/webmaps/dragon/`.
   - Ensure the entry page is named `index.html`; tiles should be referenced relative to this file.
   - Alternatively, attach a ZIP archive containing 3D Tiles to a CKAN resource and let the `cesium_viewer` extract it automatically. The archive is unpacked under `/3d/auto/<resource_id>/` and the first `tileset.json` is used unless you set an explicit `tileset_path` on the view.

## 2. Bring the CKAN stack up-to-date

```bash
cd ckan-stack
docker compose up -d --build
```

The nginx container is configured to serve everything under `./webmaps` at `/3d/` and the `ckan` container ships with the `cesium_viewer` resource view plugin.

## 3. Publish to CKAN

1. Create a config file modelled after `scripts/web_map_configs/dragon.json`.
2. Replace the CKAN API token and organization, then run:
   ```bash
   cd ckan-stack
   ./scripts/publish_web_map.py scripts/web_map_configs/dragon.json
   ```
   Environment variables `CKAN_URL` and `CKAN_API_KEY` can be used instead of setting them in the file.
3. The script creates or updates the dataset, its resources, uploads a thumbnail (optional) and ensures a `cesium_viewer` resource view exists.

## 4. Verify in CKAN

- Navigate to the dataset (e.g. `http://localhost/dataset/dragon-3d-tiles`).
- Open the "3D Viewer" resource to use the static web map.
- Open the "Cesium Tileset" resource, switch to the "3D View" tab; the Cesium view renders the tileset inline.

## Notes & Troubleshooting

- Content Security Policy is relaxed to allow `https://cdn.jsdelivr.net` for Cesium assets. If you host Cesium locally, adjust `CKAN__CONTENT__SECURITY__POLICY` in `docker-compose.yml` accordingly.
- CORS headers are enabled for `/3d/` so CKAN can fetch tiles directly. For external hosts, configure CORS there as well.
- To update an export, overwrite the files inside `webmaps/<project>` (or delete the corresponding `/3d/auto/<resource_id>/` directory to trigger re-extraction) and rerun `publish_web_map.py`; dataset resources are patched in place.

The same workflow applies to CityGML exports produced from your own 3DCityDB instance—swap in the new tiles/HTML package and run the publishing script.
