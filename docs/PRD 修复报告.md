# PRD 文档修复报告

**修复时间**: 2026-05-18 17:30  
**修复人**: COO  
**修复内容**: 法律文书格式修正 + OCR 配置更新

---

## 问题 1: 法律文书格式错误 ❌

### 原描述（错误）
```
法律文书 = PRD 文档
```

### 正确描述 ✅
```
法律文书 = Word 文档（.docx 格式）
PDF 文档（.pdf 格式，用于下载）
```

### 修复说明
- **文书生成**: 生成 Word 文档（.docx）
- **文书下载**: 支持 Word 和 PDF 两种格式
- **文书存储**: 数据库中存储文本内容，文件系统中存储 Word/PDF 文件

### 修复位置
1. `/www/wwwroot/xinclaw-law/docs/心海法律 AI 助手_PRD_V1.1.md`
2. `/www/wwwroot/xinclaw-law/docs/心海法律 AI 助手_PRD_V1.0.md`
3. `/www/wwwroot/xinclaw-law/docs/PRD_终版.md`

---

## 问题 2: OCR 配置不完整 ⚠️

### 当前状态
- ✅ 已安装阿里云 SDK
- ✅ 已配置 DASHSCOPE_API_KEY
- ❌ 未配置百炼大模型（qwen-vl）
- ❌ 代码中使用模拟结果

### 正确配置
**百炼大模型 OCR**:
- 模型：`qwen-vl-max` 或 `qwen2-vl-72b-instruct`
- API: 通义千问视觉模型
- 优势：支持复杂场景文字识别、表格识别、公式识别

### 实现方案
```python
# 使用百炼大模型进行图片识别
from openai import OpenAI

client = OpenAI(
    api_key="sk-xxx",  # 百炼 API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 调用 qwen-vl 模型
response = client.chat.completions.create(
    model="qwen-vl-max",
    messages=[{
        "role": "user",
        "content": [
            {"image": "图片 URL 或 base64"},
            {"text": "请识别图片中的文字内容"}
        ]
    }]
)

ocr_text = response.choices[0].message.content
```

---

## 修复计划

### 1. PRD 文档修复 ✅
**时间**: 17:30-18:00  
**内容**:
- 修正文书格式描述
- 明确 Word 和 PDF 用途
- 更新文档版本

### 2. OCR 配置更新 ⏳
**时间**: 18:00-18:30  
**内容**:
- 配置百炼 API Key
- 更新 config.yaml
- 实现 qwen-vl 调用

### 3. 代码更新 ⏳
**时间**: 18:30-19:00  
**内容**:
- 更新 phase5_input_enhance_v2.py
- 实现百炼 OCR 函数
- 保留开发模式（模拟结果）

---

## 配置对比

| 项目 | 原配置 | 新配置 |
|------|--------|--------|
| OCR 服务 | 阿里云 OCR SDK | 百炼大模型（qwen-vl） |
| 模型 | - | qwen-vl-max / qwen2-vl-72b |
| API Key | 未配置 | 待配置（DASHSCOPE_API_KEY） |
| 识别能力 | 基础 OCR | 复杂场景/表格/公式 |
| 成本 | 按次计费 | 按 Token 计费 |

---

## 待确认事项

1. **百炼 API Key**: 是否需要单独申请？
2. **模型选择**: qwen-vl-max 还是 qwen2-vl-72b？
3. **PRD 版本**: 更新 V1.1 还是 V2.0？

---

**修复人**: COO  
**修复时间**: 2026-05-18 17:30  
**状态**: ⏳ 进行中

---

*心海法律 AI · PRD 修复报告 | 版本：1.0 | 2026-05-18*
