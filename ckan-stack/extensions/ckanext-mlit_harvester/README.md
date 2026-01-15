# ckanext-mlit_harvester

Custom CKAN harvester for the [Japan MLIT Data Platform](https://www.mlit.go.jp/plate/) built on top of [`ckanext-harvest`](https://github.com/ckan/ckanext-harvest).

> **Note**
> Field mappings for both dataset metadata and resources are provided as placeholders in `ckanext/mlit_harvester/harvester.py`. Update them with the real keys returned by the MLIT Data API once the payload format is confirmed.

## Features

- Uses CKAN's three-stage harvest pipeline (gather → fetch → import).
- Supports configurable API base URL, API key, pagination, and filtering parameters.
- Reads API keys either from the harvest source configuration or from `ckan.ini` (`mlit.api_key`).
- Logs HTTP and mapping errors to aid troubleshooting.

## Installation

```bash
pip install -e /path/to/ckanext-mlit_harvester
```

Enable the plugin in `ckan.ini`:

```
ckan.plugins = harvest harvest_basket mlit_harvester
mlit.api_key = YOUR_API_KEY  # Optional when not provided per source
```

Run the database migrations for `ckanext-harvest` if you have not already done so.

## Configuring a Harvest Source

Create a new harvest source with type `mlit`. Example configuration JSON:

```json
{
  "api_base": "https://api.mlit-data.jp",
  "page_size": 100,
  "query": "status=public"
}
```

Optional parameters:

- `api_key`: API credential if it should not come from `ckan.ini`.
- `since`: ISO-8601 timestamp passed as `updated_since` when listing datasets.
- `page_size`: Page size for pagination (default `100`).
- `query`: Additional filter/query string forwarded to the MLIT API.

## Running the Harvester

Trigger a single source manually:

```bash
ckan -c /etc/ckan/ckan.ini harvester run mlit_source
```

Or configure Harvest Basket:

```
ckan.harvest.baskets = gov-data
ckan.harvest.basket.gov-data = mlit_source
ckan.harvest.source.mlit_source.type = mlit
ckan.harvest.source.mlit_source.url = https://mlit.example/catalog
```

## Development Notes

- The harvester relies on the MLIT API to expose dataset listings at `/datasets` and individual datasets at `/datasets/{id}`. Adjust the endpoints in `ckanext/mlit_harvester/harvester.py` if the real API differs.
- Update `_make_package_dict` and `_make_resources` with the actual MLIT response schema before going to production.
- Logging is verbose to help with early integration. Tune log levels once the harvester stabilises.

## License

AGPL-3.0-or-later
