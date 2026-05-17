# 心海法律 AI - 部署记录

**文档编号**: DEPLOY-LOG-V1.0  
**创建日期**: 2026-05-18  
**负责人**: 磐石（运维官）  
**状态**: active

---

## 1. 环境信息

### 1.1 服务器配置

| 环境 | IP 地址 | 用途 | 配置 |
|------|---------|------|------|
| 生产环境 | 8.218.93.213 | 线上服务 | 1 核 2G |
| 测试环境 | local | 测试验证 | 本地开发 |

### 1.2 软件环境

| 软件 | 版本 | 说明 |
|------|------|------|
| 操作系统 | Ubuntu 22.04 LTS | 服务器系统 |
| Python | 3.11.x | 运行环境 |
| Nginx | latest | 反向代理 |
| SQLite | 3.x | 数据库 |

---

## 2. 部署历史

### 2.1 V1.0.0 - 初始版本 (2026-05-16)

**部署时间**: 2026-05-16 18:00  
**部署人**: 磐石  
**版本**: V1.0.0

**部署内容**:
- 心海法律 AI API V1.1.0
- 小程序代码 33 个页面
- H5 前端页面
- Nginx 配置

**部署步骤**:
```bash
# 1. 代码部署
cd /home/admin/xinhai_legal_api
git pull origin main

# 2. 安装依赖
pip install -r requirements.txt

# 3. 数据库初始化
python init_database.py

# 4. 启动服务
python app/main.py

# 5. Nginx 配置
sudo nginx -t
sudo nginx -s reload
```

**验证结果**: ✅ 通过

---

### 2.2 V1.1.0 - Phase 1-13 完成 (2026-05-17)

**部署时间**: 2026-05-17 19:30  
**部署人**: 磐石  
**版本**: V1.1.0

**部署内容**:
- Phase 1-13 全部代码
- 会员与计费系统
- AI 核心功能
- 用户认证系统

**变更内容**:
```
feat(phase2): 完成会员与计费系统开发
feat(phase3): 完成合同审阅模块开发
feat(phase3): 实现 AI 对话接口
```

**部署步骤**:
```bash
# 1. 备份数据库
cp /root/xinhai-legal/data/xinhai_legal.db /home/admin/xinclaw-backup/

# 2. 代码更新
cd /home/admin/xinhai_legal_api
git pull origin main

# 3. 重启服务
sudo systemctl restart xinclaw-api

# 4. 验证服务
curl http://localhost:8081/health
```

**验证结果**: ✅ 通过

---

### 2.3 V1.2.0 - 整改版本 (2026-05-18)

**部署时间**: 2026-05-18 {HH}:MM  
**部署人**: 磐石  
**版本**: V1.2.0

**部署内容**:
- 补充需求分析文档 (13 个)
- 补充技术方案文档 (13 个)
- 补充测试报告 (13 个)
- 补充代码审查报告 (13 个)

**变更内容**:
```
docs: 补充 Phase 1-13 需求分析文档
docs: 补充 Phase 1-13 技术方案文档
docs: 补充 Phase 1-13 测试报告
docs: 补充 Phase 1-13 代码审查报告
```

**部署步骤**:
```bash
# 1. 文档更新
cp docs/requirements_phase*.md /www/wwwroot/xinclaw-law/docs/
cp docs/tech_design_phase*.md /www/wwwroot/xinclaw-law/docs/
cp docs/test_report_phase*.md /www/wwwroot/xinclaw-law/docs/

# 2. Git 提交
git add docs/
git commit -m "docs: 补充开发管理制度文档"
git push origin main
```

**验证结果**: ⏳ 待验证

---

## 3. 回滚方案

### 3.1 回滚条件

- 严重 Bug 影响核心功能
- 性能严重下降
- 安全漏洞

### 3.2 回滚步骤

```bash
# 1. 停止服务
sudo systemctl stop xinclaw-api

# 2. 恢复代码
cd /home/admin/xinhai_legal_api
git reset --hard <previous_commit>

# 3. 恢复数据库
cp /home/admin/xinclaw-backup/xinhai_legal.db /root/xinhai-legal/data/

# 4. 重启服务
sudo systemctl start xinclaw-api

# 5. 验证服务
curl http://localhost:8081/health
```

---

## 4. 监控指标

### 4.1 服务监控

| 指标 | 阈值 | 当前值 | 状态 |
|------|------|--------|------|
| API 响应时间 | < 200ms | {XX}ms | ✅ |
| 错误率 | < 0.1% | {X}% | ✅ |
| CPU 使用率 | < 80% | {XX}% | ✅ |
| 内存使用率 | < 80% | {XX}% | ✅ |

### 4.2 日志位置

| 日志类型 | 路径 | 轮转策略 |
|----------|------|----------|
| 应用日志 | /var/log/xinclaw/api.log | 每日轮转 |
| Nginx 日志 | /var/log/nginx/access.log | 每日轮转 |
| 错误日志 | /var/log/nginx/error.log | 每日轮转 |

---

## 5. 变更记录

| 版本 | 日期 | 变更人 | 变更内容 |
|------|------|--------|----------|
| V1.2.0 | 2026-05-18 | 磐石 | 补充开发管理制度文档 |
| V1.1.0 | 2026-05-17 | 磐石 | Phase 1-13 完成 |
| V1.0.0 | 2026-05-16 | 磐石 | 初始版本部署 |

---

**审批**:
- [ ] COO 审核
- [ ] 总裁审批（重大变更）

**维护人**: 磐石（运维官）  
**最后更新**: 2026-05-18
