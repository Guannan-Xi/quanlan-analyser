# QLanalyser 阿里云部署配置清单

## 📦 已生成的部署文件

本次为 QLanalyser 项目生成了完整的阿里云生产环境部署配置。

### 核心部署文件

```
项目根目录/
├── Dockerfile.backend              # 后端服务容器镜像定义
├── Dockerfile.frontend             # 前端Nginx容器镜像定义
├── .dockerignore                   # Docker构建排除文件
├── docker-compose.prod.yml         # 生产环境容器编排配置
│
└── deploy/aliyun/
    ├── README_DEPLOYMENT.md        # 📖 完整部署文档（主文档）
    ├── production.env.template     # 生产环境变量模板
    ├── nginx.production.conf       # Nginx生产环境配置
    ├── monitoring.yml              # 阿里云监控配置指南
    ├── deploy.sh                   # 🚀 一键部署脚本
    ├── rollback.sh                 # ⏮️ 一键回滚脚本
    ├── nginx.single-origin.conf    # (已存在) Staging配置
    └── qlanalyser-v01-staging.env.example  # (已存在) Staging环境变量
```

---

## 🎯 快速开始

### 1. 最小化部署步骤

```bash
# 在阿里云ECS服务器上执行：

# 1. 安装Docker和Docker Compose
curl -fsSL https://get.docker.com | bash

# 2. 克隆或上传代码
cd /opt
git clone <your-repo> quanlan-analyser-official
cd quanlan-analyser-official

# 3. 配置环境变量
cp deploy/aliyun/production.env.template deploy/aliyun/production.env
vim deploy/aliyun/production.env  # 替换所有 CHANGE_ME

# 4. 配置SSL证书
mkdir ssl
# 上传 qlanalyser.pem 和 qlanalyser.key 到 ssl/ 目录

# 5. 一键部署
chmod +x deploy/aliyun/deploy.sh
./deploy/aliyun/deploy.sh
```

### 2. 验证部署

