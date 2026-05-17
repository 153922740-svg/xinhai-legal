# 心海法律 AI - ChatRouter 对话路由系统

## 概述

ChatRouter 是心海法律 AI 平台的智能对话路由引擎（PRD v4.0），实现多种消息类型支持、对话上下文管理、心理画像触发和动态报价集成。

## 核心功能

### 1. 消息类型支持

支持 6 种消息类型：
- `text`: 普通文本消息
- `card_pricing`: 报价卡片
- `card_product`: 产品/服务卡片
- `card_document`: 文档卡片
- `card_order`: 订单卡片
- `button`: 操作按钮

### 2. 对话上下文管理

- Session-based 会话管理
- 自动保存对话历史到数据库
- 支持上下文持久化
- 消息数量追踪

### 3. 意图识别

自动识别用户意图：
- `pricing`: 价格咨询
- `product`: 产品/服务咨询
- `document`: 文档需求
- `order`: 订单相关
- `legal_consult`: 法律咨询
- `psych_check`: 心理评估
- `general`: 一般聊天

### 4. 法律领域检测

支持 15 个法律领域自动识别：
婚姻家庭、劳动争议、合同纠纷、侵权责任、刑事辩护、行政诉讼、房产纠纷、知识产权、公司法务、债权债务、交通事故、医疗纠纷、遗产继承、消费维权、互联网金融

### 5. 心理画像引擎

- 基于大五人格模型评估
- 每 5 分钟最多触发 1 次
- 至少 3 条消息后触发
- 评估维度：开放性、尽责性、外向性、宜人性、神经质、风险承受

### 6. 动态报价引擎

- 基于用户会员等级折扣
- 基于心理画像调整
- 新客户优惠
- 24 小时报价有效期

## API 端点

### POST /api/v1/chat/send

发送消息并获取智能回复

**请求参数：**
```json
{
    "message": "用户输入内容",
    "session_id": "会话 ID（可选，自动生成）",
    "user_id": "用户 ID（可选）"
}
```

**响应示例：**
```json
{
    "success": true,
    "session_id": "abc123",
    "intent": "legal_consult",
    "domain": "婚姻家庭",
    "messages": [
        {
            "type": "text",
            "content": "回答内容...",
            "metadata": {}
        }
    ],
    "psych_assessment": null,
    "pricing": null,
    "response_time_ms": 150
}
```

### GET /api/v1/chat/history

获取对话历史

**参数：**
- `session_id`: 会话 ID（必填）
- `limit`: 返回数量（默认 20）

### POST /api/v1/chat/clear

清除对话上下文

**参数：**
```json
{
    "session_id": "会话 ID"
}
```

### POST /api/v1/chat/intent

检测用户意图（独立接口）

**参数：**
```json
{
    "message": "用户输入"
}
```

### POST /api/v1/chat/pricing

获取动态报价

**参数：**
```json
{
    "product_type": "legal_consult"
}
```

### GET /api/v1/chat/psych

获取用户心理画像

## 使用示例

### Python 客户端

```python
import requests

# 发送消息
response = requests.post(
    'http://localhost:8081/api/v1/chat/send',
    json={
        'message': '我想咨询离婚财产分割的问题',
        'session_id': 'my_session_001'
    }
)

result = response.json()
print(result['messages'])
```

### 前端集成

```javascript
async function sendMessage(message, sessionId) {
    const response = await fetch('/api/v1/chat/send', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            message: message,
            session_id: sessionId
        })
    });
    
    const data = await response.json();
    
    // 根据消息类型渲染
    data.messages.forEach(msg => {
        renderMessage(msg.type, msg.content, msg.metadata);
    });
}

function renderMessage(type, content, metadata) {
    switch(type) {
        case 'text':
            renderTextMessage(content);
            break;
        case 'card_pricing':
            renderPricingCard(metadata.pricing);
            break;
        case 'card_product':
            renderProductCards(metadata.products);
            break;
        case 'button':
            renderButton(content, metadata.action);
            break;
        // ... 其他类型
    }
}
```

## 数据库表

### chat_contexts
存储对话上下文
- session_id: 会话 ID（主键）
- user_id: 用户 ID
- messages: 消息历史（JSON）
- current_intent: 当前意图
- legal_domain: 法律领域
- message_count: 消息数量

### chat_logs
聊天记录（与用户关联）
- user_id: 用户 ID
- session_id: 会话 ID
- message_type: 消息类型
- content: 内容
- metadata: 元数据（JSON）

### psych_profiles
心理画像
- user_id: 用户 ID
- openness/conscientiousness/extraversion/agreeableness/neuroticism: 大五人格评分
- risk_tolerance: 风险承受
- assessment_confidence: 评估置信度

## 测试

运行单元测试：
```bash
cd /root/xinhai-legal
python -m unittest tests.test_chat_router -v
```

运行快速测试：
```bash
python test_quick.py
```

## 文件结构

```
/root/xinhai-legal/
├── app/
│   └── main.py              # 主应用（已集成 ChatRouter API）
├── services/
│   └── chat_router.py       # ChatRouter 核心服务
├── tests/
│   └── test_chat_router.py  # 单元测试
├── test_quick.py            # 快速测试脚本
└── docs/
    └── CHATROUTER_README.md # 本文档
```

## 配置

ChatRouter 使用以下配置：
- AI API URL: `http://127.0.0.1:8642/v1/chat/completions`
- API Key: `xinclaw-law-2026-secret`
- 心理评估间隔：300 秒（5 分钟）

## 版本

- 版本：1.0.0
- 符合 PRD v4.0 规范
- 创建日期：2026-05-15
