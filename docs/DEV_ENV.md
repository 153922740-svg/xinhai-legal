# 心海法律 AI - 开发环境配置

**版本**: V1.0
**创建日期**: 2026-05-17
**负责人**: COO

---

## 一、环境规划

### 1.1 环境列表

| 环境 | 用途 | 路径 | 状态 |
|------|------|------|------|
| **开发环境** | 日常开发 | `/home/admin/xinhai-legal-dev/` | ⏳ 待搭建 |
| **测试环境** | 集成测试 | `/home/admin/xinhai-legal-test/` | ⏳ 待搭建 |
| **生产环境** | 线上服务 | `/home/admin/xinhai_legal_api/` | ✅ 运行中 |

### 1.2 环境隔离

```
开发环境 → 测试环境 → 生产环境
   ↓           ↓          ↓
 本地修改    自动部署    手动审批
```

---

## 二、开发环境搭建

### 2.1 目录结构

```bash
# 创建开发环境目录
mkdir -p /home/admin/xinhai-legal-dev/{api,miniprogram,docs,logs}

# 复制当前代码到开发环境
cp -r /home/admin/xinhai_legal_api/* /home/admin/xinhai-legal-dev/api/
cp -r /home/admin/xinclaw-code/miniprogram/* /home/admin/xinhai-legal-dev/miniprogram/

# 设置权限
chown -R admin:admin /home/admin/xinhai-legal-dev/
```

### 2.2 开发环境配置

```bash
# 开发环境 API 端口
export FLASK_ENV=development
export FLASK_PORT=5001

# 开发环境数据库
export DB_PATH=/home/admin/xinhai-legal-dev/data/xinhai_legal.db

# 启动开发服务器
cd /home/admin/xinhai-legal-dev/api
source venv/bin/activate
python3 app.py
```

### 2.3 测试环境配置

```bash
# 测试环境 API 端口
export FLASK_ENV=testing
export FLASK_PORT=5002

# 测试环境数据库（独立）
export DB_PATH=/home/admin/xinhai-legal-test/data/xinhai_legal.db
```

---

## 三、Git 仓库管理

### 3.1 仓库列表

| 项目 | 仓库地址 | 状态 |
|------|---------|------|
| 小程序 | github.com/153922740-svg/xinclaw-miniprogram | ✅ 已有 |
| API 后端 | 待创建 | ❌ 未初始化 |
| 文档 | 待创建 | ❌ 未初始化 |

### 3.2 API 后端 Git 初始化

```bash
cd /home/admin/xinhai_legal_api

# 初始化 Git
git init

# 创建.gitignore
cat > .gitignore << EOF
__pycache__/
*.pyc
venv/
*.log
.env
data/*.db
uploads/*
!uploads/.gitkeep
EOF

# 首次提交
git add .
git commit -m "Initial commit: 心海法律 AI API V1.1.0"

# 关联远程仓库（待创建）
# git remote add origin <仓库地址>
# git push -u origin main
```

### 3.3 分支策略

```
main        - 生产分支（受保护）
  ↓
develop     - 开发分支
  ↓
feature/*   - 功能分支
  ↓
hotfix/*    - 紧急修复
```

---

## 四、部署流程

### 4.1 标准部署流程

```bash
# 1. 开发环境测试通过
cd /home/admin/xinhai-legal-dev/api
python3 -m pytest tests/

# 2. 提交代码
git add .
git commit -m "feat: 功能描述"
git push origin feature/xxx

# 3. 创建 Merge Request
# 等待代码审查

# 4. 合并到 develop 分支
# 自动部署到测试环境

# 5. 测试环境验证
# 测试官执行测试用例

# 6. 合并到 main 分支
# 需要 COO/总裁审批

# 7. 生产环境部署
ssh root@8.218.93.213
cd /home/admin/xinhai_legal_api
git pull origin main
systemctl restart xinhai_legal_api
```

### 4.2 紧急修复流程

```bash
# 1. 创建 hotfix 分支
git checkout -b hotfix/bug-xxx main

# 2. 修复问题
# ...

# 3. 快速测试
python3 -m pytest tests/test_critical.py

# 4. COO 审批后合并
git checkout main
git merge hotfix/bug-xxx

# 5. 部署到生产
# ...

# 6. 事后补充文档和测试
```

---

## 五、文档管理

### 5.1 文档目录

```
/home/admin/xinhai_legal_api/docs/
├── PRD/              # 产品需求文档
├── TECH/             # 技术方案
├── API/              # API 文档
├── TEST/             # 测试文档
├── CHANGELOG/        # 变更记录
├── DEPLOY/           # 部署文档
├── DEV_MANAGEMENT.md # 开发管理制度
├── DEV_PROGRESS.md   # 开发进度
└── DEV_ENV.md        # 开发环境（本文件）
```

### 5.2 文档更新要求

- 每次开发前：更新技术方案
- 每次开发后：更新 API 文档
- 每次部署后：更新变更记录
- 每周五：更新进度报告

---

## 六、当前整改任务

| 任务 | 状态 | 负责人 | 截止 |
|------|------|--------|------|
| 创建开发环境目录 | ⏳ 待完成 | COO | 今日 |
| 复制代码到开发环境 | ⏳ 待完成 | COO | 今日 |
| 初始化 API 后端 Git | ⏳ 待完成 | COO | 今日 |
| 创建远程仓库 | ⏳ 待完成 | COO | 明日 |
| 配置 CI/CD | ⏳ 待完成 | COO | 本周 |

---

**本配置自发布之日起执行**

**COO**: ___________  **日期**: ___________
