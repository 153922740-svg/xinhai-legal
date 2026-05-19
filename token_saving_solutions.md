# Token 节省优化方案

**版本**: V1.0  
**创建时间**: 2026-05-19  
**目的**: 降低 Token 消耗，提高成本效率

---

## 📊 当前 Token 使用分析

### 消耗场景
| 场景 | Token 消耗 | 占比 | 可优化空间 |
|------|-----------|------|-----------|
| 长上下文传递 | 30-50% | 高 | ✅ 高 |
| 重复代码检索 | 20-30% | 中 | ✅ 高 |
| 完整会话加载 | 15-25% | 中 | ✅ 高 |
| 实际 AI 推理 | 20-30% | 低 | ❌ 低 |

### 问题根因
1. **无压缩传递**: 原始文本直接传给 AI，未压缩
2. **重复检索**: 相同代码/文档多次读取
3. **无缓存机制**: 已分析内容重复分析
4. **上下文冗余**: 传递不必要的前缀/后缀

---

## 🏆 Token 节省方案 (TOP 8)

### 方案 1: 语义压缩 (LLM Lingua) ⭐⭐⭐⭐⭐

**原理**: 删除冗余词，保留核心语义，压缩率 50-80%

```python
from llmlingua import PromptCompressor

compressor = PromptCompressor()
prompt = "这是一段很长的提示词，包含了很多不必要的细节和重复的描述..."
compressed = compressor.compress_prompt(
    prompt,
    target_token=500,  # 压缩到 500 token
    rate=0.5  # 压缩率 50%
)
# 结果："长提示词含不必要细节重复描述..." (保留核心语义)
```

**压缩率**: 50-80%  
**安装**: `pip install llmlingua`  
**适用**: Prompt 压缩/上下文压缩

---

### 方案 2: 响应缓存 ⭐⭐⭐⭐⭐

**原理**: 相同问题直接返回缓存答案，不调用 AI

```python
import hashlib
import sqlite3

def get_cached_response(question: str) -> str:
    """从缓存获取答案"""
    conn = sqlite3.connect('/home/admin/xinhai_legal_api/token_cache.db')
    cursor = conn.cursor()
    
    # 问题哈希
    q_hash = hashlib.md5(question.encode()).hexdigest()
    
    # 查询缓存
    cursor.execute('SELECT response FROM cache WHERE question_hash = ?', (q_hash,))
    row = cursor.fetchone()
    
    if row:
        return row[0]  # 缓存命中，0 token
    return None  # 缓存未命中

def cache_response(question: str, response: str):
    """缓存答案"""
    conn = sqlite3.connect('/home/admin/xinhai_legal_api/token_cache.db')
    cursor = conn.cursor()
    
    q_hash = hashlib.md5(question.encode()).hexdigest()
    cursor.execute('''
        INSERT OR REPLACE INTO cache (question_hash, question, response, created_at)
        VALUES (?, ?, ?, datetime('now'))
    ''', (q_hash, question, response))
    conn.commit()
```

**节省**: 30-50% (重复问题场景)  
**实现**: SQLite 缓存表  
**适用**: FAQ/常见问题/标准答案

---

### 方案 3: 分层检索 ⭐⭐⭐⭐

**原理**: 先检索摘要，再按需读取详情

```
┌─────────────────────────────────────────┐
│  L1: 摘要层 (50-100 token)              │
│  - 文件列表/函数名/类名                 │
│  - 先检索这层，确定目标                 │
├─────────────────────────────────────────┤
│  L2: 详情层 (500-2000 token)            │
│  - 具体代码/文档内容                    │
│  - 只读取 L1 选中的目标                  │
└─────────────────────────────────────────┘
```

**节省**: 60-80% (代码检索场景)  
**实现**: 代码索引 + 按需读取  
**适用**: 代码库检索/文档查询

---

### 方案 4: Diff 式更新 ⭐⭐⭐⭐

**原理**: 只传递变更部分，不传递全文

```python
# ❌ 浪费：传递完整文件
full_code = "def login():\n    # 100 行代码..."

# ✅ 节省：只传递变更
diff = """
@@ -10,7 +10,7 @@
 def login():
-    if user == None:
+    if user is None:
         return False
"""
```

**节省**: 70-90% (代码修改场景)  
**实现**: diff 工具 + patch  
**适用**: 代码修改/文档更新

---

### 方案 5: 批量处理 ⭐⭐⭐⭐

**原理**: 多个问题合并一次调用，不分多次

