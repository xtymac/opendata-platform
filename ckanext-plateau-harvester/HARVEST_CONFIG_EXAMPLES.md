# PLATEAU Harvester Configuration Examples

Complete examples for creating Harvest Sources with different configurations.

## 📝 Basic REST API Configuration

### Configuration JSON

```json
{
  "api_base": "http://mockapi:8088/api/v1/",
  "mode": "rest",
  "list_path": "datasets",
  "detail_path": "datasets/{id}",
  "page_size": 100,
  "owner_org": "plateau-data"
}
```

### Create via Web UI

1. Navigate to: `http://your-ckan/harvest`
2. Click **"Add Harvest Source"**
3. Fill in:
   - **URL**: `http://mockapi:8088/api/v1/`
   - **Title**: `PLATEAU Mock API`
   - **Source type**: `PLATEAU / 3D都市モデル`
   - **Organization**: Select your organization
   - **Configuration**: Paste the JSON above

### Create via CLI

```bash
ckan -c /etc/ckan/ckan.ini harvester source create \
  name=plateau-mock \
  title="PLATEAU Mock API" \
  url=http://mockapi:8088/api/v1/ \
  type=plateau \
  config='{"api_base":"http://mockapi:8088/api/v1/","mode":"rest","list_path":"datasets","detail_path":"datasets/{id}","page_size":100,"owner_org":"plateau-data"}'
```

### Create via API

```bash
curl -X POST http://localhost:5000/api/3/action/harvest_source_create \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "plateau-mock",
    "title": "PLATEAU Mock API",
    "url": "http://mockapi:8088/api/v1/",
    "source_type": "plateau",
    "config": "{\"api_base\":\"http://mockapi:8088/api/v1/\",\"mode\":\"rest\",\"list_path\":\"datasets\",\"detail_path\":\"datasets/{id}\",\"page_size\":100,\"owner_org\":\"plateau-data\"}"
  }'
```

---

## 🔐 REST API with Authentication

### Configuration JSON

```json
{
  "api_base": "https://api.plateau.example.com/v1/",
  "api_key": "your-api-key-here",
  "mode": "rest",
  "list_path": "datasets",
  "detail_path": "datasets/{id}",
  "page_size": 50,
  "owner_org": "plateau-data",
  "extra_headers": {
    "User-Agent": "CKAN-PLATEAU-Harvester/0.1",
    "X-Custom-Header": "value"
  }
}
```

---

## 🔍 REST API with Search Filter

### Configuration JSON

```json
{
  "api_base": "https://api.plateau.example.com/v1/",
  "mode": "rest",
  "list_path": "datasets",
  "detail_path": "datasets/{id}",
  "search": "3D都市モデル",
  "page_size": 100,
  "owner_org": "plateau-data"
}
```

This will append `?q=3D都市モデル` to the list endpoint.

---

## 🌐 GraphQL API Configuration

### Configuration JSON

```json
{
  "api_base": "https://graphql.plateau.example.com/",
  "mode": "graphql",
  "graph_path": "graphql",
  "list_query": "query($q:String,$after:String){ datasets(query:$q, after:$after, first:100){ nodes{ id title updatedAt } pageInfo{ endCursor hasNextPage }}}",
  "detail_query": "query($id:ID!){ dataset(id:$id){ id title description city prefecture year modelType themes updatedAt resources{ url name format size }}}",
  "search": "東京",
  "owner_org": "plateau-data"
}
```

### GraphQL Queries Explained

**List Query** (for gather stage):
```graphql
query($q: String, $after: String) {
  datasets(query: $q, after: $after, first: 100) {
    nodes {
      id
      title
      updatedAt
    }
    pageInfo {
      endCursor
      hasNextPage
    }
  }
}
```

**Detail Query** (for fetch stage):
```graphql
query($id: ID!) {
  dataset(id: $id) {
    id
    title
    description
    city
    prefecture
    year
    modelType
    themes
    updatedAt
    resources {
      url
      name
      format
      size
    }
  }
}
```

---

## 🌍 Real PLATEAU API Example

### For Official PLATEAU Catalog (Hypothetical)

```json
{
  "api_base": "https://www.geospatial.jp/ckan/api/3/action/",
  "mode": "rest",
  "list_path": "package_search",
  "detail_path": "package_show?id={id}",
  "search": "PLATEAU",
  "page_size": 100,
  "owner_org": "plateau-official",
  "extra_headers": {
    "User-Agent": "CKAN-PLATEAU-Harvester/0.1"
  }
}
```

Note: Adjust based on actual API structure.

---

## 🏙️ City-Specific Configuration

