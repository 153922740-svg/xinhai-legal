# 心海法律 AI - 生产环境部署清单

**部署版本**: V1.2.0  
**部署日期**: 待确认  
**部署负责人**: 磐石（运维官）  
**审批人**: COO + 总裁

---

## 📋 部署前检查

### 1. 代码检查
- [x] Phase 1-16 开发完成
- [x] 单元测试通过率 100% (22/22)
- [x] 代码审查完成 (16 个 Phase)
- [x] Git 提交已推送
- [ ] 端到端测试（需服务启动）

### 2. 安全检查
- [x] 无硬编码密钥
- [x] SQL 注入检查通过
- [x] XSS 风险检查通过
- [x] 认证鉴权完整
- [ ] 依赖漏洞扫描（待执行）

### 3. 文档检查
- [x] 需求文档 (16 个)
- [x] 技术方案 (16 个)
- [x] 测试报告 (16 个)
- [x] 代码审查 (16 个)
- [x] 部署记录
- [x] 变更管理日志

---

## 🚀 部署步骤

### 步骤 1: 备份现有环境
```bash
# 备份数据库
cp /root/xinhai-legal/data/xinhai_legal.db /home/admin/xinclaw-backup/xinhai_legal_$(date +%Y%m%d_%H%M%S).db

# 备份代码
cd /home/admin/xinhai_legal_api
git archive -o /home/admin/xinclaw-backup/code_$(date +%Y%m%d_%H%M%S).tar main
```

### 步骤 2: 更新代码
```bash
cd /home/admin/xinhai_legal_api
git pull origin main
```

### 步骤 3: 安装依赖
```bash
source venv/bin/activate
pip install -r requirements.txt
pip install bandit safety  # 安全工具
```

### 步骤 4: 数据库迁移
```bash
# Phase 14 数据库迁移
sqlite3 /root/xinhai-legal/data/xinhai_legal.db < migrations/phase14_migration.sql
```

### 步骤 5: 启动服务
```bash
# 停止旧服务
sudo systemctl restart xinclaw-api

# 检查服务状态
sudo systemctl status xinclaw-api
```

### 步骤 6: 验证服务
```bash
# 健康检查
curl http://localhost:8081/health

# 测试核心 API
curl http://localhost:8081/api/v1/dashboard/overview
```

### 步骤 7: Nginx 配置验证
```bash
# 测试配置
sudo nginx -t

# 重载配置
sudo nginx -s reload
```

---

## 🔧 环境配置

### 生产环境变量
```bash
# /home/admin/xinhai_legal_api/.env
DATABASE_URL=/root/xinhai-legal/data/xinhai_legal.db
SECRET_KEY=<生产密钥>
API_KEY=<生产 API 密钥>
DEBUG=false
```

### Nginx 配置
```nginx
# /etc/nginx/conf.d/xinclaw.conf
server {
    listen 80;
    server_name xinclaw.xhacca.cn;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name xinclaw.xhacca.cn;
    
    ssl_certificate /etc/letsencrypt/live/xinclaw.xhacca.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xinclaw.xhacca.cn/privkey.pem;
    
    location /api/ {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location / {
        root /var/www/xinclaw-chat;
        index index.html;
    }
}
```

---

## 📊 监控配置

### 服务监控
- [ ] API 响应时间监控
- [ ] 错误率监控
- [ ] CPU/内存使用率监控
- [ ] 数据库连接数监控

### 告警配置
- [ ] API 错误率 > 1% 告警
- [ ] 响应时间 P95 > 500ms 告警
- [ ] 服务宕机告警
- [ ] 磁盘空间 < 20% 告警

---

## 🔄 回滚方案

### 回滚条件
- 严重 Bug 影响核心功能
- 性能严重下降
- 安全漏洞

### 回滚步骤
```bash
# 1. 停止服务
sudo systemctl stop xinclaw-api

# 2. 恢复代码
cd /home/admin/xinhai_legal_api
git reset --hard <previous_commit>

# 3. 恢复数据库
cp /home/admin/xinclaw-backup/xinhai_legal_YYYYMMDD_HHMMSS.db /root/xinhai-legal/data/xinhai_legal.db

# 4. 重启服务
sudo systemctl start xinclaw-api

# 5. 验证服务
curl http://localhost:8081/health
```

---

## ✅ 验收标准

| 检查项 | 标准 | 验证方法 |
|--------|------|----------|
| 服务启动 | 无错误 | systemctl status |
| API 响应 | < 200ms | curl 测试 |
| 数据库 | 连接正常 | 查询测试 |
| 前端 | 页面可访问 | 浏览器访问 |
| HTTPS | 证书有效 | 浏览器检查 |

---

## 📝 部署记录

| 版本 | 日期 | 部署人 | 结果 | 备注 |
|------|------|--------|------|------|
| V1.2.0 | 待部署 | 磐石 | ⏳ | Phase 1-16 完成 |
| V1.1.0 | 2026-05-17 | 磐石 | ✅ | Phase 1-13 完成 |
| V1.0.0 | 2026-05-16 | 磐石 | ✅ | 初始版本 |

---

**审批**:
- [ ] COO 审核
- [ ] 总裁审批

**维护人**: 磐石（运维官）  
**最后更新**: 2026-05-18
