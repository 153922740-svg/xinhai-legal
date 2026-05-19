
# 本地长记忆解决方案调研报告

**调研时间**: 2026-05-19  
**调研目的**: 寻找无限制的本地长记忆方案，替代/补充 Hindsight 云记忆

---

## 📊 现有环境分析

### 已安装可用
| 方案 | 状态 | 说明 |
|------|------|------|
| SQLite | ✅ 可用 | Python 内置，无需安装 |
| JSONL 文件 | ✅ 已有 | /home/admin/.hermes/sessions/ (177MB+) |
| Pickle | ✅ 可用 | Python 内置序列化 |
| MessagePack | ✅ 已安装 | v1.1.2，高效二进制序列化 |

### 需安装
| 方案 | 状态 | 安装命令 |
|------|------|---------|
| ChromaDB | ❌ 未安装 | pip install chromadb |
| FAISS | ❌ 未安装 | pip install faiss-cpu |
| DuckDB | ❌ 未安装 | pip install duckdb |
| TinyDB | ❌ 未安装 | pip install tinydb |
| Qdrant | ❌ 未安装 | pip install qdrant-client |
| LanceDB | ❌ 未安装 | pip install lancedb |

### 不可用/不适合
| 方案 | 状态 | 原因 |
|------|------|------|
| Redis | ❌ 未安装 | 需要额外服务 |
| MongoDB | ❌ 未安装 | 需要额外服务 |
| LMDB | ❌ 未安装 | 需要安装 |
| HDF5 | ❌ 未安装 | 适合科学数据 |
| Parquet | ❌ 未安装 | 适合分析场景 |

---

## 🏆 推荐方案 (TOP 5)

### 方案 1: SQLite + 全文搜索 ⭐⭐⭐⭐⭐

**优势**:
- ✅ Python 内置，无需安装
- ✅ 无容量限制 (GB 级别)
- ✅ 支持 SQL 查询
- ✅ 支持 FTS5 全文搜索
- ✅ 单文件存储，便于备份
- ✅ 事务安全，ACID 兼容

**劣势**:
- ❌ 不支持向量搜索 (需额外扩展)
- ❌ 并发写入有限制

**适用场景**: 会话存储/问题追踪/代码索引

**实现示例**:
```python
import sqlite3

conn = sqlite3.connect('/home/admin/xinhai_legal_api/long_term_memory.db')
cursor = conn.cursor()

# 创建表
cursor.execute('''
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        timestamp DATETIME,
        content TEXT,
        metadata TEXT,
        tags TEXT
    )
''')

# 创建全文索引
cursor.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
        content,
        content_rowid=id
    )
''')

# 插入数据
cursor.execute('''
    INSERT INTO memories (session_id, timestamp, content, metadata, tags)
    VALUES (?, ?, ?, ?, ?)
''', (session_id, timestamp, content, json.dumps(metadata), tags))

# 全文搜索
cursor.execute('''
    SELECT * FROM memories WHERE content MATCH ?
''', (search_query,))
```

---

### 方案 2: JSONL 文件 + gzip 压缩 ⭐⭐⭐⭐

**优势**:
- ✅ 无需安装，纯文件存储
- ✅ 无容量限制 (取决于磁盘)
- ✅ 人类可读 (解压后)
- ✅ 易于追加写入
- ✅ 已有基础设施 (/home/admin/.hermes/sessions/)

**劣势**:
- ❌ 查询效率低 (需全文件扫描)
- ❌ 不支持随机访问
- ❌ 需要额外索引机制

**适用场景**: 会话归档/批量存储/冷数据

**实现示例**:
```python
import json
import gzip

# 写入 (追加模式)
with gzip.open('/home/admin/xinhai_legal_api/memories.jsonl.gz', 'at') as f:
    f.write(json.dumps(memory_entry, ensure_ascii=False) + '\n')

# 读取 (逐行解析)
with gzip.open('/home/admin/xinhai_legal_api/memories.jsonl.gz', 'rt') as f:
    for line in f:
        entry = json.loads(line)
        # 处理 entry
```

---

### 方案 3: ChromaDB (本地嵌入) ⭐⭐⭐⭐

**优势**:
- ✅ 向量搜索 (语义检索)
- ✅ 本地运行，无需云服务
- ✅ 自动嵌入 (支持 sentence-transformers)
- ✅ 支持元数据过滤
- ✅ API 友好

**劣势**:
- ❌ 需要安装 (pip install chromadb)
- ❌ 内存占用较大
- ❌ 首次使用需下载嵌入模型

**适用场景**: 语义检索/相似问题查找/知识检索

**实现示例**:
```python
import chromadb
from chromadb.config import Settings

client = chromadb.Client(Settings(
    persist_directory="/home/admin/xinhai_legal_api/chroma_db"
))

collection = client.create_collection("memories")

# 添加记忆
collection.add(
    documents=["会话内容..."],
    metadatas=[{"session_id": "xxx", "type": "conversation"}],
    ids=["mem_001"]
)

# 语义搜索
results = collection.query(
    query_texts=["登录问题怎么修复"],
    n_results=5
)
```

