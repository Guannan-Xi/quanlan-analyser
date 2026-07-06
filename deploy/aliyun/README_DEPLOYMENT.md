# QLanalyser 阿里云生产环境部署文档

## 📋 目录

1. [服务器配置要求](#服务器配置要求)
2. [部署前准备](#部署前准备)
3. [域名和SSL配置](#域名和ssl配置)
4. [部署步骤](#部署步骤)
5. [部署验证](#部署验证)
6. [运维管理](#运维管理)
7. [监控和告警](#监控和告警)
8. [回滚操作](#回滚操作)
9. [常见问题](#常见问题)
10. [安全最佳实践](#安全最佳实践)

---

## 🖥️ 服务器配置要求

### 最低配置（适用于测试/小规模使用）

- **CPU**: 4 核
- **内存**: 8 GB
- **磁盘**: 100 GB SSD
- **带宽**: 5 Mbps
- **操作系统**: Ubuntu 20.04/22.04 LTS 或 CentOS 7/8

### 推荐配置（适用于生产环境）

- **CPU**: 8 核
- **内存**: 16 GB
- **磁盘**: 200 GB SSD（建议 ESSD 云盘）
- **带宽**: 10 Mbps（按使用流量计费）
- **操作系统**: Ubuntu 22.04 LTS
- **实例规格**: ecs.c6.2xlarge 或更高

### 高负载配置（适用于大规模使用）

- **CPU**: 16 核+
- **内存**: 32 GB+
- **磁盘**: 500 GB+ ESSD PL1
- **带宽**: 100 Mbps
- **实例规格**: ecs.c7.4xlarge 或更高
- **负载均衡**: 使用阿里云 SLB
- **数据库**: 独立 RDS 实例
- **缓存**: 独立 Redis 实例

### 存储规划

```
/app/uploads     - EEG 文件上传临时存储 (50GB+)
/app/results     - 分析结果存储 (30GB+)
/app/artifacts   - 生成的制品存储 (20GB+)
/var/log         - 系统和应用日志 (10GB+)
Docker volumes   - 容器数据卷 (20GB+)
```

**建议**: 使用阿里云 OSS 对象存储作为主要存储后端，本地磁盘仅作为缓存。

---

## 🔧 部署前准备

### 1. 购买阿里云 ECS 服务器

1. 登录 [阿里云控制台](https://ecs.console.aliyun.com/)
2. 选择地域（建议：华东1-杭州 或 华北2-北京）
3. 选择实例规格（参考上述配置要求）
4. 配置网络：
   - 创建或选择 VPC
   - 创建安全组，开放端口：80 (HTTP)、443 (HTTPS)、22 (SSH)
5. 配置公网 IP（选择按使用流量计费）
6. 设置 root 密码或 SSH 密钥

### 2. 安全组规则配置

| 规则方向 | 端口范围 | 授权对象 | 说明 |
|---------|---------|---------|------|
| 入方向 | 22 | 管理员IP | SSH 登录（建议限制IP） |
| 入方向 | 80 | 0.0.0.0/0 | HTTP 访问 |
| 入方向 | 443 | 0.0.0.0/0 | HTTPS 访问 |

### 3. 登录服务器并安装依赖

```bash
# SSH 登录服务器
ssh root@your-server-ip

# 更新系统
apt update && apt upgrade -y  # Ubuntu
# yum update -y  # CentOS

# 安装 Docker
curl -fsSL https://get.docker.com | bash
systemctl enable docker
systemctl start docker

# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version

# 安装其他工具
apt install -y git curl wget htop vim  # Ubuntu
# yum install -y git curl wget htop vim  # CentOS
```

### 4. 配置阿里云 OSS（对象存储）

1. 登录 [OSS 控制台](https://oss.console.aliyun.com/)
2. 创建 Bucket:
   - **名称**: `qlanalyser-prod-data`
   - **地域**: 与 ECS 相同地域
   - **存储类型**: 标准存储
   - **访问控制**: 私有
3. 创建备份 Bucket:
   - **名称**: `qlanalyser-prod-backup`
   - **地域**: 不同地域（异地容灾）
4. 创建 RAM 用户:
   - 进入 [RAM 控制台](https://ram.console.aliyun.com/)
   - 创建用户：`qlanalyser-oss`
   - 授权策略：`AliyunOSSFullAccess`（或创建自定义策略）
   - 创建 AccessKey（记录 AccessKeyId 和 AccessKeySecret）

### 5. 获取代码

```bash
# 克隆代码仓库
cd /opt
git clone https://github.com/your-org/quanlan-analyser-official.git
cd quanlan-analyser-official

# 或者从本地上传代码
# 使用 scp 或 rsync 上传代码到服务器
```

---

## 🌐 域名和 SSL 配置

### 方案 A: 使用阿里云免费 SSL 证书

1. **购买域名**（如果还没有）:
   - 登录 [域名控制台](https://dc.console.aliyun.com/)
   - 搜索并购买域名（如 `qlanalyser.online`）

2. **域名解析**:
   - 进入域名管理
   - 添加 A 记录:
     ```
     主机记录: @
     记录类型: A
     记录值: ECS公网IP
     TTL: 10分钟
     ```
   - 添加 www 记录:
     ```
     主机记录: www
     记录类型: A
     记录值: ECS公网IP
     TTL: 10分钟
     ```

3. **申请免费 SSL 证书**:
   - 登录 [SSL 证书控制台](https://yundun.console.aliyun.com/)
   - 选择 "免费证书" → "立即购买"
   - 申请证书并填写域名 `qlanalyser.online`
   - 完成 DNS 验证
   - 下载证书（选择 Nginx 格式）

4. **上传证书到服务器**:
   ```bash
   # 在服务器上创建 SSL 目录
   mkdir -p /opt/quanlan-analyser-official/ssl
   
   # 使用 scp 上传证书文件
   # 在本地执行：
   # scp qlanalyser.pem root@your-server-ip:/opt/quanlan-analyser-official/ssl/
   # scp qlanalyser.key root@your-server-ip:/opt/quanlan-analyser-official/ssl/
   
   # 设置权限
   chmod 600 /opt/quanlan-analyser-official/ssl/qlanalyser.key
   chmod 644 /opt/quanlan-analyser-official/ssl/qlanalyser.pem
   ```

### 方案 B: 使用 Let's Encrypt 自动化证书

```bash
# 修改 docker-compose.prod.yml，启用 certbot 服务
# 然后执行：

# 首次申请证书
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d qlanalyser.online \
  -d www.qlanalyser.online \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email

# 证书会自动保存到 ./ssl 目录
# 并且每12小时自动续期
```

---

## 🚀 部署步骤

### 步骤 1: 配置环境变量

```bash
cd /opt/quanlan-analyser-official

# 复制环境变量模板
cp deploy/aliyun/production.env.template deploy/aliyun/production.env

# 编辑配置文件
vim deploy/aliyun/production.env

# 必须修改的配置项：
# - APP_SECRET_KEY (使用随机生成的密钥)
# - QLANALYSER_ALIYUN_OSS_ACCESS_KEY_ID
# - QLANALYSER_ALIYUN_OSS_ACCESS_KEY_SECRET
# - QLANALYSER_ALIYUN_OSS_BUCKET
# - 其他 CHANGE_ME 占位符
```

**生成安全密钥**:
```bash
# 生成 APP_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成 JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 步骤 2: 检查配置文件

```bash
# 检查是否还有未替换的占位符
grep -n "CHANGE_ME" deploy/aliyun/production.env

# 如果有输出，继续修改配置文件
# 如果无输出，说明配置完成
```

### 步骤 3: 部署前检查清单

- [ ] Docker 和 Docker Compose 已安装
- [ ] 域名解析已生效（`ping qlanalyser.online`）
- [ ] SSL 证书已上传到 `ssl/` 目录
- [ ] `production.env` 已正确配置（无 CHANGE_ME）
- [ ] 阿里云 OSS Bucket 已创建
- [ ] 阿里云 OSS AccessKey 已配置
- [ ] 安全组已开放 80 和 443 端口
- [ ] 磁盘空间充足（至少 50GB 可用）

### 步骤 4: 执行一键部署

```bash
cd /opt/quanlan-analyser-official

# 赋予执行权限（如果尚未设置）
chmod +x deploy/aliyun/deploy.sh

# 执行部署脚本
./deploy/aliyun/deploy.sh
```

部署脚本会自动执行以下操作：
1. ✅ 检查依赖和配置
2. ✅ 备份当前部署（如果存在）
3. ✅ 构建 Docker 镜像
4. ✅ 停止旧容器
5. ✅ 启动新容器
6. ✅ 执行健康检查
7. ✅ 显示部署状态

### 步骤 5: 手动部署（可选）

如果不使用部署脚本，可以手动执行：

```bash
cd /opt/quanlan-analyser-official

# 构建镜像
docker-compose -f docker-compose.prod.yml build

# 启动容器
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

---

## ✅ 部署验证

### 1. 检查容器状态

```bash
# 查看所有容器
docker ps

# 应该看到以下容器正在运行：
# - qlanalyser-backend
# - qlanalyser-frontend
# (可选: qlanalyser-redis, qlanalyser-postgres)
```

### 2. 检查服务健康

```bash
# HTTP 健康检查
curl http://localhost/health
# 期望输出: healthy

# API 健康检查
curl http://localhost/api/health
# 期望输出: {"status":"ok"} 或类似

# HTTPS 检查（如果配置了SSL）
curl https://qlanalyser.online/health
```

### 3. 检查日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs

# 查看后端日志
docker-compose -f docker-compose.prod.yml logs backend

# 查看前端日志
docker-compose -f docker-compose.prod.yml logs frontend

# 实时跟踪日志
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

### 4. 功能测试

1. **访问前端**: 浏览器打开 `https://qlanalyser.online`
2. **API 文档**: 访问 `https://qlanalyser.online/docs`
3. **注册/登录**: 创建测试账号
4. **上传文件**: 尝试上传小型 EEG 文件
5. **分析任务**: 提交分析任务并检查结果

---

## 🔧 运维管理

### 常用 Docker 命令

```bash
# 进入项目目录
cd /opt/quanlan-analyser-official

# 查看容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看容器资源使用
docker stats

# 重启所有服务
docker-compose -f docker-compose.prod.yml restart

# 重启单个服务
docker-compose -f docker-compose.prod.yml restart backend

# 停止所有服务
docker-compose -f docker-compose.prod.yml stop

# 启动所有服务
docker-compose -f docker-compose.prod.yml start

# 完全停止并删除容器（数据卷保留）
docker-compose -f docker-compose.prod.yml down

# 停止并删除所有数据（危险！）
docker-compose -f docker-compose.prod.yml down -v
```

### 日志管理

```bash
# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f backend

# 查看最近 100 行日志
docker-compose -f docker-compose.prod.yml logs --tail=100

# 导出日志到文件
docker-compose -f docker-compose.prod.yml logs > logs_$(date +%Y%m%d).txt

# 清理旧日志（Docker 会自动轮转，配置见 docker-compose.prod.yml）
docker-compose -f docker-compose.prod.yml logs --tail=0
```

### 数据备份

```bash
# 备份上传的文件
tar -czf backup_uploads_$(date +%Y%m%d).tar.gz \
  /var/lib/docker/volumes/quanlan-analyser-official_uploads/_data/

# 备份分析结果
tar -czf backup_results_$(date +%Y%m%d).tar.gz \
  /var/lib/docker/volumes/quanlan-analyser-official_results/_data/

# 如果使用 PostgreSQL，备份数据库
docker exec qlanalyser-postgres pg_dump -U qlanalyser qlanalyser > \
  backup_db_$(date +%Y%m%d).sql

# 上传备份到 OSS（推荐）
# 需要安装 ossutil: https://help.aliyun.com/document_detail/120075.html
ossutil cp backup_uploads_$(date +%Y%m%d).tar.gz \
  oss://qlanalyser-prod-backup/backups/
```

### 更新部署

```bash
cd /opt/quanlan-analyser-official

# 拉取最新代码
git pull origin main

# 重新部署
./deploy/aliyun/deploy.sh

# 或手动更新
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### 数据清理

```bash
# 清理未使用的 Docker 镜像
docker image prune -f

# 清理所有未使用的资源
docker system prune -f

# 清理包括数据卷（危险！）
docker system prune -a --volumes
```

---

## 📊 监控和告警

### 阿里云云监控配置

参考 `deploy/aliyun/monitoring.yml` 文件配置云监控告警规则。

**快速配置步骤**：

1. 登录 [云监控控制台](https://cloudmonitor.console.aliyun.com/)
2. 创建报警联系人组
3. 配置主机监控告警：
   - CPU 使用率 > 80%
   - 内存使用率 > 85%
   - 磁盘使用率 > 90%
4. 配置站点监控：
   - URL: `https://qlanalyser.online/health`
   - 频率: 1 分钟
   - 告警条件: HTTP 状态码 != 200

### Docker 监控命令

```bash
# 实时监控容器资源
docker stats

# 查看容器详细信息
docker inspect qlanalyser-backend

# 监控磁盘使用
df -h

# 监控内存使用
free -h

# 监控 CPU 和进程
htop
```

### 日志分析

```bash
# 统计错误日志
docker-compose -f docker-compose.prod.yml logs backend | grep -i "error" | wc -l

# 查看最近的错误
docker-compose -f docker-compose.prod.yml logs backend | grep -i "error" | tail -20

# 统计 API 请求
docker-compose -f docker-compose.prod.yml logs frontend | grep "GET /api" | wc -l
```

---

## ⏮️ 回滚操作

如果新部署出现问题，可以快速回滚到之前的版本。

### 使用回滚脚本（推荐）

```bash
cd /opt/quanlan-analyser-official

# 赋予执行权限
chmod +x deploy/aliyun/rollback.sh

# 执行回滚
./deploy/aliyun/rollback.sh

# 脚本会列出可用的备份版本，选择要回滚的版本
```

### 手动回滚

```bash
# 1. 查看可用的备份镜像
docker images | grep backup

# 2. 找到要回滚的版本（如 backup-20260703-120000）
BACKUP_TAG="backup-20260703-120000"

# 3. 停止当前容器
docker-compose -f docker-compose.prod.yml down

# 4. 恢复备份镜像
docker tag quanlan-analyser-official_backend:${BACKUP_TAG} \
  quanlan-analyser-official_backend:latest
docker tag quanlan-analyser-official_frontend:${BACKUP_TAG} \
  quanlan-analyser-official_frontend:latest

# 5. 启动容器
docker-compose -f docker-compose.prod.yml up -d

# 6. 验证
curl http://localhost/health
```

---

## ❓ 常见问题

### Q1: 容器启动失败，提示端口被占用

**问题**: `bind: address already in use`

**解决方案**:
```bash
# 查看端口占用
netstat -tlnp | grep :80
netstat -tlnp | grep :443

# 停止占用端口的进程
kill -9 <PID>

# 或者修改 docker-compose.prod.yml 中的端口映射
# 将 "80:80" 改为 "8080:80"
```

### Q2: 健康检查失败

**问题**: 容器启动后健康检查一直失败

**解决方案**:
```bash
# 查看后端日志
docker-compose -f docker-compose.prod.yml logs backend

# 进入容器内部调试
docker exec -it qlanalyser-backend bash
curl http://localhost:8000/api/health

# 检查环境变量是否正确
docker exec qlanalyser-backend env | grep QLANALYSER
```

### Q3: 文件上传失败或超时

**问题**: 上传大文件时出现 413 或超时错误

**解决方案**:
```bash
# 检查 nginx.production.conf 中的配置
# client_max_body_size 20g;
# client_body_timeout 3600s;

# 重启 frontend 容器
docker-compose -f docker-compose.prod.yml restart frontend
```

### Q4: OSS 连接失败

**问题**: 后端日志显示 OSS 连接错误

**解决方案**:
```bash
# 验证 OSS 配置
docker exec qlanalyser-backend env | grep OSS

# 测试 OSS 连接（在容器内）
docker exec -it qlanalyser-backend python3 -c "
import oss2
auth = oss2.Auth('your-access-key', 'your-secret-key')
bucket = oss2.Bucket(auth, 'oss-cn-hangzhou.aliyuncs.com', 'your-bucket')
print(bucket.list_objects().object_list)
"

# 检查 RAM 用户权限和 Bucket 配置
```

### Q5: SSL 证书错误

**问题**: 浏览器显示证书不受信任

**解决方案**:
```bash
# 检查证书文件
ls -la ssl/
# 应该有 qlanalyser.pem 和 qlanalyser.key

# 验证证书有效期
openssl x509 -in ssl/qlanalyser.pem -noout -dates

# 验证证书和密钥匹配
openssl x509 -noout -modulus -in ssl/qlanalyser.pem | openssl md5
openssl rsa -noout -modulus -in ssl/qlanalyser.key | openssl md5
# 两个 MD5 值应该相同

# 重启 frontend 容器
docker-compose -f docker-compose.prod.yml restart frontend
```

### Q6: 磁盘空间不足

**问题**: 磁盘使用率 100%

**解决方案**:
```bash
# 检查磁盘使用
df -h

# 查找大文件
du -sh /* | sort -hr | head -10

# 清理 Docker 资源
docker system prune -a -f

# 清理旧日志
find /var/log -name "*.log" -mtime +30 -delete

# 如果使用本地存储，清理旧的上传文件和结果
# 建议迁移到 OSS
```

### Q7: 内存不足，容器被 OOM Kill

**问题**: 容器频繁重启，dmesg 显示 OOM

**解决方案**:
```bash
# 查看内存使用
free -h
docker stats

# 调整容器内存限制（编辑 docker-compose.prod.yml）
# deploy:
#   resources:
#     limits:
#       memory: 4G  # 根据服务器内存调整

# 重新部署
docker-compose -f docker-compose.prod.yml up -d

# 或者升级服务器配置
```

### Q8: 性能问题，响应慢

**问题**: API 响应时间长，页面加载慢

**解决方案**:
```bash
# 1. 检查资源使用
docker stats
htop

# 2. 增加 uvicorn workers（编辑 production.env）
# UVICORN_WORKERS=8  # 根据 CPU 核心数调整

# 3. 启用 Redis 缓存（编辑 docker-compose.prod.yml）
# 取消注释 redis 服务

# 4. 使用 CDN 加速静态资源

# 5. 数据库优化（如使用独立 RDS）

# 6. 考虑使用负载均衡和多实例部署
```

---

## 🔒 安全最佳实践

### 1. 操作系统安全

```bash
# 禁用 root SSH 登录（使用普通用户 + sudo）
vim /etc/ssh/sshd_config
# PermitRootLogin no
systemctl restart sshd

# 配置防火墙
ufw enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# 定期更新系统
apt update && apt upgrade -y
```

### 2. Docker 安全

```bash
# 以非 root 用户运行容器（已在 Dockerfile.backend 中配置）

# 限制容器资源
# 参考 docker-compose.prod.yml 中的 deploy.resources

# 定期更新基础镜像
docker pull python:3.10-slim
docker pull nginx:1.25-alpine
```

### 3. 应用安全

- ✅ 使用强密码和安全的 SECRET_KEY
- ✅ 启用 HTTPS（强制 HTTP 到 HTTPS 重定向）
- ✅ 配置安全 Headers（已在 nginx.production.conf 中配置）
- ✅ 限制 API 文档访问（生产环境建议关闭）
- ✅ 实施速率限制（防止 DDoS）
- ✅ 定期备份数据
- ✅ 监控异常访问和错误日志

### 4. 数据安全

- ✅ 使用 OSS 私有 Bucket
- ✅ 定期备份到异地 Bucket
- ✅ 加密敏感数据
- ✅ 限制 RAM 用户权限（最小权限原则）
- ✅ 定期轮换 AccessKey

### 5. 网络安全

- ✅ 使用阿里云安全组限制访问
- ✅ 仅开放必要端口（80, 443, 22）
- ✅ SSH 仅允许特定 IP 访问
- ✅ 考虑使用 VPN 或堡垒机管理服务器
- ✅ 启用 DDoS 防护（阿里云基础防护）

---

## 📞 技术支持

如有问题，请联系：

- **技术支持邮箱**: support@qlanalyser.online
- **开发团队**: dev@qlanalyser.online
- **紧急热线**: +86-xxx-xxxx-xxxx

---

## 📝 变更记录

| 版本 | 日期 | 变更内容 |
|-----|------|---------|
| 1.0.0 | 2026-07-03 | 初始版本 - 完整的生产环境部署配置 |

---

**祝部署顺利！🎉**