```bash
# 检查容器状态
docker ps

# 健康检查
curl http://localhost/health

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 📋 部署配置说明

### 🐳 Docker 容器化配置

#### **Dockerfile.backend** - 后端服务镜像
- **基础镜像**: Python 3.10 Slim
- **多阶段构建**: 优化镜像体积
- **运行时优化**: 
  - 4 个 Uvicorn workers
  - Uvloop 事件循环
  - 非root用户运行（安全性）
- **健康检查**: 内置 /api/health 检查
- **包含组件**: FastAPI应用 + EEG核心分析库

#### **Dockerfile.frontend** - 前端Nginx镜像
- **基础镜像**: Nginx 1.25 Alpine
- **静态文件**: 包含完整前端应用
- **健康检查**: /health 端点
- **配置挂载**: 支持外部配置文件

#### **docker-compose.prod.yml** - 容器编排
- **服务**:
  - `backend`: FastAPI应用服务器
  - `frontend`: Nginx反向代理 + 静态文件服务
  - `redis`: (可选) 缓存服务
  - `postgres`: (可选) 数据库服务
  - `certbot`: (可选) SSL自动续期

- **特性**:
  - 资源限制（CPU/内存）
  - 健康检查
  - 自动重启
  - 日志轮转
  - 持久化数据卷
  - 独立网络隔离

---

### ⚙️ 环境配置

#### **production.env.template** - 环境变量模板

包含以下配置分类：

1. **应用配置**
   - 运行环境（production）
   - 密钥配置
   - 调试模式

2. **阿里云OSS存储**
   - 主存储 Bucket
   - 备份 Bucket
   - AccessKey 配置
   - 生命周期策略

3. **安全配置**
   - CORS 跨域设置
   - JWT 令牌配置
   - 速率限制
   - 会话管理

4. **第三方服务**
   - 支付服务（支付宝/微信支付）
   - 邮件服务（SMTP）
   - 短信服务（阿里云SMS）
   - 微信OAuth

5. **监控日志**
   - Sentry 错误追踪
   - 日志级别和格式
   - 性能追踪

6. **功能开关**
   - API文档开关
   - 管理功能开关
   - 计费功能开关
   - Demo模式开关

---

### 🌐 Nginx 配置

#### **nginx.production.conf** - 生产环境Nginx配置

**核心特性**:

1. **HTTP/HTTPS 配置**
   - 强制HTTPS重定向
   - HTTP/2 支持
   - SSL/TLS 1.2/1.3
   - 完整的安全头部（HSTS, CSP, X-Frame-Options等）

2. **大文件上传支持**
   - 最大 20GB 文件上传
   - 3600秒超时（支持长时间EEG分析）
   - 禁用请求缓冲（流式上传）

3. **静态资源优化**
   - Gzip 压缩
   - 长期缓存（静态资源1年）
   - 无缓存HTML（支持前端更新）

4. **API 反向代理**
   - 完整的代理头设置
   - Keepalive 连接池
   - 健康检查端点

5. **监控和日志**
   - 访问日志缓冲
   - 错误日志记录
   - 健康检查端点（负载均衡器）

---

### 📊 监控配置

#### **monitoring.yml** - 云监控配置指南

**监控维度**:

1. **ECS 主机监控**
   - CPU 使用率告警（80%/95%）
   - 内存使用率告警（85%/95%）
   - 磁盘使用率告警（80%/90%）
   - 磁盘 IOPS 监控
   - 网络带宽监控

2. **应用层监控**
   - HTTP 可用性（健康检查）
   - API 响应时间（< 3秒）
   - SSL 证书过期提醒（30天/7天）

3. **Docker 容器监控**
   - 容器状态监控
   - 容器资源使用（CPU/内存）

4. **日志监控**
   - 错误日志频率
   - 5xx/4xx 错误统计

5. **业务指标监控**
   - 上传失败率
   - 任务队列积压
   - 活跃用户异常

**告警策略**:
- 分级告警（Warning/Critical）
- 多渠道通知（邮件/短信/电话）
- 告警静默期设置
- 自动恢复通知

---

### 🚀 部署脚本

#### **deploy.sh** - 一键部署脚本

**功能**:
- ✅ 自动检查依赖（Docker/Docker Compose）
- ✅ 验证配置文件（检查未替换的占位符）
- ✅ SSL证书检查
- ✅ 磁盘空间检查（至少10GB）
- ✅ 自动备份当前部署
- ✅ Git集成（可选拉取最新代码）
- ✅ 构建Docker镜像
- ✅ 优雅停止旧容器
- ✅ 启动新容器
- ✅ 健康检查验证（最多重试10次）
- ✅ 自动回滚（如果失败）
- ✅ 显示部署状态和日志
- ✅ 可选清理旧镜像

**使用方式**:
```bash
./deploy/aliyun/deploy.sh
```

#### **rollback.sh** - 一键回滚脚本

**功能**:
- ✅ 列出所有可用的备份版本
- ✅ 交互式选择回滚目标
- ✅ 安全确认机制
- ✅ 自动停止当前服务
- ✅ 恢复备份镜像
- ✅ 启动回滚后的服务
- ✅ 健康检查验证
- ✅ 显示回滚状态

**使用方式**:
```bash
./deploy/aliyun/rollback.sh
```

---

## 🏗️ 架构特点

### 高可用设计

1. **容器编排**
   - Docker Compose 管理多服务
   - 自动重启策略
   - 健康检查自动恢复

2. **负载均衡支持**
   - 支持阿里云SLB接入
   - Nginx upstream 负载均衡
   - 多实例水平扩展

3. **数据持久化**
   - Docker volume 持久化存储
   - 阿里云OSS对象存储
   - 异地备份策略

### 安全设计

1. **网络安全**
   - HTTPS 强制加密
   - 安全头部配置
   - CORS 跨域保护

2. **应用安全**
   - 非root用户运行容器
   - 密钥环境变量管理
   - 最小权限原则（OSS RAM用户）

3. **数据安全**
   - OSS私有Bucket
   - 传输层加密（HTTPS）
   - 定期备份策略

### 性能优化

1. **后端优化**
   - 多进程 Uvicorn workers
   - Uvloop 高性能事件循环
   - OSS直传减轻服务器压力

2. **前端优化**
   - Gzip 压缩
   - 静态资源长期缓存
   - HTTP/2 多路复用

3. **数据库优化**
   - 支持独立RDS实例
   - 连接池配置
   - 索引优化

---

## 📖 文档说明

### **README_DEPLOYMENT.md** - 完整部署文档

**包含章节**:

1. **服务器配置要求**
   - 最低/推荐/高负载配置
   - 存储规划建议

2. **部署前准备**
   - 购买ECS服务器
   - 安全组配置
   - 安装Docker/Docker Compose
   - 配置阿里云OSS

3. **域名和SSL配置**
   - 域名购买和解析
   - 阿里云免费SSL证书申请
   - Let's Encrypt自动化证书

4. **部署步骤**
   - 环境变量配置
   - 部署前检查清单
   - 一键部署命令
   - 手动部署步骤

5. **部署验证**
   - 容器状态检查
   - 健康检查
   - 日志查看
   - 功能测试

6. **运维管理**
   - 常用Docker命令
   - 日志管理
   - 数据备份
   - 更新部署

7. **监控和告警**
   - 阿里云云监控配置
   - Docker监控命令
   - 日志分析

8. **回滚操作**
   - 使用回滚脚本
   - 手动回滚步骤

9. **常见问题**
   - 端口占用
   - 健康检查失败
   - 文件上传问题
   - OSS连接错误
   - SSL证书问题
   - 磁盘空间不足
   - 内存不足
   - 性能问题

10. **安全最佳实践**
    - 操作系统安全
    - Docker安全
    - 应用安全
    - 数据安全
    - 网络安全

---

## ✅ 部署检查清单

在部署前，请确保完成以下项目：

### 服务器准备
- [ ] 购买阿里云ECS服务器（推荐配置：8核16GB）
- [ ] 配置安全组（开放80、443、22端口）
- [ ] 安装Docker和Docker Compose
- [ ] 磁盘空间充足（至少100GB）

### 域名和证书
- [ ] 购买域名（如 qlanalyser.online）
- [ ] 配置域名解析到ECS公网IP
- [ ] 申请SSL证书（阿里云免费或Let's Encrypt）
- [ ] 上传证书文件到 `ssl/` 目录

### 阿里云OSS
- [ ] 创建生产环境Bucket（qlanalyser-prod-data）
- [ ] 创建备份Bucket（qlanalyser-prod-backup）
- [ ] 创建RAM用户并授权OSS访问
- [ ] 记录AccessKey ID和Secret

### 配置文件
- [ ] 复制 `production.env.template` 为 `production.env`
- [ ] 替换所有 `CHANGE_ME` 占位符
- [ ] 生成安全的SECRET_KEY和JWT_SECRET_KEY
- [ ] 配置OSS相关信息
- [ ] 配置CORS域名

### 代码准备
- [ ] 代码已上传到服务器或可通过Git拉取
- [ ] 检查 `requirements.txt` 依赖完整
- [ ] 检查前端文件在 `frontend/` 目录

### 部署脚本
- [ ] 为 `deploy.sh` 和 `rollback.sh` 添加执行权限
- [ ] 验证脚本路径正确

---

## 🔄 更新和维护

### 日常维护任务

**每日**:
- 检查服务运行状态
- 查看错误日志
- 监控资源使用

**每周**:
- 检查磁盘空间
- 清理旧日志和临时文件
- 验证备份完整性

**每月**:
- 更新系统安全补丁
- 更新Docker镜像
- 审查安全日志
- 测试回滚流程

**每季度**:
- 全面性能测试
- 容灾演练
- 安全审计
- 优化配置

### 版本更新流程

1. **测试环境验证**
   ```bash
   # 在测试环境部署新版本
   git checkout <new-version>
   ./deploy/aliyun/deploy.sh
   # 完整功能测试
   ```

2. **生产环境部署**
   ```bash
   # 备份数据
   # 部署新版本
   ./deploy/aliyun/deploy.sh
   # 验证功能
   ```

3. **回滚预案**
   ```bash
   # 如果出现问题
   ./deploy/aliyun/rollback.sh
   ```

---

## 💡 优化建议

### 性能优化

1. **使用CDN加速静态资源**
   - 配置阿里云CDN
   - 缓存前端静态文件
   - 减少源站压力

2. **启用Redis缓存**
   - 编辑 `docker-compose.prod.yml`
   - 取消注释 Redis 服务
   - 配置缓存策略

3. **数据库优化**
   - 使用阿里云RDS
   - 配置读写分离
   - 建立索引优化查询

4. **多实例部署**
   - 使用阿里云SLB负载均衡
   - 部署多台ECS实例
   - 会话共享（Redis）

### 安全加固

1. **启用Web应用防火墙（WAF）**
   - 防止SQL注入
   - 防止XSS攻击
   - 防止DDoS攻击

2. **定期安全扫描**
   - 使用阿里云安全中心
   - 漏洞扫描
   - 基线检查

3. **访问控制**
   - SSH密钥登录
   - 禁用root登录
   - VPN访问管理后台

### 成本优化

1. **按量付费资源**
   - 带宽按流量计费
   - 低频访问存储降级

2. **资源合理配置**
   - 根据实际负载调整实例规格
   - 使用预留实例节省成本

3. **监控和告警**
   - 避免资源浪费
   - 及时发现异常

---

## 🎓 相关资源

### 阿里云官方文档
- [ECS文档](https://help.aliyun.com/product/25365.html)
- [OSS文档](https://help.aliyun.com/product/31815.html)
- [云监控文档](https://help.aliyun.com/product/28572.html)
- [SLB文档](https://help.aliyun.com/product/27537.html)

### Docker文档
- [Docker官方文档](https://docs.docker.com/)
- [Docker Compose文档](https://docs.docker.com/compose/)

### Nginx文档
- [Nginx官方文档](https://nginx.org/en/docs/)

### FastAPI文档
- [FastAPI官方文档](https://fastapi.tiangolo.com/)

---

## 📧 支持

如有问题或需要帮助，请联系：

- **技术支持**: support@qlanalyser.online
- **文档反馈**: 提交 Issue 或 Pull Request

---

**祝您部署顺利！🚀**
