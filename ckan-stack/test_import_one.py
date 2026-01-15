#!/usr/bin/env python3
"""测试导入单个数据集并显示详细错误"""

import requests
import json

SOURCE_CKAN = "https://www.geospatial.jp/ckan"
LOCAL_CKAN = "https://opendata.uixai.org"

# 测试用的数据集
TEST_DATASET_ID = "plateau-13102-chuo-ku-2023"

API_KEY = input("请输入 API Key: ").strip()

print(f"\n1. 从源 CKAN 获取数据集: {TEST_DATASET_ID}")
response = requests.get(
    f"{SOURCE_CKAN}/api/3/action/package_show",
    params={"id": TEST_DATASET_ID}
)
source_data = response.json()

if not source_data.get("success"):
    print("❌ 无法获取源数据集")
    exit(1)

dataset = source_data["result"]
print(f"✓ 获取成功: {dataset.get('title', 'No title')}")
print(f"  原始字段数: {len(dataset)}")

# 显示关键字段
print("\n2. 数据集关键信息:")
print(f"  - name: {dataset.get('name')}")
print(f"  - title: {dataset.get('title')}")
print(f"  - owner_org: {dataset.get('owner_org')}")
print(f"  - license_id: {dataset.get('license_id')}")
print(f"  - tags: {len(dataset.get('tags', []))}")
print(f"  - resources: {len(dataset.get('resources', []))}")
print(f"  - extras: {len(dataset.get('extras', []))}")

# 清理数据集
print("\n3. 清理数据集...")
remove_fields = [
    'id', 'revision_id', 'creator_user_id',
    'metadata_created', 'metadata_modified',
    'num_tags', 'num_resources', 'revision_timestamp',
    'tracking_summary', 'organization', 'relationships_as_subject',
    'relationships_as_object', 'groups', 'state',
    'type', 'isopen', 'creator_user_id'
]

cleaned_dataset = {k: v for k, v in dataset.items() if k not in remove_fields}

# 确保必填字段
cleaned_dataset['owner_org'] = None  # 允许为空
cleaned_dataset['name'] = dataset['name'] + '-imported'  # 避免名称冲突

print(f"  清理后字段数: {len(cleaned_dataset)}")

# 保存到文件以便检查
with open('/tmp/cleaned_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(cleaned_dataset, f, indent=2, ensure_ascii=False)
print("  已保存到: /tmp/cleaned_dataset.json")

# 尝试导入
print("\n4. 尝试导入到本地 CKAN...")
response = requests.post(
    f"{LOCAL_CKAN}/api/3/action/package_create",
    headers={
        'Authorization': API_KEY,
        'Content-Type': 'application/json'
    },
    json=cleaned_dataset,
    timeout=30
)

result = response.json()

if result.get("success"):
    print(f"✓ 导入成功: {result['result']['name']}")
    print(f"  URL: {LOCAL_CKAN}/dataset/{result['result']['name']}")
else:
    print("❌ 导入失败")
    print("\n完整错误信息:")
    print(json.dumps(result.get('error', {}), indent=2, ensure_ascii=False))

    # 保存错误信息
    with open('/tmp/import_error.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("\n错误已保存到: /tmp/import_error.json")
