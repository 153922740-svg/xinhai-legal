# 心海法律 AI - PRD v4.0 数据库设计文档

## 概述
本文档描述根据 PRD v4.0 需求设计的 10 张核心数据库表结构。

## 现有表结构分析
基于 `/root/xinhai-legal/models/db.py` 分析，现有表包括：
- users (用户表)
- token_transactions (Token 交易)
- membership_orders (会员订单)
- api_keys (API 密钥)
- agent_profiles (代理档案)
- agent_commissions (代理分佣)
- agent_team (代理团队)
- agent_regions (代理区域)
- partner_referrals (合伙人推荐)
- legal_qa (法律问答)
- legal_cases (法律案件)
- legal_docs (法律文档)
- rights_reminders (维权提醒)
- legal_timeline (法律时间线)
- knowledge_base (知识库)
- law_articles (法律条文)

## 新表设计 (PRD v4.0)

### 1. users (扩展)
**说明**: 在现有 users 表基础上扩展心理画像和咨询相关字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| username | TEXT | 用户名 (唯一) |
| password_hash | TEXT | 密码哈希 |
| real_name | TEXT | 真实姓名 |
| phone | TEXT | 手机号 |
| id_card | TEXT | 身份证号 |
| email | TEXT | 邮箱 |
| avatar_url | TEXT | 头像 URL |
| role | TEXT | 角色 (user/agent/admin) |
| membership | TEXT | 会员类型 |
| membership_start | TIMESTAMP | 会员开始时间 |
| membership_end | TIMESTAMP | 会员结束时间 |
| tokens_balance | INTEGER | Token 余额 |
| total_tokens_used | INTEGER | 累计消耗 Token |
| total_tokens_bought | INTEGER | 累计购买 Token |
| agent_code | TEXT | 代理码 |
| agent_level | TEXT | 代理级别 |
| agent_province | TEXT | 代理省份 |
| agent_city | TEXT | 代理城市 |
| agent_district | TEXT | 代理区县 |
| parent_agent_id | INTEGER | 上级代理 ID |
| is_active | INTEGER | 是否激活 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |
| **psych_openness** | REAL | 心理开放性 (0-10) |
| **psych_conscientiousness** | REAL | 心理尽责性 (0-10) |
| **psych_extraversion** | REAL | 心理外向性 (0-10) |
| **psych_agreeableness** | REAL | 心理宜人性 (0-10) |
| **psych_neuroticism** | REAL | 心理神经质 (0-10) |
| **psych_risk_tolerance** | REAL | 风险承受度 (0-10) |
| **consultation_preference** | TEXT | 咨询偏好 (文本/语音/视频) |
| **last_consultation_at** | TIMESTAMP | 最后咨询时间 |
| **total_consultations** | INTEGER | 总咨询次数 |

### 2. chat_logs (聊天记录)
**说明**: 存储用户与 AI 的完整对话记录

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER PRIMARY KEY | 主键 |
| user_id | INTEGER | 用户 ID (外键) |
| session_id | TEXT | 会话 ID |
| message_type | TEXT | 消息类型 (user/assistant/system) |
| content | TEXT | 消息内容 |
| content_embedding | TEXT | 内容向量 (JSON) |
| model_used | TEXT | 使用的模型 |
| tokens_used | INTEGER | 消耗 Token 数 |
| response_time_ms | INTEGER | 响应时间 (毫秒) |
| confidence_score | REAL | 置信度 |
| is_helpful | INTEGER | 是否有用 (用户反馈) |
| feedback_comment | TEXT | 反馈评论 |
| metadata | TEXT | 元数据 (JSON) |
| created_at | TIMESTAMP | 创建时间 |

### 3. psych_profiles (心理画像)
**说明**: 用户心理特征 6 维度评估

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER PRIMARY KEY | 主键 |
| user_id | INTEGER UNIQUE | 用户 ID (外键) |
| openness | REAL | 开放性 (0-10) |
| conscientiousness | REAL | 尽责性 (0-10) |
| extraversion | REAL | 外向性 (0-10) |
| agreeableness | REAL | 宜人性 (0-10) |
| neuroticism | REAL | 神经质 (0-10) |
| risk_tolerance | REAL | 风险承受度 (0-10) |
| assessment_source | TEXT | 评估来源 (questionnaire/behavior/ai_analysis) |
| assessment_confidence | REAL | 评估置信度 |
| last_updated | TIMESTAMP | 最后更新时间 |
| created_at | TIMESTAMP | 创建时间 |