---

### 方案 4: MessagePack + 文件系统 ⭐⭐⭐

**优势**:
- ✅ 已安装 (msgpack v1.1.2)
- ✅ 比 JSON 更小 (约 30-50%)
- ✅ 比 Pickle 更安全
- ✅ 跨语言兼容
- ✅ 支持流式处理

**劣势**:
- ❌ 二进制格式，人类不可读
- ❌ 不支持查询 (需配合索引)

**适用场景**: 高效存储/序列化/网络传输

**实现示例**:
```python
import msgpack

# 序列化
packed = msgpack.packb(memory_entry, use_bin_type=True)

# 存储
with open('/home/admin/xinhai_legal_api/memory.msgpack', 'wb') as f:
    f.write(packed)

# 反序列化
with open('/home/admin/xinhai_legal_api/memory.msgpack', 'rb') as f:
    entry = msgpack.unpackb(f.read(), raw=False)
```

---

### 方案 5: SQLite + MessagePack 混合 ⭐⭐⭐⭐⭐

**优势**:
- ✅ SQLite 的查询能力
- ✅ MessagePack 的高效存储
- ✅ 元数据/索引存 SQLite
- ✅ 大内容存 MessagePack 文件
- ✅ 最佳性能组合

**劣势**:
- ❌ 实现复杂度稍高

**适用场景**: 大规模记忆存储/生产环境

**实现示例**:
```python
# 索引存 SQLite
cursor.execute('''
    INSERT INTO memory_index (id, timestamp, tags, content_path)
    VALUES (?, ?, ?, ?)
''', (mem_id, timestamp, tags, f"/memories/{mem_id}.msgpack"))

# 内容存 MessagePack
with open(f"/home/admin/xinhai_legal_api/memories/{mem_id}.msgpack", 'wb') as f:
    f.write(msgpack.packb(content, use_bin_type=True))
```

---

## 📋 方案对比表

| 方案 | 容量 | 查询 | 语义搜索 | 安装 | 推荐度 |
|------|------|------|---------|------|--------|
| SQLite | ∞ | ✅ SQL | ❌ | 内置 | ⭐⭐⭐⭐⭐ |
| JSONL+gzip | ∞ | ❌ 扫描 | ❌ | 内置 | ⭐⭐⭐⭐ |
| ChromaDB | ∞ | ✅ 向量 | ✅ | 需安装 | ⭐⭐⭐⭐ |
| MessagePack | ∞ | ❌ | ❌ | 已有 | ⭐⭐⭐ |
| SQLite+MPack | ∞ | ✅ SQL | ❌ | 内置 | ⭐⭐⭐⭐⭐ |
| Redis | ∞ | ✅ K/V | ❌ | 需服务 | ⭐⭐ |
| MongoDB | ∞ | ✅ 文档 | ❌ | 需服务 | ⭐⭐ |
| FAISS | ∞ | ✅ 向量 | ✅ | 需安装 | ⭐⭐⭐ |

---

## 🎯 最终推荐

### 最佳组合方案

```
┌─────────────────────────────────────────────────────────┐
│  心海法律 AI 本地长记忆架构                            │
├─────────────────────────────────────────────────────────┤
│  L1·热记忆 (本地 Memory 32KB)                          │
│  - 核心配置/当前任务/进度状态                          │
│  - 使用 Hermes memory 工具                             │
├─────────────────────────────────────────────────────────┤
│  L2·温记忆 (SQLite + FTS5)                             │
│  - 问题追踪/修复记录/代码索引                          │
│  - 路径：/home/admin/xinhai_legal_api/long_term_memory.db |
│  - 支持全文搜索/SQL 查询/元数据过滤                     │
├─────────────────────────────────────────────────────────┤
│  L3·凉记忆 (JSONL + gzip)                              │
│  - 完整会话归档/批量数据                               │
│  - 路径：/home/admin/xinhai_legal_api/sessions_archive/ |
│  - 按日期分片，压缩存储                                 │
├─────────────────────────────────────────────────────────┤
│  L4·向量检索 (ChromaDB - 可选)                         │
│  - 语义检索/相似问题查找                               │
│  - 路径：/home/admin/xinhai_legal_api/chroma_db/       │
│  - 用于"类似问题怎么解决"场景                           │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 实施计划

### 阶段 1: SQLite 基础 (立即执行)
- [ ] 创建数据库表结构
- [ ] 实现插入/查询接口
- [ ] 配置 FTS5 全文搜索
- [ ] 迁移现有 Memory 条目

### 阶段 2: JSONL 归档 (本周内)
- [ ] 创建会话归档目录
- [ ] 实现 gzip 压缩存储
- [ ] 建立日期分片机制
- [ ] 实现批量导入导出

### 阶段 3: ChromaDB 增强 (可选)
- [ ] 安装 ChromaDB
- [ ] 配置本地嵌入模型
- [ ] 建立向量索引
- [ ] 实现语义检索

---

*报告生成时间：2026-05-19*
