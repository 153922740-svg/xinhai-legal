# 心海法律 AI — Hermes 迁移需求分析文档

> **文档编号**: XINCLAW-REQ-HERMES-V1.0  
> **状态**: ⏳ 草稿  
> **创建日期**: 2026-05-19  
> **负责人**: 蓝图（产品官）  

---

## 1. 需求概述

### 1.1 项目背景

心海法律AI当前后端基于Flask框架开发，18个蓝图、70+API端点，API路径混用v1/v2/v3/v4/v5六套版本前缀，与PRD规定的无版本前缀标准路径不一致。总裁要求全面迁移至Hermes架构。

### 1.2 架构目标

1. **统一API路径** — 所有接口遵循PRD第十章规定的无版本前缀路径
2. **业务解耦** — 业务逻辑从Flask迁移至独立业务服务（端口8647）
3. **平滑过渡** — 新服务与Flask并行运行，覆盖全部功能后废弃Flask
4. **数据库统一** — 单一SQLite数据源

### 1.3 范围

涵盖PRD第十章全部34个API + 小程序实际调用的补充API，共约40+个接口。

### 1.4 约束条件

- 单一SQLite数据库 `/home/admin/xinhai_legal_api/data/xinhai_legal.db`
- 禁止创建新的PRD版本文件，修改直接在 `PRD_终版.md` 上更新
- 所有业务后端必须基于Hermes Agent架构
- API路径无版本前缀
- JWT认证，24小时有效期

---

## 2. 功能需求

### 2.1 认证模块（3个API）

| # | API | 方法 | 请求参数 | 响应字段 | 业务规则 |
|---|-----|:----:|:---------|:---------|:---------|
| R01 | /auth/send_sms | POST | {phone: string} | {success, message, dev_code?} | ①生成6位验证码 ②有效期5分钟③防刷1分钟1次 ④开发模式返回验证码 |
| R02 | /auth/login | POST | {phone, code} | {success, token, user, is_new} | ①验证验证码 ②新用户自动注册 ③赠送2000Token+3天会员 ④返回JWT |
| R03 | /auth/wx_login | POST | {code} | {success, token, user, is_new} | ①微信code换openid ②新用户自动注册 ③赠送同上 |

### 2.2 聊天模块（4个API）

| # | API | 方法 | 请求参数 | 响应字段 | 业务规则 |
|---|-----|:----:|:---------|:---------|:---------|
| R04 | /chat/send | POST | {message, session_id?} | {success, response, session_id, suggestions} | ①调用Hermes Gateway 8642的/v1/chat/completions ②Token扣费 ③保存对话 |
| R05 | /chat/sessions | GET | — | {success, sessions: [{id, title, updated_at}]} | 查询chat_sessions表 |
| R06 | /chat/history/:id | GET | — | {success, messages: [{role, content, created_at}]} | 查询chat_messages表 |
| R07 | /chat/sessions/:id/rename | PUT | {title} | {success} | 更新chat_sessions.title |

### 2.3 会员+支付模块（3个API）

| # | API | 方法 | 请求参数 | 响应字段 | 业务规则 |
|---|-----|:----:|:---------|:---------|:---------|
| R08 | /member/status | GET | — | {success, membership, start, end, auto_renew} | 查询memberships表 |
| R09 | /payment/wechat | POST | {plan_type, user_id} | {success, pay_params} | ①微信统一下单 ②返回支付参数 |
| R10 | /payment/get_openid | POST | {code} | {success, openid} | 调用微信jscode2session接口 |

### 2.4 Token模块（3个API）

| # | API | 方法 | 请求参数 | 响应字段 | 业务规则 |
|---|-----|:----:|:---------|:---------|:---------|
| R11 | /token/balance | GET | — | {success, balance} | 从users.tokens_balance读取 |
| R12 | /token/recharge | POST | {amount} | {success, pay_params} | ①创建充值订单 ②调用微信支付 |
| R13 | /token/transactions | GET | — | {success, transactions} | 查询token_transactions表 |

### 2.5 文书模块（5个API）

| # | API | 方法 | 请求参数 | 响应字段 | 业务规则 |
|---|-----|:----:|:---------|:---------|:---------|
| R14 | /document/generate | POST | {type, fields} | {success, document} | ①AI生成文书 ②保存到documents表 |
| R15 | /document/list | GET | — | {success, documents} | 按用户查询 |
| R16 | /document/:id/detail | GET | — | {success, document} | 单条查询 |
| R17 | /document/:id | PUT | {content} | {success} | 更新文书内容 |
| R18 | /document/:id/download | GET | — | 文件流 | 生成Word/PDF下载 |

### 2.6 积分+签到模块（4个API）

| # | API | 方法 | 请求参数 | 响应字段 | 业务规则 |
|---|-----|:----:|:---------|:---------|:---------|
| R19 | /integral/balance | GET | — | {success, balance} | 汇总积分记录 |
| R20 | /integral/records | GET | — | {success, records} | 分页查询 |
| R21 | /user/sign | POST | — | {success, points, streak} | 每日签到+连续奖励 |
| R22 | /user/sign/status | GET | — | {success, signed, streak} | 签到状态 |

