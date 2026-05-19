# 阿里云 OCR 正确配置指南

**更新时间**: 2026-05-18 18:30  
**更新人**: COO  
**问题**: Green SDK 不是 OCR 服务，应使用文字识别专用服务

---

## ❌ 错误配置

之前安装的 `aliyun-python-sdk-green` 是**内容安全**服务，不是 OCR！

```python
# 错误 ❌
from aliyunsdkgreen.request.v20180509 import ImageSyncDetectRequest
# 这是内容安全（鉴黄/暴恐/广告检测），不是 OCR
```

---

## ✅ 正确配置

### 方案 1: 使用 HTTP API（推荐）

阿里云文字识别（OCR）服务使用 HTTP API 调用，不需要专用 SDK。

#### 服务地址
- **通用文字识别**: `https://ocr.cn-shanghai.aliyuncs.com/`
- **身份证识别**: `https://ocr.cn-shanghai.aliyuncs.com/`
- **银行卡识别**: `https://ocr.cn-shanghai.aliyuncs.com/`

#### API 调用示例

```python
import requests
import base64
import hmac
import hashlib
from datetime import datetime

def ocr_aliyun_http(image_path, ocr_type='general'):
    """
    阿里云 OCR HTTP API 调用
    ocr_type: general(通用文字), idcard(身份证), bankcard(银行卡)
    """
    access_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID')
    access_key_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
    
    # 读取图片并转 base64
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # API 端点
    url = 'https://ocr.cn-shanghai.aliyuncs.com/2021-07-07/ocr'
    
    # 请求体
    body = {
        "Image": image_data,
        "Configure": '{"format":"json"}"
    }
    
    # 签名（简化版，生产环境需要完整签名）
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'ACS {access_key_id}:{signature}',
        'x-acs-signature-method': 'HMAC-SHA1',
        'x-acs-signature-version': '1.0',
        'x-acs-date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
    }
    
    # 发送请求
    response = requests.post(url, json=body, headers=headers)
    result = response.json()
    
    # 提取文字
    if 'Data' in result and 'Pages' in result['Data']:
        ocr_text = result['Data']['Pages'][0].get('Text', '')
        return ocr_text
    
    return None
```

---

### 方案 2: 使用百炼大模型 OCR（推荐）

**百炼 qwen-vl-max 也支持 OCR 文字提取，而且更简单！**

```python
from openai import OpenAI

def ocr_bailian(image_path):
    """
    使用百炼大模型进行 OCR 文字提取
    优势：不需要额外配置，直接用 DASHSCOPE_API_KEY
    """
    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    # 读取图片
    import base64
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # 调用 qwen-vl 模型，专门用于 OCR
    response = client.chat.completions.create(
        model="qwen-vl-max",
        messages=[{
            "role": "user",
            "content": [
                {"image": f"data:image/jpeg;base64,{image_data}"},
                {"text": "请提取这张图片中的所有文字内容，保持原有格式和换行。"}
            ]
        }]
    )
    
    ocr_text = response.choices[0].message.content
    return ocr_text
```

---

## 📊 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **百炼 OCR** | 配置简单、支持复杂场景、按 Token 计费 | 速度稍慢 | ⭐⭐⭐⭐⭐ |
| **阿里云 OCR HTTP** | 专业 OCR、速度快 | 需要签名、配置复杂 | ⭐⭐⭐⭐ |
| **Green SDK** | ❌ 不是 OCR | 无法使用 | ❌ |

---

## ✅ 推荐方案

**统一使用百炼大模型进行 OCR 和图片识别！**

### 优势
1. **配置简单**: 只需要 DASHSCOPE_API_KEY（已配置）
2. **功能强大**: 支持 OCR + 图片理解
3. **成本低**: 按 Token 计费，约 0.02 元/次
4. **代码统一**: 一个函数搞定 OCR 和图片识别

### 代码实现

```python
# phase5_input_enhance_v2.py

def ocr_and_recognize_image(image_path, mode='ocr'):
    """
    百炼大模型图片处理
    mode: 'ocr'(文字提取) 或 'describe'(图片描述)
    """
    from openai import OpenAI
    import base64
    
    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    # 读取图片
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # 根据模式选择提示词
    if mode == 'ocr':
        prompt = "请提取这张图片中的所有文字内容，保持原有格式和换行。只返回文字内容，不要其他描述。"
    else:  # describe
        prompt = "请描述这张图片的内容，包括图片中的文字、物体、场景等。"
    
    # 调用模型
    response = client.chat.completions.create(
        model="qwen-vl-max",
        messages=[{
            "role": "user",
            "content": [
                {"image": f"data:image/jpeg;base64,{image_data}"},
                {"text": prompt}
            ]
        }]
    )
    
    return response.choices[0].message.content
```

---

## 📋 配置清单

### 已配置 ✅
- [x] DASHSCOPE_API_KEY（.env 中）
- [x] openai SDK（已安装）
- [x] 代码实现（phase5_input_enhance_v2.py）

### 不需要配置 ❌
- [x] 阿里云 Green SDK（已卸载）
- [x] 阿里云 OCR HTTP API（不需要，用百炼）

---

## 💰 费用

| 操作 | Token 消耗 | 费用 |
|------|-----------|------|
| OCR 文字提取 | ~500 Token | ~0.01 元/次 |
| 图片描述 | ~800 Token | ~0.02 元/次 |

---

**更新人**: COO  
**更新时间**: 2026-05-18 18:30  
**状态**: ✅ 配置正确，使用百炼大模型

---

*心海法律 AI · 阿里云 OCR 正确配置 | 版本：1.1 | 2026-05-18*
