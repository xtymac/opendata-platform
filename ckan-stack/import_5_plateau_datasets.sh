#!/bin/bash

# 导入 5 个 PLATEAU 数据集的脚本
# 从 G空間情報センター 获取数据集并导入到本地 CKAN

set -e

echo "=========================================="
echo "导入 5 个 PLATEAU 数据集"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
SOURCE_CKAN="https://www.geospatial.jp/ckan"
LOCAL_CKAN="http://ckan:5000"

# 获取 CKAN API Key (需要管理员权限)
echo -e "${YELLOW}请提供 CKAN API Key (sysadmin):${NC}"
read -p "API Key: " API_KEY

if [ -z "$API_KEY" ]; then
    echo "错误: API Key 不能为空"
    exit 1
fi

# 5 个推荐的 PLATEAU 数据集 ID
# 这些是从 G空間情報センター 精选的数据集
DATASETS=(
    "plateau-13100-chiyoda-ku-2023"
    "plateau-27100-osaka-shi-2023"
    "plateau-14100-yokohama-shi-2022"
    "plateau-23100-nagoya-shi-2022"
    "plateau-40100-fukuoka-shi-2021"
)

# 数据集名称（用于显示）
DATASET_NAMES=(
    "東京都千代田区 2023"
    "大阪市 2023"
    "横浜市 2022"
    "名古屋市 2022"
    "福岡市 2021"
)

echo ""
echo "将导入以下数据集："
for i in "${!DATASETS[@]}"; do
    echo "  $((i+1)). ${DATASET_NAMES[$i]} (${DATASETS[$i]})"
done
echo ""

read -p "确认导入? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "取消导入"
    exit 0
fi

echo ""
echo "开始导入..."
echo ""

# 导入函数
import_dataset() {
    local dataset_id=$1
    local dataset_name=$2
    local count=$3

    echo -e "${YELLOW}[$count/5] 导入: $dataset_name${NC}"

    # 从源 CKAN 获取数据集
    echo "  获取数据集信息..."
    dataset_json=$(curl -s "$SOURCE_CKAN/api/3/action/package_show?id=$dataset_id")

    # 检查是否成功
    if echo "$dataset_json" | jq -e '.success' > /dev/null 2>&1; then
        if [ "$(echo "$dataset_json" | jq -r '.success')" != "true" ]; then
            echo -e "  ❌ 失败: 数据集不存在或无法访问"
            return 1
        fi
    else
        echo -e "  ❌ 失败: 无效的响应"
        return 1
    fi

    # 提取数据集信息
    dataset=$(echo "$dataset_json" | jq '.result')

    # 清理不需要的字段
    dataset=$(echo "$dataset" | jq 'del(.id, .revision_id, .creator_user_id, .metadata_created, .metadata_modified, .num_tags, .num_resources, .revision_timestamp, .tracking_summary)')

    # 添加额外的标签
    dataset=$(echo "$dataset" | jq '.tags += [{"name": "plateau"}, {"name": "imported"}, {"name": "3d-city-model"}]')

    # 添加 extras 说明来源
    dataset=$(echo "$dataset" | jq '.extras += [{"key": "source_catalog", "value": "G空間情報センター"}, {"key": "source_url", "value": "'"$SOURCE_CKAN/dataset/$dataset_id"'"}]')

    # 导入到本地 CKAN
    echo "  导入到本地 CKAN..."
    import_result=$(docker exec ckan bash -c "curl -s -X POST '$LOCAL_CKAN/api/3/action/package_create' \
        -H 'Authorization: $API_KEY' \
        -H 'Content-Type: application/json' \
        -d '$(echo "$dataset" | jq -c .)'" 2>&1)

    # 检查导入结果
    if echo "$import_result" | jq -e '.success' > /dev/null 2>&1; then
        if [ "$(echo "$import_result" | jq -r '.success')" == "true" ]; then
            local pkg_name=$(echo "$import_result" | jq -r '.result.name')
            echo -e "  ${GREEN}✓ 成功导入: $pkg_name${NC}"
            return 0
        else
            local error_msg=$(echo "$import_result" | jq -r '.error.message // .error.__type // "Unknown error"')
            echo -e "  ❌ 失败: $error_msg"
            return 1
        fi
    else
        echo -e "  ❌ 失败: 无效的响应"
        echo "$import_result" | head -5
        return 1
    fi
}

# 导入所有数据集
success_count=0
failed_count=0

for i in "${!DATASETS[@]}"; do
    if import_dataset "${DATASETS[$i]}" "${DATASET_NAMES[$i]}" "$((i+1))"; then
        ((success_count++))
    else
        ((failed_count++))
    fi
    echo ""
    sleep 2  # 避免请求过快
done

echo "=========================================="
echo "导入完成!"
echo "=========================================="
echo ""
echo "成功: $success_count"
echo "失败: $failed_count"
echo ""

if [ $success_count -gt 0 ]; then
    echo "重建搜索索引..."
    docker exec ckan ckan -c /srv/app/ckan.ini search-index rebuild -q
    echo -e "${GREEN}✓ 完成!${NC}"
    echo ""
    echo "访问查看: https://opendata.uixai.org/dataset?q=plateau"
fi

echo ""
echo "提示: 如果某些数据集导入失败，可能是因为:"
echo "  1. 数据集 ID 已更改"
echo "  2. 需要调整数据集名称以避免冲突"
echo "  3. 某些字段与本地 CKAN schema 不兼容"
