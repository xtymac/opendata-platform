#!/usr/bin/env python3
"""
简单导入 5 个 PLATEAU 数据集到本地 CKAN
从 G空間情報センター 获取数据
"""

import requests
import json
import sys
import time

# 配置
SOURCE_CKAN = "https://www.geospatial.jp/ckan"
LOCAL_CKAN = "https://opendata.uixai.org"  # 使用公网域名

# 5 个推荐的 PLATEAU 数据集（使用实际存在的 ID）
DATASETS = [
    {
        "id": "plateau-13102-chuo-ku-2023",
        "name": "東京都中央区 2023"
    },
    {
        "id": "plateau-13103-minato-ku-2023",
        "name": "東京都港区 2023"
    },
    {
        "id": "plateau-14100-yokohama-shi-2024",
        "name": "横浜市 2024"
    },
    {
        "id": "plateau-13113-shibuya-ku-2023",
        "name": "東京都渋谷区 2023"
    },
    {
        "id": "plateau-13109-shinagawa-ku-2024",
        "name": "東京都品川区 2024"
    }
]

def get_api_key():
    """获取 CKAN API Key"""
    print("\n请提供 CKAN API Key (需要 sysadmin 权限)")
    print("获取方式: 登录 CKAN -> 右上角用户名 -> API Tokens")
    api_key = input("API Key: ").strip()

    if not api_key:
        print("错误: API Key 不能为空")
        sys.exit(1)

    return api_key

def fetch_dataset(dataset_id):
    """从源 CKAN 获取数据集"""
    url = f"{SOURCE_CKAN}/api/3/action/package_show"
    params = {"id": dataset_id}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            return data["result"]
        else:
            print(f"  ❌ 获取失败: {data.get('error', {}).get('message', 'Unknown error')}")
            return None

    except Exception as e:
        print(f"  ❌ 网络错误: {e}")
        return None

def clean_dataset(dataset):
    """清理数据集，移除不需要的字段"""
    # 移除这些字段
    remove_fields = [
        'id', 'revision_id', 'creator_user_id',
        'metadata_created', 'metadata_modified',
        'num_tags', 'num_resources', 'revision_timestamp',
        'tracking_summary', 'organization',
        'relationships_as_subject', 'relationships_as_object',
        'groups', 'state', 'isopen', 'type'
    ]

    for field in remove_fields:
        dataset.pop(field, None)

    # 清理 tags - 只保留 name 字段
    original_tags = dataset.get('tags', [])
    cleaned_tags = []
    for tag in original_tags[:10]:  # 最多保留 10 个标签
        if isinstance(tag, dict) and tag.get('name'):
            # 只保留 name，移除其他字段
            cleaned_tags.append({'name': tag['name']})
        elif isinstance(tag, str):
            cleaned_tags.append({'name': tag})

    # 添加自定义标签
    for tag_name in ['plateau', 'imported']:
        if not any(t.get('name') == tag_name for t in cleaned_tags):
            cleaned_tags.append({'name': tag_name})

    dataset['tags'] = cleaned_tags

    # 处理 license_id - 如果是 "plateau"，改为通用 license
    if dataset.get('license_id') == 'plateau':
        dataset['license_id'] = 'cc-by'  # 使用 Creative Commons

    # 清理 resources
    resources = dataset.get('resources', [])
    cleaned_resources = []
    for res in resources:
        # 移除 resource 中的不需要字段
        cleaned_res = {
            'url': res.get('url', ''),
            'name': res.get('name', 'Resource'),
            'description': res.get('description', ''),
            'format': res.get('format', '').upper()
        }
        # 移除空值
        cleaned_res = {k: v for k, v in cleaned_res.items() if v}
        if cleaned_res.get('url'):  # 必须有 URL
            cleaned_resources.append(cleaned_res)

    dataset['resources'] = cleaned_resources

    # 添加来源信息到 extras
    dataset['extras'] = dataset.get('extras', [])
    dataset['extras'].append({
        'key': 'source_catalog',
        'value': 'G空間情報センター'
    })
    dataset['extras'].append({
        'key': 'source_url',
        'value': f"{SOURCE_CKAN}/dataset/{dataset.get('name', '')}"
    })
    # 保存原始 license
    if dataset.get('license_id'):
        dataset['extras'].append({
            'key': 'original_license',
            'value': 'PLATEAU License'
        })

    # owner_org 设置为 g-space 组织
    dataset['owner_org'] = 'g-space'  # G空間情報センター

    # 修改 name 以避免冲突
    original_name = dataset.get('name', '')
    dataset['name'] = original_name + '-imported'

    return dataset

def import_dataset(dataset, api_key):
    """导入数据集到本地 CKAN"""
    url = f"{LOCAL_CKAN}/api/3/action/package_create"
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=dataset,
            timeout=30
        )

        data = response.json()

        if data.get("success"):
            return True, data["result"]["name"]
        else:
            error_msg = data.get('error', {})
            if isinstance(error_msg, dict):
                # 显示完整的验证错误
                if '__type' in error_msg and error_msg['__type'] == 'Validation Error':
                    details = json.dumps(error_msg, indent=2, ensure_ascii=False)
                    return False, f"Validation Error:\n{details}"
                error_msg = error_msg.get('message') or error_msg.get('__type', 'Unknown error')
            return False, str(error_msg)

    except Exception as e:
        return False, str(e)

def main():
    print("=" * 50)
    print("导入 5 个 PLATEAU 数据集到本地 CKAN")
    print("=" * 50)
    print()

    print("将导入以下数据集:")
    for i, ds in enumerate(DATASETS, 1):
        print(f"  {i}. {ds['name']} ({ds['id']})")
    print()

    confirm = input("确认导入? (y/n): ").strip().lower()
    if confirm != 'y':
        print("取消导入")
        return

    api_key = get_api_key()
    print()

    success_count = 0
    failed_count = 0

    for i, ds_info in enumerate(DATASETS, 1):
        print(f"[{i}/5] 导入: {ds_info['name']}")

        # 获取数据集
        print("  获取数据集信息...")
        dataset = fetch_dataset(ds_info['id'])

        if not dataset:
            print(f"  ❌ 失败: 无法获取数据集")
            failed_count += 1
            print()
            continue

        # 清理数据集
        print("  处理数据集...")
        dataset = clean_dataset(dataset)

        # 导入
        print("  导入到本地 CKAN...")
        success, result = import_dataset(dataset, api_key)

        if success:
            print(f"  ✓ 成功导入: {result}")
            success_count += 1
        else:
            print(f"  ❌ 失败: {result}")
            failed_count += 1

        print()
        time.sleep(2)  # 避免请求过快

    print("=" * 50)
    print("导入完成!")
    print("=" * 50)
    print()
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    print()

    if success_count > 0:
        print("请手动重建搜索索引:")
        print("  docker exec ckan ckan -c /srv/app/ckan.ini search-index rebuild")
        print()
        print("然后访问: https://opendata.uixai.org/dataset?q=plateau")

if __name__ == "__main__":
    main()
