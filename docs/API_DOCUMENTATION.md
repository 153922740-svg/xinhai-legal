# 心海法律 AI - 完整接口文档

**版本**: v1.1.0  
**更新时间**: 2026-05-18  
**文档路径**: `/home/admin/xinhai_legal_api/docs/API_DOCUMENTATION.md`  
**API 地址**: `https://xinclaw.xhacca.cn/api/v1`

---

## 📋 接口总览

| Phase | 模块 | 接口数量 | 状态 |
|-------|------|---------|------|
| Phase 2 | 会员/支付/Token | 24 | ✅ |
| Phase 3 | AI 对话/文书/审阅 | 18 | ✅ |
| Phase 4 | 用户认证 | 8 | ✅ |
| Phase 5 | 输入增强 | 6 | ✅ |
| Phase 6 | 自进化 | 6 | ✅ |
| Phase 7 | 合伙人系统 | 12 | ✅ |
| Phase 8 | 认证增强 | 4 | ✅ |
| Phase 9 | 积分系统 | 10 | ✅ |
| Phase 10 | 三模型验证 | 4 | ✅ |
| Phase 11 | 文书增强 | 6 | ✅ |
| Phase 13 | 历史对话 | 8 | ✅ |
| **合计** | **11 模块** | **106** | **✅** |

---

## 🔐 通用说明

### 认证方式
所有需要认证的接口需要在 Header 中携带 JWT Token：
```
Authorization: Bearer <token>
```

### 响应格式
```json
{
  "success": true/false,
  "code": "success/error_code",
  "message": "描述信息",
  "data": {}
}
```

### 错误码
| 错误码 | 说明 |
|--------|------|
| success | 成功 |
| auth_required | 需要登录 |
| auth_expired | Token 过期 |
| permission_denied | 权限不足 |
| invalid_params | 参数错误 |
| server_error | 服务器错误 |

---

## Phase 2: 会员与计费系统

### 2.1 会员服务

#### GET /api/v2/member/packages
**获取会员套餐列表**

**请求**: 无需参数

**响应**:
```json
{
  "success": true,
  "data": {
    "packages": [
      {
        "id": "monthly",
        "name": "月卡",
        "price": 30.00,
        "duration_days": 30,
        "tokens_included": 50000
      },
      {
        "id": "quarterly",
        "name": "季卡",
        "price": 80.00,
        "duration_days": 90,
        "tokens_included": 150000
      },
      {
        "id": "yearly",
        "name": "年卡",
        "price": 288.00,
        "duration_days": 365,
        "tokens_included": 600000
      }
    ]
  }
}
```

---

#### GET /api/v2/member/info
**获取会员信息**

**请求**: Header 携带 Token

**响应**:
```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "membership_type": "monthly",
    "membership_expiry": "2026-06-18T14:30:00Z",
    "is_active": true,
    "auto_renew": false
  }
}
```

---

#### POST /api/v2/order/create
**创建会员订单**

**请求**:
```json
{
  "package_id": "monthly",
  "auto_renew": false
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "order_id": "ORD20260518001",
    "amount": 30.00,
    "status": "pending_payment",
    "expire_time": "2026-05-18T15:00:00Z"
  }
}
```

---

### 2.2 Token 计费

#### GET /api/v2/token/balance
**查询 Token 余额**

**响应**:
```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "balance": 10000,
    "currency": "CNY",
    "value": 2.00
  }
}
```

---

#### POST /api/v2/token/recharge
**充值 Token**

**请求**:
```json
{
  "amount": 10000,
  "payment_method": "wechat"
}
```

---

#### GET /api/v2/token/transactions
**查询 Token 流水**

**请求**:
```
GET /api/v2/token/transactions?page=1&limit=20
```

---

### 2.3 微信支付

#### POST /api/v2/pay/wechat
**微信支付预下单**

**请求**:
```json
{
  "order_id": "ORD20260518001",
  "openid": "oXXXX-openid",
  "amount": 30.00
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "timeStamp": "1684425600",
    "nonceStr": "5K8264ILTKCH16CQ2502SI8ZNMTM67VS",
    "package": "prepay_id=wx20230518143000abcdef1234567890",
    "signType": "RSA",
    "paySign": "oR9d8PuhnIc+YZ8cBHFCwfgpaK9gd7vaRvkYD7rthRAZ1xNnN..."
  }
}
```

