# 心海法律 AI 技术架构与实施规划

> **文档编号**: XINCLAW-TECH-ARCH-V1.0  
> **状态**: ✅ 已定稿  
> **创建日期**: 2026-05-19  
> **最后更新**: 2026-05-19  
> **文档维护**: 蓝图（产品官）+ 铸基（架构师）  
> **审批**: 总裁已审批  

---

## 修订记录

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| V1.0 | 2026-05-19 | 蓝图 + 铸基 | 初始版本，完成整体架构设计与实施规划 |

---

## 目录

1. [概述](#1-概述)
2. [系统架构](#2-系统架构)
3. [服务定义](#3-服务定义)
4. [API路由设计](#4-api路由设计)
5. [数据结构](#5-数据结构)
6. [实施规划](#6-实施规划)
7. [风险与应对](#7-风险与应对)
8. [附录](#8-附录)

---

## 1. 概述

### 1.1 项目背景

心海法律AI原系统基于Flask框架开发，业务逻辑分散在多个Phase文件中，API路径含有多套版本前缀（`/api/v1/`、`/api/v2/`等），与PRD规定的无版本前缀标准路径不一致。

根据总裁2026-05-19指令，系统需全面迁移至Hermes Agent架构，所有业务API统一遵循PRD规定的无版本前缀标准路径。

### 1.2 架构目标

1. **统一API路径**：所有接口遵循PRD第十章规定的无版本前缀路径
2. **业务解耦**：将业务逻辑从Flask迁移至独立业务服务
3. **平滑过渡**：新老服务并行运行，逐步切换流量
4. **数据库统一**：单一SQLite数据源，不拆分数据

### 1.3 设计约束

- 服务器IP：8.218.93.213（阿里云）
- 域名：xinclaw.xhacca.cn
- 数据库：SQLite（`/home/admin/xinhai_legal_api/data/xinhai_legal.db`）
- 小程序AppID：wx73612d8efb98658d
- **禁止创建新的PRD版本文件**，所有修改直接在 `PRD_终版.md` 上更新

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        微信小程序 / H5                            │
│              app.js API_BASE = 'https://xinclaw.xhacca.cn'      │
│              请求路径: POST /auth/send_sms（无版本前缀）          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                        ┌────┴────┐
                        │  Nginx  │  端口 80/443
                        │  SSL    │  xinclaw.xhacca.cn
                        └────┬────┘
                             │
            ┌────────────────┼──────────────────┐
            │                │                  │
       ┌────┴────┐     ┌────┴────┐        ┌────┴────┐
       │ 业务API  │     │ AI对话  │        │ COO管理 │
       │ 8647     │     │ 8642    │        │ 8646    │
       │ Hermes   │     │ Hermes  │        │ COO API │
       │ Business │     │ Gateway │        │ 后台管理│
       │ API      │     │ Agent   │        │ Agent   │
       └────┬────┘     │ 能力    │        │ 调度    │
            │          └─────────┘        └─────────┘
            │
       ┌────┴──────────────────────────────────────┐
       │          SQLite Database                   │
       │  /home/admin/xinhai_legal_api/data/       │
       │  xinhai_legal.db                          │
       │  25+ 张业务表                              │
       └───────────────────────────────────────────┘
```

### 2.2 架构分层说明

| 层级 | 组件 | 说明 |
|:-----|:-----|:-----|
| **接入层** | Nginx 80/443 | 反向代理、SSL终止、静态文件服务 |
| **服务层** | Hermes Business API (8647) | **核心业务API**，承载所有PRD定义的业务接口 |
| **AI层** | Hermes Gateway (8642) | AI Agent对话能力，OpenAI兼容API |
| **管理层** | COO API (8646) | COO管理后台、Agent调度、任务队列 |
| **数据层** | SQLite | 单一数据库文件，所有服务共享 |

### 2.3 Nginx路由拓扑

```
xinclaw.xhacca.cn
  ├── /auth/*      → 127.0.0.1:8647   # 认证模块
  ├── /chat/*      → 127.0.0.1:8647   # 聊天模块
  ├── /member/*    → 127.0.0.1:8647   # 会员模块
  ├── /payment/*   → 127.0.0.1:8647   # 支付模块
  ├── /token/*     → 127.0.0.1:8647   # Token模块
  ├── /document/*  → 127.0.0.1:8647   # 文书模块
  ├── /integral/*  → 127.0.0.1:8647   # 积分模块
  ├── /lawyer/*    → 127.0.0.1:8647   # 律师板块（入驻/案件/AI工具/钱包/委托）
  ├── /user/*      → 127.0.0.1:8647   # 用户模块
  ├── /health      → 127.0.0.1:8647   # 健康检查
  ├── /v1/*        → 127.0.0.1:8642   # Hermes Gateway (AI对话)
  ├── /api/v6/*    → 127.0.0.1:8646   # COO API (管理后台)
  ├── /coo/        → 静态文件          # COO前端页面
  └── /            → 静态文件          # H5前端页面
```

---

## 3. 服务定义

### 3.1 Hermes Business API（端口8647）

**文件位置**：`/home/admin/hermes_business_api.py`

**架构模式**：独立HTTP Server + Subprocess Bridge

**实现方式**：
- 继承 `BaseHTTPRequestHandler` 的独立Python HTTP服务
- 业务逻辑通过 `subprocess` 调用 `hermes_business_bridge.py` 执行
- 子进程模式避免内存泄漏和请求阻塞
- 支持CORS（开发期间允许所有来源）

**认证方式**：JWT（HMAC-SHA256签名，24小时有效期）

**日志文件**：`/home/admin/hermes_business_api.log`

**启动命令**：
```bash
nohup python3 /home/admin/hermes_business_api.py > /home/admin/hermes_business_api.log 2>&1 &
```

### 3.2 Hermes Business Bridge（无端口）

**文件位置**：`/home/admin/hermes_business_bridge.py`

**架构模式**：命令行调用的业务逻辑脚本

**调用方式**：
```bash
python3 /home/admin/hermes_business_bridge.py <action> '<json_body>'
```

**响应格式**：
```json
{
    "success": true/false,
    "error": "错误信息（仅失败时）",
    "...": "业务数据字段"
}
```

### 3.3 Hermes Gateway（端口8642）

**位置**：`/home/admin/.hermes/`

**能力**：OpenAI兼容的 `/v1/chat/completions` 接口

**用途**：仅提供AI Agent对话能力，不处理业务API

### 3.4 COO API（端口8646）

**文件位置**：`/home/admin/coo_api.py`

**能力**：COO管理后台、Agent调度、任务队列、数据看板

### 3.5 Flask 旧后端（端口5000）

**文件位置**：`/home/admin/xinhai_legal_api/app.py`

**状态**：⏳ 过渡期，参考代码

**废弃计划**：待Hermes Business API覆盖全部功能后停止

---

## 4. API路由设计

### 4.1 路由设计原则

1. **路径无版本前缀**：所有API路径 = PRD第十章规定的路径
2. **HTTP方法语义化**：GET=查询、POST=创建、PUT=更新、DELETE=删除
3. **JSON请求/响应**：统一Content-Type: application/json
4. **错误码规范**：200=业务正常（success字段区分成功/失败）、500=服务器错误
5. **认证方式**：Authorization: Bearer <token>

### 4.2 完整API路由表

#### 4.2.1 认证模块（P0 — 已完成）

| 方法 | 路径 | 请求参数 | 响应字段 | 说明 |
|:----:|:-----|:---------|:---------|:-----|
| POST | `/auth/send_sms` | `{phone: string}` | `{success, message, dev_code?}` | 发送短信验证码 |
| POST | `/auth/login` | `{phone, code}` | `{success, token, user, is_new}` | 手机号+验证码登录 |
| POST | `/auth/wx_login` | `{code}` | `{success, token, user, is_new}` | 微信登录 |

**认证流程**：
```
用户输入手机号 → POST /auth/send_sms → 发送验证码
用户输入验证码 → POST /auth/login   → 验证通过 → 返回JWT token
后续请求        → Header: Authorization: Bearer <token>
```

**验证码规则**：
- 6位数字
- 有效期5分钟
- 同一手机号1分钟1次（防刷）
- 开发模式万能验证码：888888

**新用户赠送**：
- 赠2,000 Token
- 自动开通3天免费会员（trial）

**用户表结构（users）**：
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 用户ID |
| phone | TEXT UNIQUE | 手机号 |
| wechat_openid | TEXT | 微信openid |
| username | TEXT | 用户名 |
| nickname | TEXT | 昵称 |
| tokens_balance | INTEGER DEFAULT 0 | Token余额 |
| membership | TEXT DEFAULT 'free' | 会员类型（free/trial/monthly/quarterly/yearly） |
| membership_start | TEXT | 会员开始时间 |
| membership_end | TEXT | 会员到期时间 |
| status | INTEGER DEFAULT 1 | 状态（1正常/0禁用）|
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |
| last_login | TEXT | 最后登录时间 |

#### 4.2.2 聊天模块（P0 — 待开发）

| 方法 | 路径 | 请求参数 | 响应字段 | 说明 |
|:----:|:-----|:---------|:---------|:-----|
| POST | `/chat/send` | `{message, session_id?}` | `{success, response, session_id, suggestions}` | 发送消息 |
| GET | `/chat/sessions` | — | `{success, sessions: [{id, title, updated_at}]}` | 历史会话列表 |
| GET | `/chat/history/:id` | — | `{success, messages: [{role, content, created_at}]}` | 会话详情 |
| PUT | `/chat/sessions/:id/rename` | `{title}` | `{success}` | 重命名会话 |
| DELETE | `/chat/sessions/:id` | — | `{success}` | 删除会话 |

#### 4.2.3 会员+支付模块（P0 — 待开发）

| 方法 | 路径 | 请求参数 | 响应字段 | 说明 |
|:----:|:-----|:---------|:---------|:-----|
| GET | `/member/status` | — | `{success, membership, start, end, auto_renew}` | 会员状态 |
| POST | `/payment/wechat` | `{plan_type, user_id}` | `{success, pay_params}` | 微信支付下单 |
| GET | `/payment/get_openid` | `{code}` | `{success, openid}` | 获取微信openid |

#### 4.2.4 Token模块（P0 — 待开发）

| 方法 | 路径 | 请求参数 | 响应字段 | 说明 |
|:----:|:-----|:---------|:---------|:-----|
| GET | `/token/balance` | — | `{success, balance}` | Token余额 |
| POST | `/token/recharge` | `{amount}` | `{success, pay_params}` | Token充值 |
| GET | `/token/transactions` | — | `{success, transactions}` | Token流水 |

#### 4.2.5 文书模块（P1 — 待开发）

| 方法 | 路径 | 请求参数 | 响应字段 | 说明 |
|:----:|:-----|:---------|:---------|:-----|
| POST | `/document/generate` | `{type, fields}` | `{success, document}` | 生成文书 |
| GET | `/document/list` | — | `{success, documents}` | 文书列表 |
| GET | `/document/:id/detail` | — | `{success, document}` | 文书详情 |
| PUT | `/document/:id` | `{content}` | `{success}` | 更新文书 |
| GET | `/document/:id/download` | — | 文件流 | 下载文书（Word/PDF） |

#### 4.2.6 积分模块（P1 — 待开发）

| 方法 | 路径 | 请求参数 | 响应字段 | 说明 |
|:----:|:-----|:---------|:---------|:-----|
| GET | `/integral/balance` | — | `{success, balance}` | 积分余额 |
| GET | `/integral/records` | — | `{success, records}` | 积分记录 |
| POST | `/user/sign` | — | `{success, points, streak}` | 每日签到 |
| GET | `/user/sign/status` | — | `{success, signed, streak}` | 签到状态 |

#### 4.2.7 用户模块（P2 — 待开发）

| 方法 | 路径 | 请求参数 | 响应字段 | 说明 |
|:----:|:-----|:---------|:---------|:-----|
| GET | `/user/profile` | — | `{success, user}` | 用户资料 |
| PUT | `/user/profile` | `{nickname, ...}` | `{success}` | 更新资料 |
| POST | `/user/verify` | `{name, id_no}` | `{success}` | 实名认证 |
| POST | `/user/memory` | `{type, content}` | `{success}` | 保存记忆 |
| GET | `/user/memory` | — | `{success, memories}` | 获取记忆 |
| DELETE | `/user/memory` | — | `{success}` | 清除记忆 |

#### 4.2.8 系统（P2 — 待开发）

| 方法 | 路径 | 请求参数 | 响应字段 | 说明 |
|:----:|:-----|:---------|:---------|:-----|
| GET | `/health` | — | `{status, service, version, checks}` | 健康检查 |

#### 4.2.9 合伙人模块（P1 — 待开发）

| 方法 | 路径 | 请求参数 | 响应字段 | 说明 |
|:----:|:-----|:---------|:---------|:-----|
| GET | `/partner/level` | — | `{success, level, rate}` | 合伙人等级 |
| GET | `/partner/dashboard` | — | `{success, stats}` | 合伙人仪表盘 |
| POST | `/partner/generate-link` | — | `{success, link}` | 生成推广链接 |

### 4.3 响应格式规范

**成功响应**：
```json
{
    "success": true,
    "token": "eyJ...",
    "user": {
        "id": 1,
        "phone": "138****8000",
        "nickname": "用户8000",
        "tokens_balance": 2000,
        "membership": "trial"
    },
    "is_new": true
}
```

**业务错误**：
```json
{
    "success": false,
    "error": "验证码错误"
}
```

**服务器错误**：
```json
{
    "success": false,
    "error": "服务器内部错误"
}
```

---

## 5. 数据结构

### 5.1 数据库概览

**数据库文件**：`/home/admin/xinhai_legal_api/data/xinhai_legal.db`

**数据库引擎**：SQLite 3

**连接方式**：所有服务共享同一数据库文件，通过文件级锁协调并发

### 5.2 表结构总览（25+张）

#### 用户与认证（4张）
| 表名 | 用途 | 关键字段 |
|:-----|:-----|:---------|
| users | 用户信息 | id, phone, wechat_openid, tokens_balance, membership |
| user_memory | 用户记忆 | id, user_id, memory_type, content |
| sms_codes | 短信验证码 | id, phone, code, expire_at, used |
| user_sessions | 用户会话 | id, user_id, token, expire_at |

#### 聊天（3张）
| 表名 | 用途 | 关键字段 |
|:-----|:-----|:---------|
| chat_sessions | 聊天会话 | id, user_id, title, created_at |
| chat_messages | 聊天消息 | id, session_id, role, content, created_at |
| response_cache | 响应缓存 | id, query_hash, response, created_at |

#### 会员与计费（4张）
| 表名 | 用途 | 关键字段 |
|:-----|:-----|:---------|
| memberships | 会员信息 | id, user_id, plan_type, start_date, end_date |
| member_orders | 会员订单 | id, user_id, amount, status, created_at |
| token_orders | Token充值订单 | id, user_id, amount, token_amount, status |
| token_transactions | Token流水 | id, user_id, type, amount, balance_after |

#### 文书文件（3张）
| 表名 | 用途 | 关键字段 |
|:-----|:-----|:---------|
| documents | 法律文书 | id, user_id, doc_type, title, content, status |
| document_shares | 文书分享 | id, document_id, share_code, expire_at |
| uploaded_files | 上传文件 | id, user_id, filename, file_path, file_type |

#### 合伙人（4张）
| 表名 | 用途 | 关键字段 |
|:-----|:-----|:---------|
| partners | 合伙人信息 | id, user_id, level, commission_rate |
| referrals | 推荐记录 | id, referrer_id, referred_id, reward |
| commissions | 佣金记录 | id, partner_id, amount, status |
| withdrawals | 提现记录 | id, partner_id, amount, status |

#### 积分（3张）
| 表名 | 用途 | 关键字段 |
|:-----|:-----|:---------|
| integral_records | 积分记录 | id, user_id, amount, type, created_at |
| sign_in_records | 签到记录 | id, user_id, sign_date, streak |
| exchange_orders | 兑换订单 | id, user_id, goods_id, points_cost, status |

#### 系统（4张）
| 表名 | 用途 | 关键字段 |
|:-----|:-----|:---------|
| feedbacks | 用户反馈 | id, user_id, type, content, status |
| badcases | 坏案例 | id, query, response, issue |
| model_iterations | 模型迭代 | id, model_name, version, accuracy, status |
| activity_records | 活动记录 | id, user_id, activity_type, reward |

---

## 6. 实施规划

### 6.1 总体路线

```
当前状态：Flask后端(5000) + Hermes Gateway(8642) + COO API(8646)
                                              │
                                              ▼
                          ┌─────────────────────────────────────┐
                          │  新增 Hermes Business API (8647)    │
                          │  P0-1: 认证模块（已完成）            │
                          └─────────────────────────────────────┘
                                              │
                                              ▼
                          ┌─────────────────────────────────────┐
                          │  P0-2: 聊天模块（当前阶段）          │
                          │  P0-3: 会员+Token模块               │
                          └─────────────────────────────────────┘
                                              │
                                              ▼
                          ┌─────────────────────────────────────┐
                          │  P1: 文书+积分+合伙人+支付模块       │
                          └─────────────────────────────────────┘
                                              │
                                              ▼
                          ┌─────────────────────────────────────┐
                          │  P2: 用户+记忆+系统模块              │
                          │  + Nginx路由切换完成                 │
                          └─────────────────────────────────────┘
                                              │
                                              ▼
                          最终状态：Flask废弃，全部业务由8647承载
```

### 6.2 批次划分

| 批次 | 模块 | API数量 | 工作量 | 状态 |
|:-----|:-----|:-------:|:------:|:----:|
| **P0-1** | 认证（send_sms, login, wx_login） | 3 | 已完成 | ✅ |
| **P0-2** | 聊天（send, sessions, history, rename） | 4 | 约2小时 | ⏳ |
| **P0-3** | 会员+Token（status, payment, balance, recharge） | 5 | 约3小时 | ⏳ |
| P1-1 | 文书（generate, list, detail, update, download） | 5 | 约3小时 | 📅 |
| P1-2 | 积分+合伙人（balance, sign, dashboard, records） | 8 | 约3小时 | 📅 |
| P2-1 | 用户+记忆（profile, verify, memory CRUD） | 6 | 约2小时 | 📅 |
| P2-2 | 系统+清理（health, 旧代码废弃, Nginx路由切换） | 3 | 约1小时 | 📅 |

### 6.3 各批次详细说明

#### 6.3.1 P0-1 认证模块（已完成）

**涉及文件**：
- `hermes_business_api.py`：路由注册（send_sms, login, wx_login）
- `hermes_business_bridge.py`：业务逻辑实现

**核心逻辑**：
- 短信验证码：生成6位验证码→存储到内存字典→通过阿里云API发送→开发模式直接返回
- 手机号登录：验证验证码→查询/创建用户→生成JWT→返回用户信息
- 微信登录：通过微信code获取openid→查询/创建用户→生成JWT→返回用户信息

**关键常量**：
- 验证码有效期：300秒
- 防刷间隔：60秒
- 新用户Token赠送：2,000
- 新用户会员试用：3天
- 开发模式验证码：888888
- JWT有效期：24小时

**待优化项**：
- [ ] 验证码存储从内存迁移到SQLite（解决多进程问题）
- [ ] 微信登录接入真实微信API（jscode2session）

#### 6.3.2 P0-2 聊天模块（当前阶段）

**实现方式**：
- POST `/chat/send`：接收消息 → 调用Hermes Gateway(8642)的 `/v1/chat/completions` → 返回AI回复
- GET `/chat/sessions`：查询chat_sessions表 → 返回会话列表
- GET `/chat/history/:id`：查询chat_messages表 → 返回消息列表
- PUT/POST `/chat/sessions/:id/rename`：更新chat_sessions表标题
- DELETE `/chat/sessions/:id`：标记删除

**依赖**：
- Hermes Gateway (8642) 必须可用
- chat_sessions 和 chat_messages 表

**从Flask复用的代码**：
- `services/chat_router.py`：会话管理、意图识别
- `phase3_ai_chat_api.py`：API处理逻辑参考

#### 6.3.3 P0-3 会员+Token模块

**实现方式**：
- GET `/member/status`：查询memberships表 → 返回会员状态+到期时间
- POST `/payment/wechat`：微信支付统一下单 → 返回支付参数
- GET `/token/balance`：查询users.tokens_balance → 返回余额
- POST `/token/recharge`：创建token_orders记录 → 调用微信支付

**依赖**：
- 微信支付商户号配置
- memberships、member_orders、token_orders、token_transactions表

### 6.4 文件清单

#### 新建文件
| 文件 | 说明 | 状态 |
|:-----|:-----|:----:|
| `/home/admin/hermes_business_api.py` | Hermes业务API服务（207行） | ✅ 已完成 |
| `/home/admin/hermes_business_bridge.py` | Hermes业务Bridge脚本（345行） | ✅ 已完成 |

#### 依赖的现有Flask代码（参考用，不修改）
| 文件 | 说明 | 代码量 |
|:-----|:-----|:------:|
| `services/auth.py` | 认证逻辑参考 | 12KB |
| `services/chat_router.py` | 聊天核心逻辑参考 | 34KB |
| `services/billing.py` | 计费逻辑参考 | 10KB |
| `services/agency.py` | 合伙人逻辑参考 | 27KB |
| `services/legal_files.py` | 文书处理参考 | 27KB |
| `services/legal_qa.py` | 法律问答参考 | 13KB |
| `services/promotion.py` | 推广逻辑参考 | 12KB |
| `phase3_ai_chat_api.py` | AI对话API参考 | — |
| `phase2_member_api.py` | 会员API参考 | — |
| `phase2_token_billing.py` | Token计费参考 | — |
| `phase2_payment_wechat.py` | 微信支付参考 | — |
| `phase9_integral_system_api.py` | 积分系统参考 | — |
| `phase7_partner_system_api.py` | 合伙人系统参考 | — |

### 6.5 环境与配置

#### 环境变量
| 变量名 | 说明 | 当前值 |
|:-------|:-----|:-------|
| DB_PATH | 数据库路径 | `/home/admin/xinhai_legal_api/data/xinhai_legal.db` |
| ALIYUN_ACCESS_KEY_ID | 阿里云AccessKey | 已配置 |
| ALIYUN_ACCESS_KEY_SECRET | 阿里云AccessSecret | 已配置 |
| ALIYUN_SMS_SIGN_NAME | 短信签名 | 心海法律咨询 |
| ALIYUN_SMS_TEMPLATE_CODE | 短信模板 | 已配置 |
| JWT_SECRET | JWT签名密钥 | `xinclaw-law-2026-jwt-secret-key-change-in-production` |

#### 服务启动命令
```bash
# 启动Hermes Business API
nohup python3 /home/admin/hermes_business_api.py > /home/admin/hermes_business_api.log 2>&1 &

# 验证
curl -s -X POST http://localhost:8647/auth/send_sms -H 'Content-Type: application/json' -d '{"phone":"13800138000"}'

# 查看日志
tail -f /home/admin/hermes_business_api.log
```

---

## 7. 风险与应对

### 7.1 风险清单

| 风险 | 概率 | 影响 | 应对措施 |
|:-----|:----:|:----:|:---------|
| 新服务启动失败（端口冲突） | 低 | 高 | 启动前检查端口占用，准备备用端口 |
| 验证码存储内存化导致多进程冲突 | 中 | 中 | 后续迁移到SQLite存储 |
| JWT密钥硬编码在代码中 | 中 | 高 | 后续改为环境变量读取 |
| 新服务与Flask数据库写冲突 | 低 | 中 | 单一SQLite文件，使用事务隔离 |
| 前端API_BASE变更后接口不兼容 | 低 | 高 | 部署前做完整的端到端测试 |

### 7.2 回滚方案

```bash
# 回滚Nginx配置：将PRD路径重新指向Flask 5000
sudo sed -i 's|proxy_pass http://127.0.0.1:8647|proxy_pass http://127.0.0.1:5000|g' /etc/nginx/conf.d/xinclaw.conf
sudo nginx -t && sudo nginx -s reload

# 停止新服务
kill $(pgrep -f hermes_business_api.py)
```

---

## 8. 附录

### 8.1 相关文档

- PRD终版：`/www/wwwroot/xinclaw-law/docs/PRD_终版.md`
- 开发管理制度：`/home/admin/xinhai_legal_api/docs/开发管理制度_V3.0.md`
- COO API参考：`/home/admin/coo_api.py`
- 敏感信息：`/home/admin/xinhai-legal-dev/api/SENSITIVE_INFO.md`

### 8.2 迁移进度追踪

迁移进度记录在 `/home/admin/.hermes/progress/hermes_migration_plan.md`

### 8.3 术语表

| 术语 | 说明 |
|:-----|:-----|
| Hermes Business API | 新业务服务，端口8647，承载全部PRD API |
| Hermes Business Bridge | 子进程调用的业务逻辑脚本 |
| Hermes Gateway | AI Agent服务，端口8642 |
| PRD路径 | PRD第十章规定的无版本前缀API路径 |
| JWT | JSON Web Token，用户认证令牌 |

---

> **文档结束**
> 
> 本文档是心海法律AI项目的核心技术参考资料，所有开发工作开始前必须阅读本文档。
> 文档更新直接在本文档上修改，不创建新版本。