### 4. consultation_intents (咨询意向)
**说明**: 用户咨询意向和线索管理

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER PRIMARY KEY | 主键 |
| user_id | INTEGER | 用户 ID (外键) |
| intent_type | TEXT | 意向类型 (initial/follow_up/urgent/referral) |
| legal_domain | TEXT | 法律领域 |
| case_type | TEXT | 案件类型 |
| urgency_level | TEXT | 紧急程度 (low/medium/high/critical) |
| budget_range | TEXT | 预算范围 |
| preferred_contact | TEXT | 偏好联系方式 |
| description | TEXT | 问题描述 |
| status | TEXT | 状态 (new/contacted/converted/lost) |
| assigned_agent_id | INTEGER | 分配代理 ID |
| source | TEXT | 来源 (web/app/referral/ad) |
| converted_order_id | INTEGER | 转化订单 ID |
| notes | TEXT | 备注 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 5. orders (订单表)
**说明**: 支持动态价格的订单系统

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER PRIMARY KEY | 主键 |
| order_no | TEXT UNIQUE | 订单号 |
| user_id | INTEGER | 用户 ID (外键) |
| order_type | TEXT | 订单类型 (consultation/membership/token_package/legal_doc) |
| product_id | TEXT | 产品 ID |
| product_name | TEXT | 产品名称 |
| original_price | REAL | 原价 |
| discount_rate | REAL | 折扣率 |
| final_price | REAL | 最终价格 |
| pricing_strategy_id | INTEGER | 定价策略 ID |
| quantity | INTEGER | 数量 |
| tokens_included | INTEGER | 包含 Token 数 |
| status | TEXT | 状态 (pending/paid/shipped/completed/refunded/cancelled) |
| payment_id | INTEGER | 支付记录 ID |
| delivery_id | INTEGER | 交付记录 ID |
| agent_id | INTEGER | 关联代理 ID |
| commission_amount | REAL | 分佣金额 |
| coupon_code | TEXT | 优惠券码 |
| coupon_discount | REAL | 优惠券折扣 |
| remarks | TEXT | 备注 |
| paid_at | TIMESTAMP | 支付时间 |
| completed_at | TIMESTAMP | 完成时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 6. payments (支付记录)
**说明**: 支付流水记录

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER PRIMARY KEY | 主键 |
| payment_no | TEXT UNIQUE | 支付单号 |
| order_id | INTEGER | 订单 ID (外键) |
| user_id | INTEGER | 用户 ID (外键) |
| amount | REAL | 支付金额 |
| currency | TEXT | 货币类型 (CNY/USD) |
| payment_method | TEXT | 支付方式 (wechat/alipay/card/bank_transfer/token) |
| payment_channel | TEXT | 支付渠道 |
| transaction_id | TEXT | 第三方交易 ID |
| status | TEXT | 状态 (pending/success/failed/refunded) |
| error_code | TEXT | 错误码 |
| error_message | TEXT | 错误信息 |
| paid_at | TIMESTAMP | 支付成功时间 |
| refunded_at | TIMESTAMP | 退款时间 |
| refund_amount | REAL | 退款金额 |
| metadata | TEXT | 元数据 (JSON) |
| created_at | TIMESTAMP | 创建时间 |

### 7. deliveries (交付记录)
**说明**: 服务/产品交付记录

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER PRIMARY KEY | 主键 |
| delivery_no | TEXT UNIQUE | 交付单号 |
| order_id | INTEGER | 订单 ID (外键) |
| user_id | INTEGER | 用户 ID (外键) |
| delivery_type | TEXT | 交付类型 (consultation_session/document/token_credit/service_access) |
| content | TEXT | 交付内容 |
| file_urls | TEXT | 文件 URL 列表 (JSON) |
| tokens_credited | INTEGER | 充值 Token 数 |
| service_duration_min | INTEGER | 服务时长 (分钟) |
| consultant_id | INTEGER | 咨询师 ID |
| consultation_time | TIMESTAMP | 咨询时间 |
| status | TEXT | 状态 (pending/delivered/confirmed/expired) |
| confirmed_at | TIMESTAMP | 确认时间 |
| expires_at | TIMESTAMP | 过期时间 |
| notes | TEXT | 备注 |
| created_at | TIMESTAMP | 创建时间 |

