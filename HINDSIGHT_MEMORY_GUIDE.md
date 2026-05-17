# 心海法律 AI - Hindsight Cloud 记忆系统使用指南

## ✅ 已启用

**Hindsight Cloud 长期记忆系统已成功集成！**

---

## 📋 配置信息

| 项目 | 值 |
|------|-----|
| **API URL** | `https://api.hindsight.vectorize.io` |
| **API Key** | `hsk_87ff310d8059c5a1729da76b879abbf5_370e60b8e570220c` |
| **Bank ID** | `xinclaw_coo` |
| **Python 包** | `hindsight-client>=0.6.2` |

---

## 🛠️ 使用方法

### 1. 命令行工具

```bash
cd /home/admin/xinhai_legal_api
source venv/bin/activate

# 写入记忆
python hindsight_memory.py retain "记忆内容" --context "分类"

# 读取记忆
python hindsight_memory.py recall "搜索关键词" --limit 10

# 列出所有记忆
python hindsight_memory.py list --limit 20

# 同步项目状态
python hindsight_memory.py sync
```

### 2. Python 代码

```python
from hindsight_client import Hindsight

hindsight = Hindsight(
    base_url="https://api.hindsight.vectorize.io",
    api_key="hsk_87ff310d8059c5a1729da76b879abbf5_370e60b8e570220c"
)

# 写入记忆
hindsight.retain(
    content="项目状态更新",
    context="project_status",
    bank_id="xinclaw_coo"
)

# 读取记忆
results = hindsight.recall(
    query="心海法律 AI",
    bank_id="xinclaw_coo"
)

# 列出记忆
results = hindsight.list_memories(
    bank_id="xinclaw_coo",
    limit=20
)
```

---

## 📊 当前记忆内容

### 已存储的记忆类型

| 分类 | 说明 | 数量 |
|------|------|------|
| `project_status` | 项目进度状态 | ~5 条 |
| `pending_tasks` | 待办事项 | ~5 条 |
| `server_config` | 服务器配置 | ~2 条 |
| `system_integration` | 系统集成记录 | ~2 条 |
| `general` | 其他记忆 | ~7 条 |
| **总计** | | **~21 条** |

### 示例记忆内容

```
[project_status] 心海法律 AI 项目已完成 15 个阶段（Phase 2-11,13），代码量超过 24 万行。
[pending_tasks] 心海法律 AI 待办：1) Phase 3 合同审阅开发 2) 小程序登录修复 3) 图片识别 API 401 修复
[server_config] 心海法律 AI 服务器：8.218.93.213 (root), API 路径 /home/admin/xinhai_legal_api
```

---

## 🔄 与桌面助理共享

### 方案 1: Hindsight Cloud（推荐）

**优点**:
- ✅ 云端存储，永久保存
- ✅ 自动语义搜索和关联
- ✅ COO 和桌面助理共享同一记忆库
- ✅ 支持自然语言查询

**使用**:
```bash
# COO 写入
python hindsight_memory.py retain "内容" --context "分类"

# 桌面助理读取
python hindsight_memory.py recall "关键词"
```

### 方案 2: 本地共享文件（备用）

**文件位置**: `/home/admin/xinhai_legal_api/SHARED_MEMORY.json`

**优点**:
- ✅ 无需 API 调用
- ✅ 即时读写

**缺点**:
- ❌ 无语义搜索
- ❌ 需要手动同步

---

## 📝 最佳实践

### 1. 记忆分类

使用有意义的 `context` 分类：
- `project_status` - 项目状态
- `pending_tasks` - 待办事项
- `server_config` - 服务器配置
- `api_docs` - API 文档
- `user_preferences` - 用户偏好
- `meeting_notes` - 会议记录

### 2. 记忆内容格式

```
[主题] 具体内容。| When: 日期 | 相关方
```

示例：
```
心海法律 AI 项目已完成 Phase 2-11 和 13。| When: 2026-05-17 | xinclaw_coo
```

### 3. 定期同步

建议每 30 分钟或任务完成后同步：
```bash
python hindsight_memory.py sync
```

---

## 🔧 故障排查

### 问题 1: 认证失败

```
TypeError: Hindsight.__init__() got an unexpected keyword argument 'api_url'
```

**解决**: 使用 `base_url` 而不是 `api_url`

### 问题 2: 连接超时

```
aiohttp.client_exceptions.ClientConnectorError
```

**解决**: 检查网络连接，增加 timeout

### 问题 3: 记忆未找到

**解决**: 
1. 确认 `bank_id` 正确
2. 尝试不同的搜索关键词
3. 使用 `list` 命令查看所有记忆

---

## 📚 参考资料

- **官方文档**: https://ui.hindsight.vectorize.io
- **PyPI 包**: https://pypi.org/project/hindsight-client/
- **GitHub**: https://github.com/vectorize-io/hindsight

---

*最后更新：2026-05-17 18:50*