```python
# ❌ 浪费：多次调用
questions = ["问题 1", "问题 2", "问题 3"]
for q in questions:
    ai_call(q)  # 3 次调用，3 倍 token

# ✅ 节省：一次调用
batch_prompt = """
请回答以下问题：
1. 问题 1
2. 问题 2
3. 问题 3

请依次回答：
"""
ai_call(batch_prompt)  # 1 次调用，节省 50-70%
```

**节省**: 50-70% (多问题场景)  
**适用**: 批量问答/代码审查

---

### 方案 6: Token 计数 + 预警 ⭐⭐⭐

**原理**: 实时计数，超出阈值时压缩

```python
import tiktoken

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """计算 token 数"""
    encoder = tiktoken.encoding_for_model(model)
    return len(encoder.encode(text))

def smart_compress(text: str, max_tokens: int = 4000) -> str:
    """智能压缩"""
    tokens = count_tokens(text)
    
    if tokens <= max_tokens:
        return text  # 无需压缩
    
    # 超出阈值，压缩
    compression_ratio = max_tokens / tokens * 0.9  # 留 10% 余量
    return compress_text(text, compression_ratio)
```

**节省**: 20-40% (防止超限浪费)  
**安装**: `pip install tiktoken`  
**适用**: 所有场景

---

### 方案 7: 关键词检索 ⭐⭐⭐⭐

**原理**: 用关键词代替全文检索

```python
# ❌ 浪费：全文搜索
search_files(pattern="登录.*验证.*密码", path="/code/")

# ✅ 节省：先关键词定位
# 1. 搜索索引 (0 token)
cursor.execute('SELECT file_path FROM code_index WHERE tags MATCH ?', ('登录 验证 密码',))
files = cursor.fetchall()

# 2. 只读取相关文件 (节省 90%)
for file_path in files:
    read_file(file_path)
```

**节省**: 80-95% (检索场景)  
**实现**: SQLite 全文索引  
**适用**: 代码搜索/文档查找

---

### 方案 8: 结构化摘要 ⭐⭐⭐⭐

**原理**: 用结构化格式代替自然语言

```python
# ❌ 浪费：自然语言
summary = """
这个文件是一个用户认证模块，包含了登录函数、注册函数、
密码验证函数、token 生成函数等。登录函数接收用户名和密码，
验证通过后返回 JWT token..."""  # 100+ token

# ✅ 节省：结构化
summary = """
{
  "file": "auth.py",
  "functions": ["login", "register", "verify_password", "generate_token"],
  "dependencies": ["jwt", "bcrypt"],
  "lines": 250
}"""  # 50 token
```

**节省**: 50-70% (摘要场景)  
**适用**: 代码摘要/文档摘要

---

## 📋 实施计划

### 阶段 1: 立即实施 (今天)
- [ ] 安装 tiktoken (Token 计数)
- [ ] 创建响应缓存表 (SQLite)
- [ ] 实现 Token 计数工具
- [ ] 创建代码索引 (用于关键词检索)

### 阶段 2: 本周实施
- [ ] 安装 llmlingua (语义压缩)
- [ ] 实现 Prompt 压缩工具
- [ ] 实现批量处理工具
- [ ] 创建结构化摘要工具

### 阶段 3: 下周实施
- [ ] 实现 Diff 式更新工具
- [ ] 实现分层检索工具
- [ ] Token 使用监控面板
- [ ] 自动压缩阈值配置

---

## 📊 预期效果

| 方案 | 实施难度 | Token 节省 | 优先级 |
|------|---------|-----------|--------|
| 响应缓存 | ⭐ | 30-50% | P0 |
| Token 计数 | ⭐ | 20-40% | P0 |
| 关键词检索 | ⭐⭐ | 80-95% | P0 |
| 语义压缩 | ⭐⭐ | 50-80% | P1 |
| 分层检索 | ⭐⭐ | 60-80% | P1 |
| 批量处理 | ⭐ | 50-70% | P1 |
| Diff 更新 | ⭐⭐⭐ | 70-90% | P2 |
| 结构化摘要 | ⭐⭐ | 50-70% | P2 |

**综合节省**: 60-80% (所有方案实施后)

---

## 🛠️ 工具实现

### Token 计数工具
```python
# /home/admin/xinhai_legal_api/token_optimizer.py
```

### 响应缓存工具
```python
# /home/admin/xinhai_legal_api/response_cache.py
```

### 代码索引工具
```python
# /home/admin/xinhai_legal_api/code_indexer.py
```

---

*报告生成时间：2026-05-19*
