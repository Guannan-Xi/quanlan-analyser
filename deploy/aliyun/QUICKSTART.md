# QLanalyser 阿里云生产环境部署 - 快速参考

## 📦 生成的文件清单

```
项目根目录/
├── Dockerfile.backend              ✅ 后端Python容器镜像
├── Dockerfile.frontend             ✅ 前端Nginx容器镜像
├── .dockerignore                   ✅ Docker构建排除规则
├── docker-compose.prod.yml         ✅ 生产环境容器编排
│
└── deploy/aliyun/
    ├── README_DEPLOYMENT.md        ✅ 完整部署文档（19KB）
    ├── DEPLOYMENT_CHECKLIST.md     ✅ 部署配置清单（13KB）
    ├── production.env.template     ✅ 环境变量配置模板
    ├── nginx.production.conf       ✅ Nginx生产配置
    ├── monitoring.yml              ✅ 监控告警配置指南
    ├── deploy.sh                   ✅ 一键部署脚本（可执行）
    └── rollback.sh                 ✅ 一键回滚脚本（可执行）
```

## 🚀 一键部署命令

```bash
# 1. 登录阿里云ECS服务器
ssh root@your-server-ip

# 2. 安装Docker环境
curl -fsSL https://get.docker.com | bash

# 3. 上传代码到服务器
cd /opt
git clone <your-repo> quanlan-analyser-official
cd quanlan-analyser-official

# 4. 配置环境变量
cp deploy/aliyun/production.env.template deploy/aliyun/production.env
vim deploy/aliyun/production.env  # 替换所有 CHANGE_ME

# 5. 配置SSL证书
mkdir ssl
# 上传证书: qlanalyser.pem 和 qlanalyser.key

# 6. 一键部署
./deploy/aliyun/deploy.sh
```

## 📖 主要文档说明

### README_DEPLOYMENT.md（必读）
**完整的部署指南**，包含：
- 服务器配置要求（最低/推荐/高负载）
- 域名和SSL证书配置步骤
- 详细部署流程
- 运维管理命令
- 监控告警配置
- 常见问题排查（8个常见场景）
- 安全最佳实践

### DEPLOYMENT_CHECKLIST.md
**部署配置说明和检查清单**，包含：
- 所有配置文件的详细说明
- 架构特点和设计理念
- 部署前检查清单（26项）
- 更新和维护建议
- 性能优化建议
- 成本优化建议

## ⚙️ 核心配置说明

### Docker镜像
- **Dockerfile.backend**: 多阶段构建，Python 3.10，4个Uvicorn workers，非root用户
- **Dockerfile.frontend**: Nginx 1.25 Alpine，静态文件服务，健康检查

### 容器编排
- **docker-compose.prod.yml**: 
  - 2个核心服务（backend + frontend）
  - 可选服务（Redis/PostgreSQL/Certbot）
  - 资源限制和健康检查
  - 持久化数据卷

### Nginx配置
- **nginx.production.conf**:
  - HTTPS强制重定向
  - 支持20GB大文件上传
  - 3600秒长超时（EEG分析）
  - 完善的安全头部
  - Gzip压缩和缓存优化

### 环境变量
- **production.env.template**:
  - 应用配置（密钥、环境）
  - 阿里云OSS存储配置
  - 第三方服务（支付/邮件/短信）
  - 监控日志配置
  - 功能开关

## 🔍 关键配置项

### 必须修改的配置（production.env）

```bash
# 生成安全密钥
APP_SECRET_KEY=<使用 python -c "import secrets; print(secrets.token_urlsafe(32))" 生成>
JWT_SECRET_KEY=<使用相同命令生成>

# 阿里云OSS配置
QLANALYSER_ALIYUN_OSS_BUCKET=qlanalyser-prod-data
QLANALYSER_ALIYUN_OSS_ACCESS_KEY_ID=<从阿里云RAM用户获取>
QLANALYSER_ALIYUN_OSS_ACCESS_KEY_SECRET=<从阿里云RAM用户获取>

# 域名配置
QLANALYSER_PUBLIC_BASE_URL=https://qlanalyser.online
QLANALYSER_CORS_ORIGINS=https://qlanalyser.online
```

## 📊 监控配置（monitoring.yml）

配置云监控告警规则：
- CPU > 80%（警告）/ 95%（严重）
- 内存 > 85%（警告）/ 95%（严重）
- 磁盘 > 80%（警告）/ 90%（严重）
- HTTP可用性检查
- API响应时间 > 3秒
- SSL证书过期提醒（30天/7天）

## 🛡️ 安全最佳实践

1. ✅ 使用强密码和随机SECRET_KEY
2. ✅ 强制HTTPS访问
3. ✅ 限制SSH访问IP（安全组）
4. ✅ OSS使用私有Bucket
5. ✅ 容器以非root用户运行
6. ✅ 定期备份数据到异地
7. ✅ 启用云监控和日志分析
8. ✅ 定期更新系统和Docker镜像

## 🔄 运维常用命令

```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 重启服务
docker-compose -f docker-compose.prod.yml restart

# 更新部署
git pull
./deploy/aliyun/deploy.sh

# 回滚
./deploy/aliyun/rollback.sh

# 查看资源使用
docker stats

# 备份数据
tar -czf backup_$(date +%Y%m%d).tar.gz \
  /var/lib/docker/volumes/quanlan-analyser-official_*
```

## ⚠️ 注意事项

1. **首次部署前必须**:
   - 替换 production.env 中所有 CHANGE_ME
   - 配置SSL证书到 ssl/ 目录
   - 创建阿里云OSS Bucket
   - 配置域名解析

2. **安全组配置**:
   - 必须开放：80 (HTTP), 443 (HTTPS)
   - 限制访问：22 (SSH) - 仅管理员IP

3. **存储建议**:
   - 使用阿里云OSS作为主存储
   - 本地磁盘仅作为临时缓存
   - 定期清理临时文件

4. **性能调优**:
   - Uvicorn workers = CPU核心数
   - 根据内存调整容器资源限制
   - 考虑使用Redis缓存和独立RDS

## 📞 支持

详细问题排查请参考 `README_DEPLOYMENT.md` 第9章"常见问题"。

---

**完成时间**: 2026-07-03  
**版本**: 1.0.0  
**状态**: ✅ 生产就绪
