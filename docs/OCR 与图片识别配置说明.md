# 心海法律 AI - OCR 与图片识别配置说明

**更新时间**: 2026-05-18 17:45  
**更新人**: COO

---

## 📊 配置总览

| 功能 | 服务商 | 模型/SDK | 用途 | 状态 |
|------|--------|---------|------|------|
| **OCR 文字提取** | 阿里云 | Green SDK | 提取图片中的文字 | ✅ 已配置 |
| **图片理解识别** | 百炼 | qwen-vl-max | 理解图片内容、场景 | ✅ 已配置 |
| **语音识别** | 阿里云 | NLS SDK | 语音转文字 | ✅ 已配置 |

---

## 1. OCR 文字提取（阿里云）

### 配置
```python
# 阿里云 Green SDK
aliyun-python-sdk-green==3.6.6

# API 配置
ALIYUN_ACCESS_KEY_ID=<your-access-key-id>
ALIYUN_ACCESS_KEY_SECRET=<your-access-key-secret>
```

### 函数
```python
def ocr_aliyun(image_path):
    """
    调用阿里云 Green SDK 进行 OCR 文字提取
    用于提取图片中的文字内容
    """
```

### 使用场景
- 身份证识别
- 营业执照识别
- 合同文档文字提取
- 票据识别

---

## 2. 图片理解识别（百炼）

### 配置
```python
# 百炼大模型 SDK
openai==1.12.0

# API 配置
DASHSCOPE_API_KEY=sk-xxx
BAILOAN_MODEL=qwen-vl-max
```

### 函数
```python
def recognize_image_bailian(image_path):
    """
    调用百炼大模型进行图片理解识别
    用于理解图片内容、场景、物体等
    """
```

### 使用场景
- 图片内容描述
- 场景识别
- 物体识别
- 图片中的文字 + 上下文理解

---

## 🔧 代码实现

### phase5_input_enhance_v2.py

```python
# 导入 SDK
from aliyunsdkcore.client import AcsClient
from aliyunsdkgreen.request.v20180509 import ImageSyncDetectRequest
from openai import OpenAI

# OCR 文字提取（阿里云）
def ocr_aliyun(image_path):
    client = AcsClient(
        ALIYUN_ACCESS_KEY_ID,
        ALIYUN_ACCESS_KEY_SECRET,
        'cn-shanghai'
    )
    request = ImageSyncDetectRequest.ImageSyncDetectRequest()
    # ... 实现 OCR 逻辑

# 图片理解（百炼）
def recognize_image_bailian(image_path):
    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    response = client.chat.completions.create(
        model="qwen-vl-max",
        messages=[{
            "role": "user",
            "content": [
                {"image": "base64 图片数据"},
                {"text": "请描述这张图片的内容"}
            ]
        }]
    )
```

---

## 📝 开发模式

当前使用开发模式（`DEV_MODE = True`）：
- OCR 返回模拟结果："图片中的文字内容..."
- 图片识别返回模拟结果
- 不产生费用

切换到生产模式（`DEV_MODE = False`）：
- 调用真实 API
- 产生费用（OCR 约 0.05 元/次，图片识别按 Token 计费）

---

## 💰 费用对比

| 服务 | 计费方式 | 单价 | 适用场景 |
|------|---------|------|---------|
| 阿里云 OCR | 按次计费 | ~0.05 元/次 | 纯文字提取 |
| 百炼图片识别 | 按 Token 计费 | ~0.02 元/次 | 内容理解 + 文字 |

---

## ✅ 配置状态

| 项目 | 状态 |
|------|------|
| 阿里云 Green SDK | ✅ 已安装 |
| 百炼 OpenAI SDK | ✅ 已安装 |
| API Key 配置 | ✅ 已配置 |
| 代码实现 | ✅ 已完成 |
| 开发模式 | ✅ 可用（模拟结果） |
| 生产模式 | ⏳ 待测试 |

---

**更新人**: COO  
**更新时间**: 2026-05-18 17:45  
**状态**: ✅ 配置完成

---

*心海法律 AI · OCR 与图片识别配置 | 版本：1.0 | 2026-05-18*
