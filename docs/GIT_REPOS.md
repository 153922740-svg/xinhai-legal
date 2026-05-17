# 心海法律 AI - Git 仓库清单

**更新日期**: 2026-05-17 14:00
**负责人**: COO

---

## 📦 仓库列表

### 1. 小程序仓库

| 项目 | 信息 |
|------|------|
| **路径** | `/home/admin/xinclaw-code/miniprogram/` |
| **远程** | `github.com/153922740-svg/xinclaw-miniprogram` |
| **分支** | main |
| **最新提交** | `b4f4b3a` - fix(login): 添加登录调试日志 |
| **状态** | ✅ 已推送（推送失败，需修复远程仓库） |

### 2. API 后端仓库（新建）

| 项目 | 信息 |
|------|------|
| **路径** | `/home/admin/xinhai_legal_api/` |
| **远程** | 待创建 |
| **分支** | main |
| **最新提交** | `7eea1d9` - Initial commit: 心海法律 AI API V1.1.0 |
| **状态** | ✅ 本地已初始化 |

### 3. Hermes Agent 仓库

| 项目 | 信息 |
|------|------|
| **开发环境** | `/home/admin/xinclaw-dev/` |
| **测试环境** | `/home/admin/xinclaw-test/` |
| **状态** | ✅ 已有 Git |

---

## 📝 提交历史

### 小程序

```
b4f4b3a fix(login): 添加登录调试日志，便于排查登录失败问题
b971642 Phase 1-3 完成：新增 chat, dashboard, verification, assistant 页面
```

### API 后端

```
7eea1d9 Initial commit: 心海法律 AI API V1.1.0
```

---

## ⚠️ 待办事项

### 高优先级

- [ ] **创建 API 后端远程仓库**
  - GitHub / Gitee / 私有 Git 服务器
  - 配置 SSH 密钥或访问令牌
  - 推送本地仓库

- [ ] **修复小程序远程仓库**
  - 推送失败：Repository not found
  - 确认仓库是否存在
  - 确认访问权限

### 中优先级

- [ ] 配置 Git hook（可选）
- [ ] 配置 CI/CD（可选）
- [ ] 添加远程仓库备份

---

## 🔐 SSH 密钥配置（如需）

```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "coo@xinclaw.law"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 添加到 GitHub/Gitee
# Settings → SSH and GPG keys → New SSH key
```

---

## 📊 仓库统计

| 仓库 | 提交数 | 文件大小 | 最后更新 |
|------|--------|---------|---------|
| 小程序 | 2 | ~500KB | 2026-05-17 14:00 |
| API 后端 | 1 | ~2MB | 2026-05-17 14:00 |
| Hermes Dev | - | - | - |
| Hermes Test | - | - | - |

---

**最后更新**: 2026-05-17 14:00