### Tokyo Only

```json
{
  "api_base": "http://mockapi:8088/api/v1/",
  "mode": "rest",
  "list_path": "datasets",
  "detail_path": "datasets/{id}",
  "search": "東京",
  "page_size": 100,
  "owner_org": "tokyo-city-data"
}
```

### Osaka Only

```json
{
  "api_base": "http://mockapi:8088/api/v1/",
  "mode": "rest",
  "list_path": "datasets",
  "detail_path": "datasets/{id}",
  "search": "大阪",
  "page_size": 100,
  "owner_org": "osaka-city-data"
}
```

---

## 🔄 Incremental Harvest (Date Filtering)

### Configuration JSON

```json
{
  "api_base": "https://api.plateau.example.com/v1/",
  "mode": "rest",
  "list_path": "datasets",
  "detail_path": "datasets/{id}",
  "modified_since": "2023-01-01T00:00:00Z",
  "page_size": 100,
  "owner_org": "plateau-data"
}
```

Note: Requires custom implementation in harvester to use `modified_since` parameter.

---

## 📊 Multiple Sources Setup

You can create multiple harvest sources for different purposes:

### Source 1: Tokyo Data
```bash
ckan harvester source create \
  name=plateau-tokyo \
  url=http://mockapi:8088/api/v1/ \
  type=plateau \
  config='{"api_base":"http://mockapi:8088/api/v1/","mode":"rest","list_path":"datasets","detail_path":"datasets/{id}","search":"東京","owner_org":"tokyo-data"}'
```

### Source 2: Osaka Data
```bash
ckan harvester source create \
  name=plateau-osaka \
  url=http://mockapi:8088/api/v1/ \
  type=plateau \
  config='{"api_base":"http://mockapi:8088/api/v1/","mode":"rest","list_path":"datasets","detail_path":"datasets/{id}","search":"大阪","owner_org":"osaka-data"}'
```

### Source 3: All PLATEAU Data
```bash
ckan harvester source create \
  name=plateau-all \
  url=http://mockapi:8088/api/v1/ \
  type=plateau \
  config='{"api_base":"http://mockapi:8088/api/v1/","mode":"rest","list_path":"datasets","detail_path":"datasets/{id}","owner_org":"plateau-data"}'
```

---

## 🧪 Testing Configuration

### Test with Mock API

1. **Start Mock API**:
   ```bash
   cd mockapi
   docker-compose up -d
   ```

2. **Verify endpoints**:
   ```bash
   curl http://localhost:8088/api/v1/datasets
   curl http://localhost:8088/api/v1/datasets/13100_tokyo_chiyoda_2023
   ```

3. **Create harvest source** (use one of the configs above)

4. **Run harvest**:
   ```bash
   ckan -c /etc/ckan/ckan.ini harvester run
   ```

5. **Check results**:
   ```bash
   # List harvested packages
   ckan -c /etc/ckan/ckan.ini package search plateau
   ```

---

## ⚙️ Configuration Parameters Reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_base` | string | Yes | Base URL of the API |
| `mode` | string | Yes | `"rest"` or `"graphql"` |
| `api_key` | string | No | API authentication key |
| `list_path` | string | REST only | Path to list endpoint |
| `detail_path` | string | REST only | Path template for detail (use `{id}`) |
| `graph_path` | string | GraphQL only | Path to GraphQL endpoint |
| `list_query` | string | GraphQL only | GraphQL query for listing |
| `detail_query` | string | GraphQL only | GraphQL query for detail |
| `search` | string | No | Search keyword/filter |
| `page_size` | integer | No | Items per page (default: 100) |
| `owner_org` | string | No | Organization name or ID |
| `extra_headers` | object | No | Additional HTTP headers |

---

## 🐛 Troubleshooting Configurations

### Config not working?

1. **Validate JSON**:
   ```bash
   echo '{"api_base":"..."}' | python -m json.tool
   ```

2. **Test API manually**:
   ```bash
   curl -v http://mockapi:8088/api/v1/datasets
   ```

3. **Check CKAN logs**:
   ```bash
   docker-compose logs -f ckan
   ```

4. **View harvest job details**:
   ```bash
   ckan -c /etc/ckan/ckan.ini harvester jobs
   ckan -c /etc/ckan/ckan.ini harvester job-show {job-id}
   ```

---

## 📚 Additional Resources

- [CKAN Harvest Extension](https://github.com/ckan/ckanext-harvest)
- [PLATEAU Project](https://www.mlit.go.jp/plateau/)
- [CKAN API Documentation](https://docs.ckan.org/en/latest/api/)
