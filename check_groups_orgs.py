#!/usr/bin/env python3
"""
Check Groups and Organizations structure in CKAN
"""
import requests
import json

# CKAN API configuration
CKAN_URL = 'http://localhost:5002'

def get_data(endpoint):
    """Get data from CKAN API"""
    url = f'{CKAN_URL}/api/3/action/{endpoint}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['result']
        else:
            print(f"Error fetching {endpoint}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return None

def main():
    print("=== CKAN Groups and Organizations Structure ===\n")

    # Get Groups
    print("1. GROUPS:")
    groups = get_data('group_list')
    if groups:
        for group_name in groups:
            group_detail = get_data(f'group_show?id={group_name}')
            if group_detail:
                print(f"   - {group_detail['name']} ({group_detail['title']})")
                print(f"     Type: {group_detail.get('type', 'group')}")
                print(f"     Is Organization: {group_detail.get('is_organization', False)}")
                print(f"     Packages: {len(group_detail.get('packages', []))}")
                if group_detail.get('packages'):
                    for pkg in group_detail['packages'][:3]:  # Show first 3
                        print(f"       - {pkg['name']}")
                print()
    else:
        print("   No groups found or error occurred\n")

    # Get Organizations
    print("2. ORGANIZATIONS:")
    orgs = get_data('organization_list')
    if orgs:
        for org_name in orgs:
            org_detail = get_data(f'organization_show?id={org_name}')
            if org_detail:
                print(f"   - {org_detail['name']} ({org_detail['title']})")
                print(f"     Type: {org_detail.get('type', 'organization')}")
                print(f"     Is Organization: {org_detail.get('is_organization', True)}")
                print(f"     Packages: {len(org_detail.get('packages', []))}")
                if org_detail.get('packages'):
                    for pkg in org_detail['packages'][:3]:  # Show first 3
                        print(f"       - {pkg['name']}")
                print()
    else:
        print("   No organizations found or error occurred\n")

    # Get example dataset to show relationship
    print("3. EXAMPLE DATASET RELATIONSHIPS:")
    datasets = get_data('package_list')
    if datasets:
        for dataset_name in datasets[:2]:  # Check first 2 datasets
            dataset = get_data(f'package_show?id={dataset_name}')
            if dataset:
                print(f"   Dataset: {dataset['name']} ({dataset['title']})")
                print(f"     Owner Organization: {dataset.get('owner_org', 'None')}")
                print(f"     Groups: {[g['name'] for g in dataset.get('groups', [])]}")
                print()

    print("\n=== RELATIONSHIP EXPLANATION ===")
    print("""
CKAN中Groups和Organizations的关系：

1. **技术实现层面**：
   - Groups和Organizations都存储在同一个数据表中（group表）
   - 区别在于 is_organization 字段：
     * is_organization=True → Organization
     * is_organization=False → Group

2. **功能层面**：
   - **Organizations（组织）**：
     * 用于数据集的所有权管理
     * 每个数据集只能属于一个Organization
     * 控制数据集的权限和访问
     * 通常代表发布数据的机构或部门

   - **Groups（分组）**：
     * 用于数据集的分类和组织
     * 一个数据集可以属于多个Groups
     * 主要用于主题分类、标签化
     * 帮助用户发现相关数据集

3. **关系结构**：
   - Dataset ←→ Organization：一对一关系（owner_org）
   - Dataset ←→ Groups：多对多关系（groups字段）
   - Groups和Organizations之间没有直接的层级关系

4. **使用场景**：
   - Organization：山口县政府、统计局、环境部等
   - Groups：人口统计、环境数据、经济指标等主题分类
""")

if __name__ == '__main__':
    main()