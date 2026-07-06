#!/bin/bash

# QLanalyser Aliyun Production Deployment Script
# This script automates the deployment process on Aliyun ECS

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${DEPLOY_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"
ENV_FILE="${DEPLOY_DIR}/production.env"

echo "======================================"
echo "  QLanalyser 阿里云生产环境部署"
echo "======================================"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root or with sudo
if [ "$EUID" -eq 0 ]; then 
    print_warn "不建议使用root用户运行，但继续执行..."
fi

# Pre-deployment checks
print_info "执行部署前检查..."

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker 未安装！请先安装 Docker。"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose 未安装！请先安装 Docker Compose。"
    exit 1
fi

# Check if production.env exists
if [ ! -f "${ENV_FILE}" ]; then
    print_error "production.env 配置文件不存在！"
    print_info "请从 production.env.template 创建 production.env 并填写配置"
    exit 1
fi

# Check if sensitive values are still templates
if grep -q "CHANGE_ME" "${ENV_FILE}"; then
    print_error "production.env 中仍包含 'CHANGE_ME' 占位符！"
    print_info "请替换所有 CHANGE_ME 为实际配置值"
    exit 1
fi

# Check if SSL certificates exist
SSL_DIR="${PROJECT_ROOT}/ssl"
if [ ! -d "${SSL_DIR}" ] || [ ! -f "${SSL_DIR}/qlanalyser.pem" ]; then
    print_warn "SSL证书未找到在 ${SSL_DIR}"
    print_warn "请确保部署前已配置SSL证书，或使用HTTP模式"
    read -p "是否继续部署? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check disk space (require at least 10GB free)
AVAILABLE_SPACE=$(df -BG "${PROJECT_ROOT}" | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "${AVAILABLE_SPACE}" -lt 10 ]; then
    print_error "磁盘空间不足！至少需要 10GB 可用空间，当前可用: ${AVAILABLE_SPACE}GB"
    exit 1
fi

print_info "✓ 部署前检查通过"
echo ""

# Backup current deployment (if exists)
if docker ps -a | grep -q "qlanalyser"; then
    print_info "检测到现有部署，创建备份点..."
    BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"
    
    # Tag current images as backup
    if docker images | grep -q "qlanalyser"; then
        docker tag quanlan-analyser-official_backend:latest quanlan-analyser-official_backend:${BACKUP_TAG} 2>/dev/null || true
        docker tag quanlan-analyser-official_frontend:latest quanlan-analyser-official_frontend:${BACKUP_TAG} 2>/dev/null || true
        print_info "✓ 已创建镜像备份: ${BACKUP_TAG}"
    fi
fi

# Pull latest code (if in git repo)
if [ -d "${PROJECT_ROOT}/.git" ]; then
    print_info "检查代码更新..."
    cd "${PROJECT_ROOT}"
    
    CURRENT_BRANCH=$(git branch --show-current)
    print_info "当前分支: ${CURRENT_BRANCH}"
    
    # Show current commit
    CURRENT_COMMIT=$(git rev-parse --short HEAD)
    print_info "当前提交: ${CURRENT_COMMIT}"
    
    # Option to pull latest
    read -p "是否拉取最新代码? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git pull origin ${CURRENT_BRANCH}
        print_info "✓ 代码已更新"
    fi
fi

# Build Docker images
print_info "开始构建 Docker 镜像..."
cd "${PROJECT_ROOT}"

docker-compose -f "${COMPOSE_FILE}" build --no-cache

if [ $? -ne 0 ]; then
    print_error "镜像构建失败！"
    exit 1
fi

print_info "✓ 镜像构建成功"
echo ""

# Stop old containers
print_info "停止旧容器..."
docker-compose -f "${COMPOSE_FILE}" down

if [ $? -eq 0 ]; then
    print_info "✓ 旧容器已停止"
else
    print_warn "停止旧容器时出现警告（可能不存在旧容器）"
fi

echo ""

# Start new containers
print_info "启动新容器..."
docker-compose -f "${COMPOSE_FILE}" up -d

if [ $? -ne 0 ]; then
    print_error "容器启动失败！"
    print_info "尝试回滚到之前的版本..."
    
    # Rollback if backup exists
    if docker images | grep -q "${BACKUP_TAG}"; then
        docker tag quanlan-analyser-official_backend:${BACKUP_TAG} quanlan-analyser-official_backend:latest
        docker tag quanlan-analyser-official_frontend:${BACKUP_TAG} quanlan-analyser-official_frontend:latest
        docker-compose -f "${COMPOSE_FILE}" up -d
        print_warn "已回滚到备份版本"
    fi
    
    exit 1
fi

print_info "✓ 容器已启动"
echo ""

# Wait for services to be ready
print_info "等待服务启动..."
sleep 10

# Check container status
print_info "检查容器状态..."
docker-compose -f "${COMPOSE_FILE}" ps

# Health check
print_info "执行健康检查..."

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
    print_error "健康检查失败！服务可能未正常启动"
    print_info "查看日志："
    docker-compose -f "${COMPOSE_FILE}" logs --tail=50
    exit 1
fi

# Show running containers
echo ""
print_info "运行中的容器："
docker ps --filter "name=qlanalyser"

# Show logs
echo ""
print_info "最近的日志："
docker-compose -f "${COMPOSE_FILE}" logs --tail=20

# Cleanup old images (optional)
echo ""
read -p "是否清理未使用的旧镜像? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "清理旧镜像..."
    docker image prune -f
    print_info "✓ 清理完成"
fi

# Summary
echo ""
echo "======================================"
print_info "✅ 部署成功！"
echo "======================================"
echo ""
print_info "访问地址："
print_info "  - HTTPS: https://qlanalyser.online"
print_info "  - HTTP:  http://$(hostname -I | awk '{print $1}')"
echo ""
print_info "常用命令："
print_info "  - 查看日志: docker-compose -f ${COMPOSE_FILE} logs -f"
print_info "  - 查看状态: docker-compose -f ${COMPOSE_FILE} ps"
print_info "  - 停止服务: docker-compose -f ${COMPOSE_FILE} down"
print_info "  - 重启服务: docker-compose -f ${COMPOSE_FILE} restart"
echo ""
print_info "监控面板："
print_info "  - 容器状态: docker stats"
print_info "  - 系统资源: htop"
echo ""

exit 0
