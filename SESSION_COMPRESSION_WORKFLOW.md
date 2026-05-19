# 会话压缩存储工作流程

**版本**: V1.0  
**创建时间**: 2026-05-18  
**用途**: 防止 COO 失忆，跨会话保留完整对话历史

---

## 📋 问题背景

### Claude Code 的优势
- 100 万 + token 上下文
- 整个代码库在记忆中
- 之前的对话全部保留
- 不会丢失任何修复记录

### 我的限制
- 本地 Memory: 32,000 字符（约 20-25 条条目）
- 会话切换丢失上下文
- 修复记录容易丢失

### 解决方案
```
会话内容 → gzip 压缩 (40-60% 压缩率) → base64 编码 → Hindsight 云记忆 (无限制)
```

---

## 🛠️ 技术实现

### 压缩工具
- **压缩算法**: gzip (Python 标准库)
- **编码方式**: base64 (便于 JSON 存储)
- **压缩率**: 40-60% (文本类内容)

### 存储架构
```
┌─────────────────────────────────────────────────────────┐
│  会话数据存储架构                                      │
├─────────────────────────────────────────────────────────┤
│  L1·索引层 (本地 Memory)                               │
│  - 会话数量/日期范围/关键主题                          │
│  - 压缩文件大小/压缩率                                 │
│  - 文件路径索引                                        │
├─────────────────────────────────────────────────────────┤
│  L2·压缩存档 (文件系统)                                │
│  - /home/admin/xinhai_legal_api/sessions_archive.json │
│  - gzip + base64 压缩数据                              │
│  - 包含元数据 (大小/日期/会话数)                       │
├─────────────────────────────────────────────────────────┤
│  L3·云记忆 (Hindsight)                                 │
│  - bank_id: xinclaw_coo                                │
│  - 无限制容量                                          │
│  - 支持语义/实体/时间多策略检索                        │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 操作流程

### 会话结束时执行

```bash
# 1. 运行压缩脚本
python3 /home/admin/xinhai_legal_api/compress_sessions.py

# 2. 验证压缩结果
cat /home/admin/xinhai_legal_api/sessions_archive.json

# 3. 存入 Hindsight (curl 调用 API)
curl -X POST https://api.hindsight.vectorize.io/retain \
  -H "Authorization: Bearer $HINDSIGHT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "bank_id": "xinclaw_coo",
    "content": "会话压缩存档...",
    "metadata": {"type": "sessions_archive", "date": "2026-05-18"}
  }'

# 4. 更新本地 Memory 索引
# (手动添加 Memory 条目，包含压缩文件路径和摘要)
```

### 会话开始时执行

```bash
# 1. 运行会话初始化脚本
bash /home/admin/coo_session_init.sh

# 2. 从 Hindsight 检索历史会话
curl -X POST https://api.hindsight.vectorize.io/recall \
  -H "Authorization: Bearer $HINDSIGHT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "bank_id": "xinclaw_coo",
    "query": "历史会话 修复记录",
    "top_k": 5
  }'

# 3. 解压会话数据 (如需要)
python3 /home/admin/xinhai_legal_api/decompress_sessions.py

# 4. 向总裁汇报当前问题清单
```

---

## 📂 文件清单

| 文件 | 路径 | 用途 |
|------|------|------|
| 压缩脚本 | `/home/admin/xinhai_legal_api/compress_sessions.py` | 会话压缩 |
| 解压脚本 | `/home/admin/xinhai_legal_api/decompress_sessions.py` | 会话解压 |
| 压缩存档 | `/home/admin/xinhai_legal_api/sessions_archive.json` | 存储压缩数据 |
| 初始化脚本 | `/home/admin/coo_session_init.sh` | 会话开始加载 |
| 问题追踪 | `/home/admin/xinhai_legal_api/ISSUES_TRACKING.md` | 问题清单 |

---

## 🔍 检索示例

### 从 Hindsight 检索历史修复记录

```python
import requests

response = requests.post(
    "https://api.hindsight.vectorize.io/recall",
    headers={
        "Authorization": "Bearer <API_KEY>",
        "Content-Type": "application/json"
    },
    json={
        "bank_id": "xinclaw_coo",
        "query": "bug 修复 API 数据库",
        "top_k": 5,
        "strategies": ["semantic", "entity", "temporal"]
    }
)

results = response.json()
for item in results['memories']:
    print(f"日期：{item['timestamp']}")
    print(f"内容：{item['content'][:200]}...")
```

### 解压会话存档

```python
import gzip
import base64
import json

with open('/home/admin/xinhai_legal_api/sessions_archive.json') as f:
    data = json.load(f)

compressed = base64.b64decode(data['compressed_data'])
decompressed = gzip.decompress(compressed)
sessions = json.loads(decompressed)

print(f"解压完成：{len(sessions)} 个会话")
for s in sessions:
    print(f"  - {s['session_id']}: {s['summary']}")
```

---

## 📊 压缩效果

| 指标 | 数值 |
|------|------|
| 原始大小 | ~1,000 字节/会话 |
| 压缩后 | ~400-600 字节/会话 |
| 压缩率 | 40-60% |
| 100 个会话 | ~50KB (压缩后) |
| Hindsight 容量 | 无限制 |

---

## ⚠️ 注意事项

1. **定期归档**: 每 5-10 次会话执行一次压缩归档
2. **元数据完整**: 压缩文件必须包含日期/会话数/压缩率等元数据
3. **双重存储**: 同时存储到文件系统 + Hindsight 云记忆
4. **本地索引**: Memory 中只存索引，不存完整压缩数据
5. **检索优化**: 使用关键词标签便于后续检索

---

## 📋 使用场景

### 场景 1: 会话开始恢复上下文
```
总裁："继续昨天的工作"
→ 运行 coo_session_init.sh
→ 从 Hindsight 检索历史会话
→ 向总裁汇报当前进度和问题清单
```

### 场景 2: 查找历史修复记录
```
总裁："上次登录接口的问题是怎么修复的？"
→ 从 Hindsight 检索"登录 修复 API"
→ 解压相关会话
→ 向总裁汇报修复方案
```

### 场景 3: 代码问题追踪
```
发现问题 → 记录到 ISSUES_TRACKING.md → 存入 Hindsight → 修复 → 验证 → 更新状态
```

---

*本流程由 COO 维护，确保跨会话记忆不丢失*