---

#### POST /api/v2/pay/callback/wechat
**微信支付回调**

**说明**: 微信支付成功后异步通知此接口

---

## Phase 3: AI 核心功能

### 3.1 AI 对话

#### POST /api/v3/chat/send
**发送对话消息**

**请求**:
```json
{
  "message": "我想咨询一下离婚流程",
  "conversation_id": "conv_123"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "message_id": "msg_456",
    "response": "离婚流程如下：1. 协议离婚...",
    "tokens_used": 500,
    "model": "deepseek-v4-pro"
  }
}
```

---

#### WebSocket /api/v3/chat/stream
**流式对话（实时响应）**

**说明**: 使用 WebSocket 连接，实时接收 AI 回复

---

### 3.2 文书生成

#### GET /api/v3/document/templates
**获取文书模板列表**

**响应**:
```json
{
  "success": true,
  "data": {
    "templates": [
      {
        "id": "civil_complaint",
        "name": "民事起诉状",
        "category": "诉讼文书",
        "fields": ["原告信息", "被告信息", "诉讼请求", "事实与理由"]
      },
      {
        "id": "lawyer_letter",
        "name": "律师函",
        "category": "非诉文书",
        "fields": ["委托人信息", "收件人信息", "事由", "要求"]
      }
      // ... 共 9 种模板
    ]
  }
}
```

---

#### POST /api/v3/document/generate
**生成文书**

**请求**:
```json
{
  "template_id": "civil_complaint",
  "fields": {
    "plaintiff_name": "张三",
    "defendant_name": "李四",
    "claim": "请求判决离婚",
    "facts": "双方感情破裂..."
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "document_id": "doc_789",
    "content": "民事起诉状\n\n原告：张三...\n\n此致\nXX 人民法院",
    "created_at": "2026-05-18T14:30:00Z"
  }
}
```

---

### 3.3 合同审阅

#### POST /api/v3/contract/review
**合同审阅**

**请求**:
```json
{
  "contract_text": "甲方：张三\n乙方：李四\n...",
  "review_type": "risk"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "risks": [
      {
        "level": "high",
        "content": "违约责任条款不明确",
        "suggestion": "建议明确违约金数额"
      }
    ],
    "score": 75
  }
}
```

---

## Phase 4: 用户认证

### 4.1 登录注册

#### POST /api/v4/auth/register
**用户注册**

**请求**:
```json
{
  "phone": "13800138000",
  "sms_code": "888888",
  "password": "Chen0812*"
}
```

---

#### POST /api/v4/auth/login
**用户登录**

**请求**:
```json
{
  "phone": "13800138000",
  "password": "Chen0812*"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 123,
      "phone": "138****8000",
      "username": "用户 123"
    }
  }
}
```

---

#### POST /api/v4/auth/sms
**发送短信验证码**

**请求**:
```json
{
  "phone": "13800138000"
}
```

---

## Phase 5: 输入增强

### 5.1 语音输入

#### POST /api/v5/voice/upload
**上传语音文件**

**请求**: multipart/form-data
- file: 语音文件 (max 60s)

**响应**:
```json
{
  "success": true,
  "data": {
    "file_url": "/uploads/voice/20260518_143000.mp3",
    "duration": 15.5,
    "text": "我想咨询一下离婚流程"
  }
}
```

---

### 5.2 文件上传

#### POST /api/v5/file/upload
**上传文件**

**请求**: multipart/form-data
- file: 文件 (max 10MB)

---

#### POST /api/v5/image/upload
**上传图片**

**请求**: multipart/form-data
- file: 图片 (max 5MB)

**响应**:
```json
{
  "success": true,
  "data": {
    "file_url": "/uploads/images/20260518_143000.jpg",
    "ocr_text": "图片中的文字内容..."
  }
}
```

---

## Phase 6: 自进化

### 6.1 用户反馈

#### POST /api/v6/feedback/submit
**提交反馈**