### 8. system_prompts (提示词库)
**说明**: 系统提示词模板管理

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER PRIMARY KEY | 主键 |
| prompt_name | TEXT | 提示词名称 |
| prompt_category | TEXT | 分类 (consultation/legal_analysis/doc_generation/customer_service) |
| prompt_template | TEXT | 提示词模板 |
| variables | TEXT | 变量定义 (JSON) |
| model_compatibility | TEXT | 适用模型 (JSON) |
| version | TEXT | 版本号 |
| is_active | INTEGER | 是否启用 |
| is_default | INTEGER | 是否默认 |
| performance_score | REAL | 性能评分 |
| usage_count | INTEGER | 使用次数 |
| created_by | INTEGER | 创建者 ID |
| approved_by | INTEGER | 审批者 ID |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 9. pricing_strategies (定价策略)
**说明**: 动态定价策略配置

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER PRIMARY KEY | 主键 |
| strategy_name | TEXT | 策略名称 |
| strategy_type | TEXT | 策略类型 (fixed/dynamic/tiered/time_based/user_segment) |
| product_type | TEXT | 产品类型 |
| base_price | REAL | 基础价格 |
| min_price | REAL | 最低价格 |
| max_price | REAL | 最高价格 |
| discount_rules | TEXT | 折扣规则 (JSON) |
| user_segment | TEXT | 用户群体 (new/vip/agent/regular) |
| time_range | TEXT | 时间范围 (JSON) |
| conditions | TEXT | 应用条件 (JSON) |
| priority | INTEGER | 优先级 |
| is_active | INTEGER | 是否启用 |
| test_group | TEXT | 测试分组 (A/B 测试) |
| performance_metrics | TEXT | 性能指标 (JSON) |
| created_by | INTEGER | 创建者 ID |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 10. optimization_logs (优化日志)
**说明**: 系统优化和 A/B 测试日志

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER PRIMARY KEY | 主键 |
| optimization_type | TEXT | 优化类型 (prompt/pricing/model/ux/conversion) |
| experiment_id | TEXT | 实验 ID |
| experiment_name | TEXT | 实验名称 |
| variant | TEXT | 变体 (A/B/C) |
| target_metric | TEXT | 目标指标 |
| baseline_value | REAL | 基准值 |
| current_value | REAL | 当前值 |
| improvement_rate | REAL | 提升率 |
| sample_size | INTEGER | 样本量 |
| confidence_level | REAL | 置信水平 |
| status | TEXT | 状态 (running/completed/failed) |
| conclusion | TEXT | 结论 |
| implemented | INTEGER | 是否实施 |
| metadata | TEXT | 元数据 (JSON) |
| created_by | INTEGER | 创建者 ID |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

## 索引设计

```sql
-- chat_logs 索引
CREATE INDEX idx_chat_logs_user ON chat_logs(user_id);
CREATE INDEX idx_chat_logs_session ON chat_logs(session_id);
CREATE INDEX idx_chat_logs_created ON chat_logs(created_at);

-- consultation_intents 索引
CREATE INDEX idx_consultation_intents_user ON consultation_intents(user_id);
CREATE INDEX idx_consultation_intents_status ON consultation_intents(status);
CREATE INDEX idx_consultation_intents_domain ON consultation_intents(legal_domain);

-- orders 索引
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at);
CREATE INDEX idx_orders_type ON orders(order_type);

-- payments 索引
CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_order ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(status);

-- deliveries 索引
CREATE INDEX idx_deliveries_user ON deliveries(user_id);
CREATE INDEX idx_deliveries_order ON deliveries(order_id);

-- system_prompts 索引
CREATE INDEX idx_system_prompts_category ON system_prompts(prompt_category);
CREATE INDEX idx_system_prompts_active ON system_prompts(is_active);

-- pricing_strategies 索引
CREATE INDEX idx_pricing_strategies_type ON pricing_strategies(strategy_type);
CREATE INDEX idx_pricing_strategies_active ON pricing_strategies(is_active);

-- optimization_logs 索引
CREATE INDEX idx_optimization_logs_type ON optimization_logs(optimization_type);
CREATE INDEX idx_optimization_logs_status ON optimization_logs(status);
```

## 关系图

```
users (1) ──< chat_logs
users (1) ──< psych_profiles (1)
users (1) ──< consultation_intents
users (1) ──< orders
users (1) ──< payments
users (1) ──< deliveries

orders (1) ──< payments
orders (1) ──< deliveries
orders (1) ──> pricing_strategies

system_prompts >── (many) model interactions
optimization_logs >── tracks all optimizations
```
