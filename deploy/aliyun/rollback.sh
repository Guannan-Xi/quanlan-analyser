#!/bin/bash

# QLanalyser Aliyun Production Rollback Script
# Quick rollback to previous deployment

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${DEPLOY_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "======================================"
echo "  QLanalyser 回滚工具"
echo "======================================"
echo ""

# Check if backup images exist
print_info "查找可用的备份镜像..."

BACKUP_IMAGES=$(docker images | grep "quanlan-analyser-official" | grep "backup-" | awk '{print $2}' | sort -r)

if [ -z "${BACKUP_IMAGES}" ]; then
    print_error "未找到备份镜像！"
    print_info "备份镜像标签格式: backup-YYYYMMDD-HHMMSS"
    exit 1
fi

# Display available backups
echo "可用的备份版本："
echo ""
INDEX=1
declare -A BACKUP_MAP

while IFS= read -r backup; do
    echo "  ${INDEX}) ${backup}"
    BACKUP_MAP[${INDEX}]="${backup}"
    INDEX=$((INDEX + 1))
done <<< "${BACKUP_IMAGES}"

echo ""
read -p "选择要回滚到的版本 (1-$((INDEX-1))，或按 Ctrl+C 取消): " SELECTION

# Validate selection
if ! [[ "${SELECTION}" =~ ^[0-9]+$ ]] || [ "${SELECTION}" -lt 1 ] || [ "${SELECTION}" -ge ${INDEX} ]; then
    print_error "无效的选择！"
    exit 1
fi

SELECTED_BACKUP="${BACKUP_MAP[${SELECTION}]}"
print_info "选择的备份版本: ${SELECTED_BACKUP}"

# Confirmation
echo ""
print_warn "⚠️  警告：此操作将停止当前服务并回滚到选定版本"
read -p "确认回滚? (yes/no): " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    print_info "已取消回滚"
    exit 0
fi

echo ""
print_info "开始回滚..."

# Stop current containers
print_info "停止当前容器..."
cd "${PROJECT_ROOT}"
docker-compose -f "${COMPOSE_FILE}" down

if [ $? -ne 0 ]; then
    print_error "停止容器失败！"
    exit 1
fi

# Tag backup images as latest
print_info "恢复备份镜像..."

docker tag quanlan-analyser-official_backend:${SELECTED_BACKUP} quanlan-analyser-official_backend:latest
docker tag quanlan-analyser-official_frontend:${SELECTED_BACKUP} quanlan-analyser-official_frontend:latest

if [ $? -ne 0 ]; then
    print_error "恢复镜像失败！"
    exit 1
fi

print_info "✓ 镜像已恢复"

# Start containers with backup images
print_info "启动回滚后的容器..."
docker-compose -f "${COMPOSE_FILE}" up -d

if [ $? -ne 0 ]; then
    print_error "启动容器失败！"
    exit 1
fi

print_info "✓ 容器已启动"

# Wait and health check
print_info "等待服务启动..."
sleep 10

RETRY_COUNT=0
MAX_RETRIES=10

while [ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]; do
    if curl -f http://localhost/health &> /dev/null; then
        print_info "✓ 健康检查通过"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        print_warn "健康检查失败，重试 ${RETRY_COUNT}/${MAX_RETRIES}..."
        sleep 5
    fi
done

if [ ${RETRY_COUNT} -eq ${MAX_RETRIES} ]; then
    print_error "健康检查失败！回滚可能未成功"
    print_info "查看日志："
    docker-compose -f "${COMPOSE_FILE}" logs --tail=50
    exit 1
fi

# Show status
echo ""
print_info "容器状态："
docker-compose -f "${COMPOSE_FILE}" ps

echo ""
echo "======================================"
print_info "✅ 回滚成功！"
echo "======================================"
echo ""
print_info "已回滚到版本: ${SELECTED_BACKUP}"
print_info "服务已恢复运行"
echo ""

exit 0
