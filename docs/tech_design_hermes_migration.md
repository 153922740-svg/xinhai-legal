# 心海法律 AI — Hermes 迁移技术方案设计

> **文档编号**: XINCLAW-TECH-HERMES-V1.0  
> **状态**: ⏳ 草稿  
> **创建日期**: 2026-05-19  
> **负责人**: 铸基（架构师）  

---

## 1. 总体架构

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                   微信小程序 / H5                              │
│     API_BASE = 'https://xinclaw.xhacca.cn'                   │
│     请求: POST /auth/send_sms（无版本前缀）                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                    Nginx (80/443)
                    xinclaw.xhacca.cn
                         │
          ┌──────────────┼──────────────────┐
          │              │                  │
     Hermes Business  Hermes Gateway    COO API (8646)
     API (8647)       (8642)           管理后台
     ┌────────────┐   AI Agent对话       Agent调度
     │ 全部PRD API│   /v1/chat/         └──────────┘
     │ 34个接口   │   completions
     └─────┬──────┘
           │
      ┌────┴──────────────────────────────────┐
      │       SQLite Database                  │
      │  /home/admin/xinhai_legal_api/data/   │
      │  xinhai_legal.db                      │
      │  25+ 张表                              │
      └───────────────────────────────────────┘
```

### 1.2 服务分层

| 层 | 组件 | 协议 | 说明 |
|:---|:-----|:-----|:-----|
| L1 接入层 | Nginx 80/443 | HTTPS | SSL终止、反向代理、静态文件 |
| L2 业务层 | Hermes Business API 8647 | HTTP | Python BaseHTTPRequestHandler |
| L3 AI层 | Hermes Gateway 8642 | HTTP | OpenAI兼容/v1/chat/completions |
| L4 管理 | COO API 8646 | HTTP | 后台管理 |
| L5 数据 | SQLite | 文件级 | 单一数据库文件 |

### 1.3 Nginx路由设计

```
# PRD标准路径 → Hermes Business API (8647)
/auth/*       → 127.0.0.1:8647
/chat/*       → 127.0.0.1:8647
/member/*     → 127.0.0.1:8647
/payment/*    → 127.0.0.1:8647
/token/*      → 127.0.0.1:8647
/document/*   → 127.0.0.1:8647
/integral/*   → 127.0.0.1:8647
/user/*       → 127.0.0.1:8647
/partner/*    → 127.0.0.1:8647
/health       → 127.0.0.1:8647

# AI对话 → Hermes Gateway (8642)
/v1/*         → 127.0.0.1:8642

# 管理后台 → COO API (8646)
/api/v6/*     → 127.0.0.1:8646
/coo/*        → 静态文件
```

---

## 2. 服务设计

### 2.1 Hermes Business API

**架构模式**：独立HTTP Server + Subprocess Bridge

**为什么用Bridge模式？**
- 避免业务逻辑常驻内存导致的内存泄漏
- 子进程隔离，崩溃不影响主进程
- 方便独立测试业务逻辑

**实现方式**：
```
客户端请求 → hermes_business_api.py（路由分发）
                         ↓ (subprocess)
        hermes_business_bridge.py <action> '<json_body>'
                         ↓ (stdout)
                    JSON响应返回客户端
```

**路由表**（hermes_business_api.py中do_POST/do_GET实现）：
```python
# 路由映射
routes = {
    '/auth/send_sms':       ('POST', 'send_sms'),
    '/auth/login':          ('POST', 'login'),
    '/auth/wx_login':       ('POST', 'wx_login'),
    '/chat/send':           ('POST', 'chat_send'),
    '/chat/sessions':       ('GET',  'chat_sessions'),
    '/member/status':       ('GET',  'member_status'),
    '/payment/wechat':      ('POST', 'payment_wechat'),
    '/token/balance':       ('GET',  'token_balance'),
    '/token/recharge':      ('POST', 'token_recharge'),
    '/health':              ('GET',  'health'),
    # ... 更多路由
}
```

### 2.2 数据库连接方案

```python
def get_db():
    """获取数据库连接（每次请求新建，用完关闭）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # WAL模式支持读写并发
    conn.execute("PRAGMA busy_timeout=5000") # 忙等待5秒
    return conn
```

### 2.3 日志方案

```python
# 统一日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/admin/hermes_business_api.log'),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)
```

---

## 3. 模块详细设计

### 3.1 认证模块（已实现）

**文件**：`/home/admin/hermes_business_bridge.py`（第187-308行）

**JWT Token格式**：
```
header = base64({"alg":"HS256","typ":"JWT"})
payload = base64({"user_id":1,"phone":"138***", "exp":timestamp})
signature = HMAC-SHA256(header.payload, secret)
token = header.payload.signature
```

**验证码生命周期**：
```
生成验证码（6位数字）
    ↓ 存储到内存字典 sms_codes{phone: {code, expire, send_time}}
    ↓ 有效期300秒
    ↓ 防刷限制60秒
验证码验证（一次性，验证后删除）
    ↓ 开发模式万能码888888
    ↓ 超时返回"验证码已过期"
    ↓ 错误返回"验证码错误"
```

**新用户赠送**：
```
注册 → tokens_balance += 2000
     → membership = 'trial'
     → membership_end = now + 3天
```

### 3.2 聊天模块

**交互流程**：
```
用户消息 → POST /chat/send
    ↓ 解析Authorization获取user_id
    ↓ 查询会话（新/续）
    ↓ 扣Token
    ↓ 调用Hermes Gateway 8642 /v1/chat/completions
    ↓ 保存消息到chat_messages
    ↓ 返回AI回复
```

**Hermes Gateway调用**：
```python
def call_hermes_ai(messages, session_id):
    """调用Hermes Gateway的AI能力"""
    response = requests.post(
        'http://localhost:8642/v1/chat/completions',
        headers={
            'Authorization': 'Bearer xinclaw-law-2026-secret',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'deepseek-chat',
            'messages': messages,
            'session_id': session_id
        },
        timeout=30
    )
    return response.json()['choices'][0]['message']['content']
```

### 3.3 会员+Token模块

**微信支付流程**：
```
用户选择套餐 → POST /payment/wechat {plan_type, user_id}
    ↓ 统一下单
    ↓ 返回 prepay_id + sign
    ↓ 小程序调起支付
    ↓ 支付成功 → 微信回调 notify_url
    ↓ 更新memberships + token_balances
```

**会员方案**：
| 类型 | 价格 | 有效期 |
|:-----|:----:|:------|
| trial | 免费 | 3天 |
| first_month | ¥1 | 首月 |
| monthly | ¥30 | 30天 |
| quarterly | ¥80 | 90天 |
| yearly | ¥288 | 365天 |

**Token方案**：
| 充值金额 | Token数量 |
|:--------:|:---------:|
| ¥10 | 50,000 |
| ¥30 | 160,000 |
| ¥50 | 270,000 |
| ¥100 | 600,000 |
| ¥500 | 3,200,000 |

### 3.4 积分+签到模块

**签到奖励规则**：
| 连续天数 | 奖励积分 |
|:--------:|:--------:|
| 3天 | 20 |
| 7天 | 230 |
| 14天 | 120 |
| 30天 | 300 |

**每日任务积分**：
- 签到：+10（连续7天共240分）
- 咨询：+5/次（上限5分/日）
- 生成文书：+5/次（上限5分/日）

### 3.5 文书模块

**9种文书类型**：
1. civil_complaint — 民事起诉状
2. defense — 答辩状
3. lawyer_letter — 律师函
4. rental_contract — 租房合同
5. loan_agreement — 借款协议
6. divorce_agreement — 离婚协议
7. labor_arbitration — 劳动仲裁申请书
8. debt_transfer — 债权转让协议
9. settlement — 和解协议

**生成流程**：
```
用户请求 → 收集字段 → AI生成 → 保存documents表
    ↓ Word/PDF下载
```

### 3.6 合伙人模块

**等级体系**：
| 等级 | 佣金比例 | 升级条件 |
|:-----|:--------:|:---------|
| 初级 | 5% | 注册即可 |
| 铜牌 | 8% | 直推5人 |
| 银牌 | 12% | 直推20人 |
| 金牌 | 15% | 直推50人 |
| 钻石 | 20% | 直推100人 |

---

## 4. 安全设计

### 4.1 JWT认证中间件

```python
def verify_token(request):
    """从Authorization头解析并验证JWT"""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    
    token = auth[7:]
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        # 验证签名
        payload_b64 = parts[1]
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + '=='))
        
        # 验证过期
        if payload.get('exp', 0) < time.time():
            return None
        
        return payload
    except:
        return None
```

### 4.2 短信防刷

```python
# 频率限制
if phone in sms_codes:
    last_send = sms_codes[phone].get('send_time', 0)
    if time.time() - last_send < 60:  # 1分钟
        return {'success': False, 'error': '请60秒后再试'}
```

### 4.3 SQL注入防护

所有数据库查询使用参数化：
```python
# ✅ 安全
conn.execute("SELECT * FROM users WHERE phone=?", (phone,))

# ❌ 危险
conn.execute(f"SELECT * FROM users WHERE phone='{phone}'")
```

### 4.4 CORS配置

```python
def do_OPTIONS(self):
    """CORS预检"""
    self.send_response(200)
    self.send_header('Access-Control-Allow-Origin', '*')
    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    self.end_headers()
```

---

## 5. 部署方案

### 5.1 启动命令

```bash
# 启动 Hermes Business API
nohup python3 /home/admin/hermes_business_api.py > /home/admin/hermes_business_api.log 2>&1 &
echo $! > /home/admin/hermes_business_api.pid

# 停止
kill $(cat /home/admin/hermes_business_api.pid)
```

### 5.2 健康检查

```bash
# 简单健康检查
curl -s http://localhost:8647/health

# 预期响应
{"status":"ok","service":"hermes-business-api","version":"1.0.0"}
```

### 5.3 Nginx配置切换

```nginx
# 迁移完成后，Nginx配置
# 旧：location /auth/ { proxy_pass http://127.0.0.1:5000; }
# 新：
location /auth/    { proxy_pass http://127.0.0.1:8647; }
location /chat/    { proxy_pass http://127.0.0.1:8647; }
location /member/  { proxy_pass http://127.0.0.1:8647; }
location /payment/ { proxy_pass http://127.0.0.1:8647; }
location /token/   { proxy_pass http://127.0.0.1:8647; }
location /document/{ proxy_pass http://127.0.0.1:8647; }
location /integral/{ proxy_pass http://127.0.0.1:8647; }
location /user/    { proxy_pass http://127.0.0.1:8647; }
location /partner/ { proxy_pass http://127.0.0.1:8647; }
location /health   { proxy_pass http://127.0.0.1:8647; }
```

---

## 6. 错误码设计

| 错误码 | HTTP状态 | 说明 |
|:------|:--------:|:-----|
| AUTH_MISSING_PARAM | 200 | 缺少参数（success=false）|
| AUTH_SMS_COOLDOWN | 200 | 短信发送太频繁 |
| AUTH_CODE_EXPIRED | 200 | 验证码已过期 |
| AUTH_CODE_WRONG | 200 | 验证码错误 |
| AUTH_TOKEN_EXPIRED | 200 | Token已过期 |
| AUTH_TOKEN_INVALID | 200 | Token无效 |
| DB_ERROR | 500 | 数据库错误 |
| AI_ERROR | 500 | AI服务不可用 |
| PAYMENT_ERROR | 500 | 支付接口异常 |

---

## 7. 文件清单

| 文件 | 说明 | 状态 |
|:-----|:-----|:----:|
| /home/admin/hermes_business_api.py | 路由分发（207行） | ✅ 已创建 |
| /home/admin/hermes_business_bridge.py | 业务逻辑（345行） | ✅ 已创建（认证模块）|
| /home/admin/hermes_business_api.log | 日志文件 | ⏳ 待创建 |
| Nginx配置 | /etc/nginx/conf.d/xinclaw.conf | ⏳ 待修改 |
| 小程序app.js | API_BASE修改 | ⏳ 待修改 |

---

> *文档结束*
> *下次更新：根据总裁反馈修改*