### 2.7 用户模块（6个API）

| # | API | 方法 | 请求参数 | 响应字段 | 业务规则 |
|---|-----|:----:|:---------|:---------|:---------|
| R23 | /user/profile | GET | — | {success, user} | 获取当前用户信息 |
| R24 | /user/profile | PUT | {nickname, avatar} | {success} | 更新用户资料 |
| R25 | /user/verify | POST | {name, id_no} | {success} | 实名认证 |
| R26 | /user/memory | POST | {type, content} | {success} | 保存记忆 |
| R27 | /user/memory | GET | — | {success, memories} | 获取记忆 |
| R28 | /user/memory | DELETE | — | {success} | 清除记忆 |

### 2.8 合伙人模块（3个API）

| # | API | 方法 | 请求参数 | 响应字段 | 业务规则 |
|---|-----|:----:|:---------|:---------|:---------|
| R29 | /partner/level | GET | — | {success, level, rate} | 合伙人等级5级（5%/8%/12%/15%/20%）|
| R30 | /partner/dashboard | GET | — | {success, stats} | 收益统计+团队数据 |
| R31 | /partner/generate-link | POST | — | {success, link} | 生成推广链接 |

### 2.9 其他补充API（从小程序端盘点未覆盖的）

| # | API | 方法 | 请求参数 | 响应字段 | 说明 |
|---|-----|:----:|:---------|:---------|:-----|
| R32 | /health | GET | — | {status, service, version} | 健康检查 |
| R33 | /chat/sessions/:id | DELETE | — | {success} | 删除会话 |
| R34 | /document/:id/download/word | GET | — | 文件流 | 小程序用的路径，与R18合并 |

---

## 3. 非功能需求

| 类别 | 需求 | 指标 |
|:-----|:-----|:-----|
| 性能 | API响应时间 | <500ms（认证/查询类）<3000ms（AI对话类）|
| 安全 | 认证方式 | JWT（HMAC-SHA256），24小时有效期 |
| 安全 | 短信防刷 | 同一手机号1分钟1次，1小时5次 |
| 安全 | SQL注入 | 全部使用参数化查询 |
| 可用性 | 服务可用率 | 99.9% |
| 可维护性 | 日志 | 统一日志文件，滚动保留7天 |
| 可维护性 | 部署 | 独立进程，nohup启动 |

---

## 4. 数据字典

### 4.1 核心表字段说明

**users表**（操作最频繁）
| 字段 | 类型 | 说明 | 是否必填 |
|------|------|------|:--------:|
| id | INTEGER PK | 用户ID | 自动 |
| phone | TEXT | 手机号（唯一） | 是 |
| wechat_openid | TEXT | 微信openid | 否 |
| username | TEXT | 用户名 | 是 |
| nickname | TEXT | 昵称 | 否 |
| tokens_balance | INTEGER | Token余额 | 默认0 |
| membership | TEXT | 会员类型 | 默认free |
| membership_start | TEXT | 会员开始时间 | 否 |
| membership_end | TEXT | 会员到期时间 | 否 |
| status | INTEGER | 1正常/0禁用 | 默认1 |
| created_at | TEXT | 创建时间 | 自动 |

**chat_sessions表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 会话ID（UUID）|
| user_id | INTEGER | 用户ID |
| title | TEXT | 会话标题 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

**chat_messages表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 消息ID |
| session_id | TEXT | 会话ID |
| role | TEXT | user/assistant |
| content | TEXT | 消息内容 |
| created_at | TEXT | 创建时间 |

---

## 5. 迁移批次与优先级

| 批次 | 模块 | API数量 | 优先级 | 工作量 | 依赖 |
|:-----|:-----|:-------:|:------:|:------:|:-----|
| P0-1 | 认证 | 3 | 🔴最高 | 已完成 | — |
| P0-2 | 聊天 | 4 | 🔴最高 | 2h | Hermes Gateway 8642 |
| P0-3 | 会员+Token | 6 | 🔴最高 | 3h | 微信支付配置 |
| P1-1 | 文书 | 5 | 🟡高 | 3h | AI模型能力 |
| P1-2 | 积分+签到 | 4 | 🟡高 | 2h | — |
| P2-1 | 用户+记忆 | 6 | 🟢中 | 2h | — |
| P2-2 | 合伙人 | 3 | 🟢中 | 2h | — |
| P2-3 | 系统+清理 | 3 | 🟢中 | 1h | Nginx切换 |

---

## 6. 风险与假设

| 风险 | 影响 | 应对 |
|:-----|:----:|:-----|
| Hermes Gateway 8642 AI能力不稳定 | 聊天模块 | 准备降级方案（直接调用LLM API）|
| 微信支付接口回调延迟 | 支付体验 | 实现本地重试队列 |
| SQLite并发写冲突 | 高并发场景 | 使用WAL模式+重试机制 |
| 小程序端未更新API_BASE | 全部接口404 | 上线前强制小程序发版 |

---

> *文档结束*
> *下次更新：根据总裁反馈修改*