**请求**:
```json
{
  "message_id": "msg_456",
  "rating": 5,
  "comment": "回答很专业"
}
```

---

#### POST /api/v6/badcase/submit
**提交坏案例**

**请求**:
```json
{
  "message_id": "msg_456",
  "reason": "回答不准确",
  "expected": "期望的回答内容..."
}
```

---

## Phase 7: 合伙人系统

### 7.1 合伙人信息

#### GET /api/v7/partner/info
**获取合伙人信息**

**响应**:
```json
{
  "success": true,
  "data": {
    "level": "silver",
    "level_name": "银牌合伙人",
    "commission_rate": 0.12,
    "total_commission": 1500.00,
    "referral_count": 25
  }
}
```

---

#### GET /api/v7/partner/referrals
**获取推荐列表**

---

#### GET /api/v7/partner/commissions
**获取佣金明细**

---

#### POST /api/v7/partner/withdraw
**申请提现**

**请求**:
```json
{
  "amount": 100.00,
  "withdraw_method": "wechat",
  "account": "微信号"
}
```

---

## Phase 8: 认证增强

### 8.1 手机验证码登录

#### POST /api/v8/auth/sms-login
**短信验证码登录**

**请求**:
```json
{
  "phone": "13800138000",
  "sms_code": "888888"
}
```

---

## Phase 9: 积分系统

### 9.1 签到

#### POST /api/v9/integral/signin
**每日签到**

**响应**:
```json
{
  "success": true,
  "data": {
    "points": 10,
    "continuous_days": 5,
    "bonus": 0
  }
}
```

---

### 9.2 积分任务

#### GET /api/v9/integral/tasks
**获取任务列表**

---

#### POST /api/v9/integral/task/complete
**完成任务**

---

### 9.3 积分商城

#### GET /api/v9/integral/shop
**获取商城商品**

---

#### POST /api/v9/integral/exchange
**积分兑换**

---

## Phase 10: 三模型验证

### 10.1 交叉验证

#### POST /api/v10/validate
**三模型交叉验证**

**请求**:
```json
{
  "question": "离婚需要哪些材料？",
  "threshold": 0.8
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "answers": [
      {"model": "deepseek", "answer": "..."},
      {"model": "qwen", "answer": "..."},
      {"model": "glm", "answer": "..."}
    ],
    "consensus": true,
    "confidence": 0.95,
    "final_answer": "综合三个模型的回答..."
  }
}
```

---

## Phase 11: 文书增强

### 11.1 PDF 生成

#### POST /api/v11/document/pdf
**生成 PDF 文书**

**请求**:
```json
{
  "document_id": "doc_789",
  "format": "A4"
}
```

---

## Phase 13: 历史对话

### 13.1 会话管理

#### GET /api/v13/conversations
**获取会话列表**

---

#### GET /api/v13/conversations/{id}
**获取会话详情**

---

#### DELETE /api/v13/conversations/{id}
**删除会话**

---

#### PUT /api/v13/conversations/{id}/title
**修改会话标题**

---

## 📊 接口统计

### 按功能分类
| 功能 | 接口数 | 占比 |
|------|--------|------|
| 用户认证 | 12 | 11% |
| AI 对话 | 8 | 8% |
| 文书生成 | 10 | 9% |
| 会员服务 | 10 | 9% |
| 支付 | 6 | 6% |
| Token 计费 | 8 | 8% |
| 合伙人 | 12 | 11% |
| 积分 | 10 | 9% |
| 输入增强 | 6 | 6% |
| 自进化 | 6 | 6% |
| 其他 | 18 | 17% |

---

## 🧪 测试说明

### 测试环境
- 地址：https://xinclaw.xhacca.cn/api/v1
- 测试账号：13800138000 / 888888

### 测试工具
- Postman
- curl
- 微信小程序开发者工具

---

## 📝 更新记录

| 日期 | 版本 | 更新内容 | 更新人 |
|------|------|---------|--------|
| 2026-05-18 | v1.1.0 | 初始完整版本 | COO |

---

*心海法律 AI · 接口文档 | 版本：1.1.0 | 2026-05-18*
