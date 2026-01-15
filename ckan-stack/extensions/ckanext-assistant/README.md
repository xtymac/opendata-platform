# ckanext-assistant

Provides an AI assistant widget for CKAN portals. The extension injects a floating chat panel and proxies chat requests to an external assistant service running inside the CKAN stack.

## Configuration

Add `assistant` to `ckan.plugins` and configure `ckanext.assistant.service_url` if the backend service is not reachable at `http://assistant:8000`.

### Automatic resource views

When new resources are created (including those imported via harvesters) the extension can automatically add resource views based on the detected file format. A default mapping is shipped:

- `csv`, `tsv` → `recline_view`
- `json`, `txt` → `text_view`
- `geojson`, `kml`, `kmz` → `geo_view`
- `png`, `jpg`, `jpeg`, `gif` → `image_view`

You can override or extend the mapping in your CKAN configuration:

```
# Example: add a datatables view for CSV and enable map view for zipped shapefiles
ckanext.assistant.auto_view_map.csv = recline_view,datatables_view
ckanext.assistant.auto_view_map.zip = geo_view
```

Set `ckanext.assistant.auto_view_user` if you need a specific CKAN user to own the auto-created views. By default the plugin reuses the acting user or falls back to `harvest`.
